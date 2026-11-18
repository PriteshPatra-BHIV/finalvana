# ============================================================
# Dockerfile — VANA Control Center Frontend + Nginx Proxy
# Build context: frontend/group5-lineage-dashboard/vana-control-center
# ============================================================

FROM nginx:1.27-alpine

# Restrict envsubst to VANA_* variables so Nginx built-in vars ($host, $scheme, etc.) stay intact
ENV NGINX_ENVSUBST_FILTER=^VANA_

# Default upstream values (override via .env / docker-compose)
ENV VANA_BACKEND_URL=http://vana-auth:8000 \
    VANA_G1_URL=http://vana-masterdb:8000 \
    VANA_G2_URL=https://niyantran.blackholeinfiverse.com \
    VANA_G4_URL=http://vana-auth:8000

RUN rm -f /etc/nginx/conf.d/default.conf

COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# Copy only runtime web assets (exclude local dev server, tests, and DB files)
COPY index.html login.html admin.html /usr/share/nginx/html/
COPY config.js app.js admin.js admin-auth.js geospatial.js /usr/share/nginx/html/
COPY styles.css admin.css geospatial.css /usr/share/nginx/html/
COPY SOURCE_EVIDENCE_PACK_EMITTED_TC-Z03-EXT-OPENMETEO-OBS001.json /usr/share/nginx/html/
COPY assets/ /usr/share/nginx/html/assets/

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --retries=3 --start-period=10s \
  CMD wget -q -O /dev/null http://127.0.0.1/nginx-health || exit 1
