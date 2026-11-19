#!/usr/bin/env bash
# ==============================================================================
# VANA Unified Infrastructure — Production Deployment Script
#
# This script is intended to be executed ON THE PRODUCTION VM.
# It safely transitions from the old chunk deployments (vana-masterdb-foundation
# and vana_lineage) to the unified VANA system, mounting the existing PostgreSQL
# database volume to guarantee ZERO DATA LOSS.
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh [IMAGE_TAG]
# ==============================================================================

set -euo pipefail

IMAGE_TAG="${1:-latest}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=============================================================================="
echo "         VANA ENVIRONMENTAL GOVERNANCE SYSTEM — DEPLOYMENT"
echo "=============================================================================="
echo "Target Image Tag: $IMAGE_TAG"
echo "Working Directory: $SCRIPT_DIR"

# ------------------------------------------------------------------------------
# 1. DATABASE VOLUME PRESERVATION (ZERO DATA LOSS)
# ------------------------------------------------------------------------------
echo ""
echo "--> Checking for existing PostgreSQL database volume..."
if docker volume inspect vana-masterdb-foundation_vana_pg_data >/dev/null 2>&1; then
    TARGET_DB_VOL="vana-masterdb-foundation_vana_pg_data"
    echo "    [+] Found existing database volume: $TARGET_DB_VOL"
elif docker volume inspect vana_pg_data >/dev/null 2>&1; then
    TARGET_DB_VOL="vana_pg_data"
    echo "    [+] Found existing database volume: $TARGET_DB_VOL"
else
    TARGET_DB_VOL="vana-masterdb-foundation_vana_pg_data"
    echo "    [!] No existing volume found. Creating persistent volume: $TARGET_DB_VOL"
    docker volume create "$TARGET_DB_VOL" >/dev/null
fi

# ------------------------------------------------------------------------------
# 2. STOP LEGACY CHUNK DEPLOYMENTS SAFELY
# ------------------------------------------------------------------------------
echo ""
echo "--> Safely stopping legacy chunk deployments (avoiding conflict on ports 8013, 8010, 5178, 8080)..."

if [ -d "$HOME/vana-masterdb-foundation" ]; then
    echo "    [+] Stopping old vana-masterdb-foundation compose stack..."
    (cd "$HOME/vana-masterdb-foundation" && docker compose -f docker-compose.production.yml down 2>/dev/null || true)
fi

if [ -d "$HOME/vana_lineage" ]; then
    echo "    [+] Stopping old vana_lineage compose stack..."
    (cd "$HOME/vana_lineage" && docker compose -f docker-compose.production.yml down 2>/dev/null || true)
fi

# Ensure legacy container names are stopped if they were run standalone
echo "    [+] Verifying legacy containers are stopped..."
docker stop vana_api bhiv_vana_lineage vana_db vana_auth_runtime vana_gateway 2>/dev/null || true
docker rm vana_api bhiv_vana_lineage vana_db vana_auth_runtime vana_gateway 2>/dev/null || true

# ------------------------------------------------------------------------------
# 3. CONFIGURE ENVIRONMENT FILE
# ------------------------------------------------------------------------------
echo ""
echo "--> Preparing environment variables..."
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "    [+] Creating .env from .env.example..."
        cp .env.example .env
    else
        echo "    [!] ERROR: .env file missing and .env.example not found!"
        exit 1
    fi
fi

# Ensure VANA_DB_VOLUME_NAME references the detected volume
if grep -q "^VANA_DB_VOLUME_NAME=" .env; then
    sed -i "s|^VANA_DB_VOLUME_NAME=.*|VANA_DB_VOLUME_NAME=$TARGET_DB_VOL|g" .env
else
    echo "VANA_DB_VOLUME_NAME=$TARGET_DB_VOL" >> .env
fi
echo "    [+] Attached database volume: $TARGET_DB_VOL"

# Load variables for health checking
set -a
# shellcheck disable=SC1091
source .env
set +a

FE_PORT="${VANA_FRONTEND_PORT:-8089}"
G1_PORT="${VANA_G1_PORT:-8033}"
AUTH_PORT="${VANA_AUTH_PORT:-8034}"
LINEAGE_PORT="${VANA_LINEAGE_PORT:-5185}"

# ------------------------------------------------------------------------------
# 4. COMPILE DOCKER COMPOSE CONFIGURATION
# ------------------------------------------------------------------------------
echo ""
echo "--> Generating docker-compose.production.yml with image tag: $IMAGE_TAG..."
sed "s|IMG_TAG|$IMAGE_TAG|g" docker-compose.production.template.yml > docker-compose.production.yml

docker compose -f docker-compose.production.yml config --quiet
echo "    [+] Compose configuration syntax validated."

# ------------------------------------------------------------------------------
# 5. PULL PRODUCTION IMAGES & START STACK
# ------------------------------------------------------------------------------
echo ""
echo "--> Pulling latest container images..."
docker compose -f docker-compose.production.yml pull

echo ""
echo "--> Starting VANA unified stack..."
docker compose -f docker-compose.production.yml up -d --remove-orphans

# ------------------------------------------------------------------------------
# 6. MULTI-SERVICE HEALTH CHECK VERIFICATION
# ------------------------------------------------------------------------------
echo ""
echo "--> Awaiting healthy state across all tiers..."
for i in {1..18}; do
    MDB_HEALTH=0
    AUTH_HEALTH=0
    GATEWAY_HEALTH=0
    LINEAGE_HEALTH=0

    # Probe Group 1 MasterDB
    curl -sf "http://localhost:${G1_PORT}/health" > /dev/null 2>&1 && MDB_HEALTH=1 || true

    # Probe Unified Auth & Group 4 Runtime (checks configured host port and 8000 fallback)
    curl -sf "http://localhost:${AUTH_PORT}/health" > /dev/null 2>&1 && AUTH_HEALTH=1 || true
    if [ "$AUTH_HEALTH" -eq 0 ]; then
        curl -sf "http://localhost:8000/health" > /dev/null 2>&1 && AUTH_HEALTH=1 || true
    fi

    # Probe VANA Frontend & Nginx Proxy
    curl -sf "http://localhost:${FE_PORT}/nginx-health" > /dev/null 2>&1 && GATEWAY_HEALTH=1 || true

    # Probe Lineage Port
    curl -sf "http://localhost:${LINEAGE_PORT}/nginx-health" > /dev/null 2>&1 && LINEAGE_HEALTH=1 || true

    if [ "$MDB_HEALTH" -eq 1 ] && [ "$AUTH_HEALTH" -eq 1 ] && [ "$GATEWAY_HEALTH" -eq 1 ] && [ "$LINEAGE_HEALTH" -eq 1 ]; then
        echo "=============================================================================="
        echo "                 ALL VANA SERVICES ARE OPERATIONAL & HEALTHY!                 "
        echo "=============================================================================="
        echo "  [✓] MasterDB Observation API    : http://localhost:${G1_PORT}/health (Port ${G1_PORT})"
        echo "  [✓] Auth & Group 4 Runtime      : http://localhost:${AUTH_PORT}/health (Port ${AUTH_PORT})"
        echo "  [✓] VANA Control Center Gateway : http://localhost:${FE_PORT}/ (Port ${FE_PORT})"
        echo "  [✓] Preserved Lineage Port      : http://localhost:${LINEAGE_PORT}/ (Port ${LINEAGE_PORT})"
        echo "  [✓] Mounted Database Volume     : $TARGET_DB_VOL"
        echo "=============================================================================="
        exit 0
    fi

    echo "    [$i/18] Probing endpoints (MDB=$MDB_HEALTH, Auth=$AUTH_HEALTH, Gateway=$GATEWAY_HEALTH, Lineage=$LINEAGE_HEALTH)..."
    sleep 10
done

echo ""
echo "[!] Error: Health check verification timed out after 180 seconds."
docker compose -f docker-compose.production.yml ps
docker compose -f docker-compose.production.yml logs --tail=40
exit 1
