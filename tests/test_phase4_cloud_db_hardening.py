"""
VANA Phase 4 Cloud Infrastructure & Database Hardening Automated Test Suite
===========================================================================
Tests:
  1. Universal DATABASE_URL validation and driver resolution.
  2. PostGIS Point geometry formatting and coordinate range validation.
  3. Source SQLite database inspection: 19 MasterDB tables verified.
  4. Migration Plan Generator: PostGIS spatial layers (TC, MV, SMR) & table mappings.
  5. RBAC Protection on GET /api/database/migration/plan: Admin permitted, others 403.
  6. PostgreSQL DDL Migration 0010 syntax and extension coverage.
"""

import sys
from pathlib import Path
import pytest

FINALVANA_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = FINALVANA_DIR / "backend"
MASTERDB_DIR = BACKEND_DIR / "group1-masterdb"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(MASTERDB_DIR) not in sys.path:
    sys.path.insert(0, str(MASTERDB_DIR))

import auth_service
import unified_auth_runtime
from db_migration_tool import migration_manager
from api import db as masterdb_db


@pytest.fixture(scope="session", autouse=True)
def setup_databases():
    auth_service.init_users_table()
    unified_auth_runtime.init_governance_audit_table()
    masterdb_db.initialize_database()


def test_database_url_parser():
    """Verify DATABASE_URL parsing for SQLite and PostgreSQL."""
    # SQLite
    res_sqlite = migration_manager.parse_database_url("sqlite:///vana_api.db")
    assert res_sqlite["driver"] == "sqlite"
    assert res_sqlite["is_postgres"] is False
    assert res_sqlite["is_postgis_supported"] is False

    # PostgreSQL
    res_pg = migration_manager.parse_database_url("postgresql://vana:pass@db.vana.gov.in:5432/vana_prod")
    assert res_pg["driver"] == "postgresql"
    assert res_pg["is_postgres"] is True
    assert res_pg["is_postgis_supported"] is True

    # Invalid
    with pytest.raises(ValueError):
        migration_manager.parse_database_url("mysql://root:pass@localhost/db")

    with pytest.raises(ValueError):
        migration_manager.parse_database_url("")


def test_postgis_point_formatter():
    """Verify PostGIS WKT formatting with (Longitude X, Latitude Y) order."""
    # Thane Creek coordinates: Lat 19.1288, Lon 72.9421
    pt = migration_manager.format_postgis_point(latitude=19.1288, longitude=72.9421)
    assert pt == "SRID=4326;POINT(72.942100 19.128800)"

    # Out of range latitude
    with pytest.raises(ValueError):
        migration_manager.format_postgis_point(latitude=95.0, longitude=72.0)

    # Out of range longitude
    with pytest.raises(ValueError):
        migration_manager.format_postgis_point(latitude=19.0, longitude=190.0)


def test_source_database_inspection_has_19_tables():
    """Verify all 19 MasterDB tables are verified in the source database."""
    stats = migration_manager.inspect_source_database()
    assert stats["engine"] == "SQLite"
    assert stats["total_tables_present"] >= 19
    assert len(stats["missing_tables"]) == 0
    assert "observation" in stats["table_counts"]
    assert "sensor_calibration_registry" in stats["table_counts"]
    assert "statutory_dispatch_ledger" in stats["table_counts"]
    assert stats["status"] == "HEALTHY"


def test_migration_plan_generation():
    """Verify cloud migration plan contains PostGIS layers and zero-data-loss guarantee."""
    plan = migration_manager.generate_migration_plan("postgresql://user:pass@host:5432/db")
    assert plan["target_engine"] == "postgresql"
    assert plan["is_postgis_active"] is True
    assert len(plan["tables_to_migrate"]) == 19
    assert plan["zero_data_loss_guaranteed"] is True

    layers = plan["postgis_spatial_layers"]
    zone_codes = [lyr["zone_code"] for lyr in layers]
    assert "TC" in zone_codes
    assert "MV" in zone_codes
    assert "SMR" in zone_codes


def test_rbac_migration_plan_endpoint():
    """Only Platform Admin can view database migration plans; others receive 403."""
    ok, _, _, admin_sess = auth_service.authenticate_user("vana@gmail.com", "vana", "ADMIN")
    ok2, _, _, officer_sess = auth_service.authenticate_user("forest@gmail.com", "vana", "FOREST_OFFICER")
    ok3, _, _, field_sess = auth_service.authenticate_user("feild@gmail.com", "vana", "FIELD_AGENT")

    # Admin permitted
    res_admin = unified_auth_runtime.get_database_migration_plan(authorization=f"Bearer {admin_sess['access_token']}")
    assert res_admin["target_engine"] == "postgresql"
    assert res_admin["is_postgis_active"] is True

    # Forest Officer rejected
    with pytest.raises(unified_auth_runtime.HTTPException) as exc1:
        unified_auth_runtime.get_database_migration_plan(authorization=f"Bearer {officer_sess['access_token']}")
    assert exc1.value.status_code == 403

    # Field Agent rejected
    with pytest.raises(unified_auth_runtime.HTTPException) as exc2:
        unified_auth_runtime.get_database_migration_plan(authorization=f"Bearer {field_sess['access_token']}")
    assert exc2.value.status_code == 403


def test_postgresql_ddl_0010_content():
    """Verify PostgreSQL migration file 0010 contains PostGIS extension and new tables."""
    migration_file = MASTERDB_DIR / "migrations" / "0010_phase1_3_hardening.sql"
    assert migration_file.is_file()
    sql_text = migration_file.read_text(encoding="utf-8")

    assert "CREATE EXTENSION IF NOT EXISTS postgis" in sql_text
    assert "CREATE TABLE IF NOT EXISTS sensor_calibration_registry" in sql_text
    assert "CREATE TABLE IF NOT EXISTS statutory_dispatch_ledger" in sql_text
    assert "CREATE INDEX IF NOT EXISTS idx_geo_location_geom_gist ON geo_location USING GIST (geom)" in sql_text


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
