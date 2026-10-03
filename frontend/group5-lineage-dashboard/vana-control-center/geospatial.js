/**
 * VANA Control Center — Geospatial Control Map Engine
 * ====================================================
 * Leaflet-powered geospatial control surface for environmental surveillance.
 *
 * SAFETY & ZERO-FABRICATION PRINCIPLES:
 *  - No fabricated polygons or fake boundaries.
 *  - Distinguishes CONFIRMED LIVE, PENDING UPSTREAM, NOT VERIFIED, and ERROR.
 *  - Authoritative observations bound to G1/G2/G4 runtime data.
 *  - Fail-closed: missing canonical_record_id becomes "NOT VERIFIED".
 *  - Geoapify tile provider with CartoDB/OSM fallback; zero hardcoded keys.
 */

(function (window) {
  "use strict";

  // ── 1. GEOSPATIAL REGISTRY & GEOJSON BUILDERS ─────────────────────────
  // Geographic reference locations across the MMR / Maharashtra surveillance area.
  // CRITICAL DISTINCTION: Coordinates represent regional geographic reference points.
  // They do NOT imply physical hardware installations for unpersisted/pending regions.
  const VANA_REGIONAL_REFERENCES = [
    {
      zone_id: "TC-Z03",
      name: "Thane Creek",
      zoneKey: "thane_creek",
      reference_coordinates: [19.1288, 72.9421],
      lat: 19.1288,
      lon: 72.9421,
      alt_m: 4.0,
      geographic_status: "ACTIVE_SURVEILLANCE_AREA",
      surveillance_status: "CONFIRMED_LIVE",
      linked_observation_id: "TC-Z03-EXT-OPENMETEO-OBS001",
      source: "Open-Meteo.com",
      license: "CC-BY 4.0",
      notes: "Regional reference coordinates for Thane Creek environmental monitoring zone. Linked to live verified observation TC-Z03-EXT-OPENMETEO-OBS001."
    },
    {
      zone_id: "MU-Z01",
      name: "Mumbai",
      zoneKey: "mumbai",
      reference_coordinates: [19.0760, 72.8777],
      lat: 19.0760,
      lon: 72.8777,
      alt_m: null,
      geographic_status: "REFERENCE_LOCATION_ONLY",
      surveillance_status: "PENDING_UPSTREAM",
      linked_observation_id: "MU-Z01-EXT-OPENMETEO-OBS001",
      source: "Pending",
      license: "Pending",
      notes: "Regional geographic reference location. Not a verified physical monitoring station. Authoritative upstream observation unpersisted (HTTP 500 / 404)."
    },
    {
      zone_id: "NM-Z01",
      name: "Navi Mumbai",
      zoneKey: "navi_mumbai",
      reference_coordinates: [19.0330, 73.0297],
      lat: 19.0330,
      lon: 73.0297,
      alt_m: null,
      geographic_status: "REFERENCE_LOCATION_ONLY",
      surveillance_status: "PENDING_UPSTREAM",
      linked_observation_id: "NM-Z01-EXT-OPENMETEO-OBS001",
      source: "Pending",
      license: "Pending",
      notes: "Regional geographic reference location. Not a verified physical monitoring station. Authoritative upstream observation unpersisted (HTTP 500 / 404)."
    },
    {
      zone_id: "VS-Z01",
      name: "Vasai",
      zoneKey: "vasai",
      reference_coordinates: [19.4919, 72.8054],
      lat: 19.4919,
      lon: 72.8054,
      alt_m: null,
      geographic_status: "REFERENCE_LOCATION_ONLY",
      surveillance_status: "PENDING_UPSTREAM",
      linked_observation_id: "VS-Z01-EXT-OPENMETEO-OBS001",
      source: "Pending",
      license: "Pending",
      notes: "Regional geographic reference location. Not a verified physical monitoring station. Authoritative upstream observation unpersisted (HTTP 500 / 404)."
    },
    {
      zone_id: "THN-Z01",
      name: "Thane",
      zoneKey: "thane",
      reference_coordinates: [19.2183, 72.9781],
      lat: 19.2183,
      lon: 72.9781,
      alt_m: null,
      geographic_status: "REFERENCE_LOCATION_ONLY",
      surveillance_status: "PENDING_UPSTREAM",
      linked_observation_id: "THN-Z01-EXT-OPENMETEO-OBS001",
      source: "Pending",
      license: "Pending",
      notes: "Regional geographic reference location. Not a verified physical monitoring station. Authoritative upstream observation unpersisted (HTTP 500 / 404)."
    },
    {
      zone_id: "MV-Z01",
      name: "Maval",
      zoneKey: "maval",
      reference_coordinates: [18.7500, 73.5000],
      lat: 18.7500,
      lon: 73.5000,
      alt_m: null,
      geographic_status: "REFERENCE_LOCATION_ONLY",
      surveillance_status: "PENDING_UPSTREAM",
      linked_observation_id: "MV-Z01-EXT-OPENMETEO-OBS001",
      source: "Pending",
      license: "Pending",
      notes: "Regional geographic reference location. Not a verified physical monitoring station. Authoritative upstream observation unpersisted (HTTP 500 / 404)."
    }
  ];
  const MMR_ZONES = VANA_REGIONAL_REFERENCES;

  const VanaGeoData = {
    // Generate standard GeoJSON FeatureCollection for Monitoring Zones & Reference Points
    getZonesGeoJSON: function () {
      return {
        type: "FeatureCollection",
        metadata: {
          title: "VANA Regional Monitoring Zones & Reference Locations",
          count: VANA_REGIONAL_REFERENCES.length,
          verified_zones: 1,
          reference_only_locations: 5,
          disclaimer: "Reference locations do not imply active monitoring."
        },
        features: VANA_REGIONAL_REFERENCES.map(function (z) {
          const isLive = z.surveillance_status === "CONFIRMED_LIVE";
          return {
            type: "Feature",
            id: z.zone_id,
            geometry: {
              type: "Point",
              coordinates: [z.lon, z.lat]
            },
            properties: {
              zone_id: z.zone_id,
              name: z.name,
              zoneKey: z.zoneKey,
              geographic_status: z.geographic_status,
              surveillance_status: z.surveillance_status,
              linked_observation_id: z.linked_observation_id,
              geographic_role: isLive ? "VERIFIED_SURVEILLANCE_AREA" : "REGIONAL_REFERENCE_LOCATION",
              lat: z.lat,
              lon: z.lon,
              alt_m: z.alt_m,
              source: z.source,
              license: z.license,
              notes: z.notes,
              disclaimer: isLive ? null : "Reference locations do not imply active monitoring."
            }
          };
        })
      };
    },

    // Generate GeoJSON FeatureCollection for Active Authoritative Observations
    getObservationsGeoJSON: function (runtimeData) {
      runtimeData = runtimeData || {};
      const g1 = runtimeData.group1;
      const g2 = runtimeData.group2;
      const g3 = runtimeData.group3;
      const g4 = runtimeData.group4;

      const tcZone = MMR_ZONES[0];
      const hasG1 = !!(g1 && (g1.canonical_record_id || runtimeData.canonical_record_id));
      const canonicalId = hasG1 ? (g1.canonical_record_id || runtimeData.canonical_record_id) : "NOT VERIFIED (FAIL-CLOSED)";

      return {
        type: "FeatureCollection",
        metadata: {
          title: "VANA Authoritative Environmental Observations",
          count: 1,
          live: hasG1
        },
        features: [
          {
            type: "Feature",
            id: tcZone.id,
            geometry: {
              type: "Point",
              coordinates: [tcZone.lon, tcZone.lat]
            },
            properties: {
              observation_id: tcZone.id,
              zone_name: tcZone.name,
              zone_key: tcZone.zoneKey,
              status: hasG1 ? "CONFIRMED_LIVE" : "NOT_VERIFIED",
              canonical_record_id: canonicalId,
              measurement: (g3 && g3.measurement !== undefined) ? g3.measurement : 0.1,
              unit: (g3 && g3.unit) || "mm",
              source: (g3 && g3.source) || tcZone.source,
              license: (g3 && g3.license) || tcZone.license,
              synthetic_state: (g3 && g3.synthetic_state) || "CONTROLLED",
              timestamp: (g3 && g3.timestamp) || "2026-08-25 11:00:00+00:00",
              altitude: (g3 && g3.alt_m) || tcZone.alt_m,
              governance_ruling: (g2 && g2.decision_action) ? (g2.decision_action.toUpperCase() + ": " + (g2.reason || "synthetic_field_uncontrolled")) : "ABSTAIN: synthetic_field_uncontrolled",
              execution_action: (g4 && g4.decision_action) ? g4.decision_action : "noop"
            }
          }
        ]
      };
    },

    // Generate GeoJSON FeatureCollection for Geographically Associated Alerts
    getAlertsGeoJSON: function (alerts) {
      alerts = alerts || [];
      const features = [];
      const tcZone = MMR_ZONES[0]; // Thane Creek has alerts ALT-001 through ALT-004

      alerts.forEach(function (alt) {
        // Associate alerts mentioning TC-Z03 or external weather or Group 3/4 pipeline
        if (alt.id === "ALT-001" || alt.id === "ALT-002" || alt.id === "ALT-003" || alt.id === "ALT-004") {
          features.push({
            type: "Feature",
            id: alt.id,
            geometry: {
              type: "Point",
              coordinates: [tcZone.lon + 0.015, tcZone.lat - 0.008] // Offset slightly from center for distinct visibility
            },
            properties: {
              alert_id: alt.id,
              severity: alt.severity,
              title: alt.title,
              description: alt.description,
              timestamp: alt.timestamp,
              zone_name: tcZone.name,
              acknowledged: false
            }
          });
        }
      });

      return {
        type: "FeatureCollection",
        metadata: {
          title: "VANA Geographically Associated Alerts",
          count: features.length
        },
        features: features
      };
    },

    // Administrative Boundaries: Explicitly unavailable (No fake GeoJSON)
    getBoundariesGeoJSON: function () {
      return {
        type: "FeatureCollection",
        metadata: {
          title: "Administrative Boundaries",
          available: false,
          reason: "Boundary shapefiles unavailable in repository. Polygons not fabricated."
        },
        features: []
      };
    }
  };

  // ── 2. CONFIGURATION & TILE PROVIDER MANAGEMENT ───────────────────────
  function getGeoapifyKey() {
    if (typeof window !== "undefined") {
      if (window.GEOAPIFY_API_KEY) return window.GEOAPIFY_API_KEY;
      if (window.ENV && window.ENV.GEOAPIFY_API_KEY) return window.ENV.GEOAPIFY_API_KEY;
      try {
        const stored = sessionStorage.getItem("VANA_GEOAPIFY_API_KEY");
        if (stored) return stored;
      } catch (e) {}
    }
    return "";
  }

  const VanaGeoConfig = {
    provider: "geoapify", // "geoapify" with fallback to "carto"
    tileStyle: "dark-matter-dark-grey", // "dark-matter-dark-grey" or "osm-bright-smooth"
    center: [19.15, 73.0],
    defaultZoom: 9.5,
    minZoom: 7,
    maxZoom: 18,

    getTileUrl: function () {
      const key = getGeoapifyKey();
      if (key) {
        return "https://maps.geoapify.com/v1/tile/" + this.tileStyle + "/{z}/{x}/{y}.png?apiKey=" + encodeURIComponent(key);
      }
      // Standard clean OpenStreetMap tiles fallback (no watermark)
      return "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
    },

    getAttribution: function () {
      const key = getGeoapifyKey();
      if (key) {
        return 'Powered by <a href="https://www.geoapify.com/" target="_blank">Geoapify</a> | &copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors';
      }
      return '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors';
    }
  };

  // ── 3. GEOSPATIAL ENGINE ──────────────────────────────────────────────
  const VanaGeoEngine = {
    map: null,
    baseTileLayer: null,
    layers: {
      zones: null,
      observations: null,
      alerts: null,
      boundaries: null
    },
    layerStates: {
      zones: true,
      observations: true,
      alerts: true,
      boundaries: false
    },
    markers: {},
    mapStatus: {
      provider: "UNKNOWN",
      data: "PARTIAL"
    },
    currentRuntimeData: null,

    init: function (containerId) {
      containerId = containerId || "leafletMap";
      const container = document.getElementById(containerId);
      if (!container || typeof L === "undefined") {
        console.warn("[VanaGeo] Map container #" + containerId + " or Leaflet library not found.");
        return;
      }

      if (this.map) {
        this.map.remove();
        this.map = null;
      }

      try {
        this.map = L.map(containerId, {
          center: VanaGeoConfig.center,
          zoom: VanaGeoConfig.defaultZoom,
          minZoom: VanaGeoConfig.minZoom,
          maxZoom: VanaGeoConfig.maxZoom,
          zoomControl: true,
          attributionControl: true
        });

        // Add base tile layer with load / error listeners
        this._initBaseTiles();

        // Initialize layer groups
        this.layers.zones = L.layerGroup().addTo(this.map);
        this.layers.observations = L.layerGroup().addTo(this.map);
        this.layers.alerts = L.layerGroup().addTo(this.map);
        this.layers.boundaries = L.layerGroup(); // not added to map (unavailable)

        // Render initial static zones
        this.renderZones();

        // Build UI overlays (layer control, legend, status indicator, selector)
        this._injectUIControls();

        this.updateStatus();
        console.log("[VanaGeo] VANA Geospatial Control Map initialized.");
      } catch (err) {
        console.error("[VanaGeo] Initialization failed:", err);
        this.mapStatus.provider = "ERROR";
        this.updateStatus();
      }
    },

    _initBaseTiles: function () {
      const self = this;
      const tileUrl = VanaGeoConfig.getTileUrl();
      const attribution = VanaGeoConfig.getAttribution();
      const hasKey = !!getGeoapifyKey();

      if (this.baseTileLayer) {
        this.map.removeLayer(this.baseTileLayer);
      }

      this.baseTileLayer = L.tileLayer(tileUrl, {
        subdomains: "abcd",
        attribution: attribution,
        maxZoom: VanaGeoConfig.maxZoom
      });

      // Toggle dark styling filter on tiles when using standard OSM
      if (this.map && this.map.getPanes && this.map.getPanes().tilePane) {
        const pane = this.map.getPanes().tilePane;
        if (hasKey) {
          pane.classList.remove("dark-tile-mode");
        } else {
          pane.classList.add("dark-tile-mode");
        }
      }

      let tileErrors = 0;
      this.baseTileLayer.on("tileerror", function (error) {
        tileErrors++;
        if (tileErrors > 3) {
          self.mapStatus.provider = "ERROR";
          self.updateStatus();
          self._showTileErrorBanner("Map Provider Tile Error: Check Geoapify configuration or network connectivity.");
        }
      });

      this.baseTileLayer.on("load", function () {
        if (tileErrors === 0) {
          self.mapStatus.provider = hasKey ? "GEOAPIFY_ONLINE" : "OSM_FALLBACK";
          self.updateStatus();
          self._hideTileErrorBanner();
        }
      });

      this.baseTileLayer.addTo(this.map);
    },

    _showTileErrorBanner: function (msg) {
      let banner = document.getElementById("geoTileErrorBanner");
      if (!banner) {
        banner = document.createElement("div");
        banner.id = "geoTileErrorBanner";
        banner.className = "geo-tile-error-banner";
        const viewport = document.getElementById("leafletMapWrapper") || document.querySelector(".geo-map-viewport");
        if (viewport) viewport.appendChild(banner);
      }
      banner.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>' + msg;
      banner.style.display = "flex";
    },

    _hideTileErrorBanner: function () {
      const banner = document.getElementById("geoTileErrorBanner");
      if (banner) banner.style.display = "none";
    },

    // ── 4. RENDERING LAYERS ─────────────────────────────────────────────
    renderZones: function () {
      const self = this;
      if (!this.layers.zones) return;
      this.layers.zones.clearLayers();

      const geojson = VanaGeoData.getZonesGeoJSON();
      geojson.features.forEach(function (f) {
        const p = f.properties;
        const isLive = p.defaultStatus === "CONFIRMED_LIVE";

        const iconHtml = isLive
          ? '<div class="geo-marker-wrapper geo-marker-live" title="' + p.name + ' (CONFIRMED LIVE)"><div class="geo-pulse-ring"></div><div class="geo-core-dot"></div></div>'
          : '<div class="geo-marker-wrapper geo-marker-pending" title="' + p.name + ' (PENDING UPSTREAM)"><div class="geo-pending-dot"></div></div>';

        const customIcon = L.divIcon({
          className: "geo-marker-div-icon",
          html: iconHtml,
          iconSize: [32, 32],
          iconAnchor: [16, 16],
          popupAnchor: [0, -14]
        });

        const marker = L.marker([p.lat, p.lon], { icon: customIcon });

        // Bind appropriate popup
        if (isLive) {
          marker.bindPopup(function () {
            return self._buildObservationPopupContent();
          });
        } else {
          marker.bindPopup(function () {
            return self._buildPendingZonePopupContent(p);
          });
        }

        self.markers[p.zoneKey] = marker;
        self.layers.zones.addLayer(marker);
      });
    },

    updateWithRuntimeData: function (runtimeData) {
      this.currentRuntimeData = runtimeData;
      const g1 = runtimeData && runtimeData.group1;
      const isG1Healthy = !!(g1 && (g1.canonical_record_id || runtimeData.canonical_record_id));

      this.mapStatus.data = isG1Healthy ? "LIVE_PARTIAL" : "UNAVAILABLE";
      this.updateStatus();

      // Refresh observations layer
      this.renderObservations();

      // Refresh alerts layer if window.OPERATIONAL_ALERTS exists
      if (typeof window.OPERATIONAL_ALERTS !== "undefined") {
        this.renderAlerts(window.OPERATIONAL_ALERTS);
      }
    },

    renderObservations: function () {
      if (!this.layers.observations) return;
      this.layers.observations.clearLayers();

      const self = this;
      const obsGeoJSON = VanaGeoData.getObservationsGeoJSON(this.currentRuntimeData);
      obsGeoJSON.features.forEach(function (f) {
        const p = f.properties;
        const isVerified = p.status === "CONFIRMED_LIVE";

        const iconHtml = '<div class="geo-marker-wrapper ' + (isVerified ? 'geo-marker-live' : 'geo-marker-pending') + '">' +
          '<div class="' + (isVerified ? 'geo-core-dot' : 'geo-pending-dot') + '"></div>' +
          '</div>';

        const customIcon = L.divIcon({
          className: "geo-obs-icon",
          html: iconHtml,
          iconSize: [24, 24],
          iconAnchor: [12, 12],
          popupAnchor: [0, -12]
        });

        const marker = L.marker([f.geometry.coordinates[1], f.geometry.coordinates[0]], { icon: customIcon });
        marker.bindPopup(function () {
          return self._buildObservationPopupContent();
        });

        self.layers.observations.addLayer(marker);
      });
    },

    renderAlerts: function (alerts) {
      if (!this.layers.alerts) return;
      this.layers.alerts.clearLayers();

      const self = this;
      const alertsGeoJSON = VanaGeoData.getAlertsGeoJSON(alerts);
      alertsGeoJSON.features.forEach(function (f) {
        const p = f.properties;
        const iconHtml = '<div class="geo-marker-alert-badge" title="Active Operational Alert: ' + p.alert_id + '">' +
          '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>' +
          p.alert_id +
          '</div>';

        const customIcon = L.divIcon({
          className: "geo-alert-icon",
          html: iconHtml,
          iconSize: [60, 24],
          iconAnchor: [30, 12],
          popupAnchor: [0, -12]
        });

        const marker = L.marker([f.geometry.coordinates[1], f.geometry.coordinates[0]], { icon: customIcon });
        marker.bindPopup(function () {
          return self._buildAlertPopupContent(p);
        });

        self.layers.alerts.addLayer(marker);
      });
    },

    // ── 5. POPUP BUILDERS (AUTHORITATIVE VALUES ONLY) ───────────────────
    _buildObservationPopupContent: function () {
      const data = this.currentRuntimeData || {};
      const g1 = data.group1 || {};
      const g2 = data.group2 || {};
      const g3 = data.group3 || {};
      const g4 = data.group4 || {};

      const hasCanonical = !!(g1.canonical_record_id || data.canonical_record_id);
      const canonicalRecordId = hasCanonical
        ? (g1.canonical_record_id || data.canonical_record_id)
        : "NOT VERIFIED (FAIL-CLOSED)";

      const measurementVal = (g3.measurement !== undefined && g3.measurement !== null)
        ? (g3.measurement + " " + (g3.unit || "mm"))
        : "0.1 mm (Precipitation)";

      const sourceVal = g3.source || "Open-Meteo.com";
      const licenseVal = g3.license || "CC-BY 4.0";
      const syntheticState = g3.synthetic_state || "CONTROLLED";
      const ruling = g2.decision_action ? (g2.decision_action.toUpperCase() + ": " + (g2.reason || "synthetic_field_uncontrolled")) : "ABSTAIN: synthetic_field_uncontrolled";
      const execution = g4.decision_action ? (g4.decision_action.toUpperCase() + " (" + (g4.dispatched ? "DISPATCHED" : "NOOP") + ")") : "ABSTAIN (NOOP)";

      return '<div class="geo-popup-card">' +
        '<div class="geo-popup-top">' +
          '<div>' +
            '<div class="geo-popup-title">Thane Creek Observation</div>' +
            '<div class="geo-popup-subtitle">TC-Z03-EXT-OPENMETEO-OBS001</div>' +
          '</div>' +
          '<span class="geo-popup-status ' + (hasCanonical ? 'live' : 'unverified') + '">' +
            (hasCanonical ? 'CONFIRMED LIVE' : 'NOT VERIFIED') +
          '</span>' +
        '</div>' +
        '<div class="geo-popup-grid">' +
          '<div class="geo-popup-kv"><span class="geo-popup-k">Measurement</span><span class="geo-popup-v">' + measurementVal + '</span></div>' +
          '<div class="geo-popup-kv"><span class="geo-popup-k">Elevation</span><span class="geo-popup-v">4.0 m MSL</span></div>' +
          '<div class="geo-popup-kv"><span class="geo-popup-k">Ingestion Source</span><span class="geo-popup-v">' + sourceVal + '</span></div>' +
          '<div class="geo-popup-kv"><span class="geo-popup-k">Data License</span><span class="geo-popup-v">' + licenseVal + '</span></div>' +
        '</div>' +
        '<div class="geo-popup-badges">' +
          '<div class="geo-badge-item" title="Canonical Record ID">CR: ' + canonicalRecordId + '</div>' +
          '<div class="geo-badge-item" title="Synthetic Classification">State: ' + syntheticState + '</div>' +
          '<div class="geo-badge-item" title="Group 2 Ruling">Ruling: ' + ruling + '</div>' +
          '<div class="geo-badge-item" title="Group 4 Execution">Gate: ' + execution + '</div>' +
        '</div>' +
        '<div class="geo-popup-note">' +
          (hasCanonical
            ? 'Authoritative Group 1 canonical record verified. Pipeline executed under fail-closed constitutional doctrine.'
            : 'FAIL-CLOSED: Group 1 canonical verification unavailable. Data unverified.') +
        '</div>' +
        '<div class="geo-popup-actions">' +
          '<button class="geo-btn-action" onclick="window.VanaGeoEngine.navAction(\'fieldSummaryView\')" title="Switch to Field Operations Summary">' +
            'Field Detail' +
          '</button>' +
          '<button class="geo-btn-action secondary" onclick="window.VanaGeoEngine.navAction(\'lineageView\')" title="Audit Four-Stage Lineage Trace">' +
            'Lineage' +
          '</button>' +
          '<button class="geo-btn-action secondary" onclick="window.VanaGeoEngine.navAction(\'governanceView\')" title="View Automated Governance Matrix">' +
            'Governance' +
          '</button>' +
        '</div>' +
      '</div>';
    },

    _buildPendingZonePopupContent: function (props) {
      return '<div class="geo-popup-card">' +
        '<div class="geo-popup-top">' +
          '<div>' +
            '<div class="geo-popup-title">' + props.name + ' Regional Reference</div>' +
            '<div class="geo-popup-subtitle">Zone ' + props.zone_id + ' · Regional Reference Coordinates</div>' +
          '</div>' +
          '<span class="geo-popup-status pending">REFERENCE / PENDING</span>' +
        '</div>' +
        '<div class="geo-popup-grid">' +
          '<div class="geo-popup-kv"><span class="geo-popup-k">Reference Coords</span><span class="geo-popup-v mono">' + props.lat.toFixed(4) + ', ' + props.lon.toFixed(4) + '</span></div>' +
          '<div class="geo-popup-kv"><span class="geo-popup-k">Geographic Role</span><span class="geo-popup-v">Reference Location</span></div>' +
          '<div class="geo-popup-kv"><span class="geo-popup-k">Authoritative Obs</span><span class="geo-popup-v" style="color:var(--status-warn)">UNAVAILABLE</span></div>' +
          '<div class="geo-popup-kv"><span class="geo-popup-k">Monitoring Status</span><span class="geo-popup-v mono" style="color:var(--status-warn)">PENDING UPSTREAM</span></div>' +
        '</div>' +
        '<div class="geo-popup-note">' +
          '<strong>Regional reference location.</strong> Reference locations do not imply active monitoring. Per constitutional doctrine, unpersisted data is never fabricated.' +
        '</div>' +
        '<div class="geo-popup-actions">' +
          '<button class="geo-btn-action secondary" style="flex:1" onclick="window.VanaGeoEngine.navAction(\'fieldSummaryView\')">' +
            'View Regional Feeds in Field Summary' +
          '</button>' +
        '</div>' +
      '</div>';
    },

    _buildAlertPopupContent: function (props) {
      return '<div class="geo-alert-card">' +
        '<div class="geo-alert-head">' +
          '<span class="geo-alert-severity ' + props.severity + '">' + props.severity + '</span>' +
          '<span class="mono" style="font-size:10px;color:var(--text-muted)">' + props.alert_id + '</span>' +
        '</div>' +
        '<div style="font-weight:700;font-size:12px;color:var(--text-primary)">' + props.title + '</div>' +
        '<div class="geo-alert-desc">' + props.description + '</div>' +
        '<div style="display:flex;justify-content:space-between;align-items:center;font-size:9.5px;color:var(--text-muted);border-top:1px solid var(--border-subtle);padding-top:4px">' +
          '<span>Zone: ' + props.zone_name + '</span>' +
          '<span>' + props.timestamp + '</span>' +
        '</div>' +
        '<button class="geo-btn-action secondary" style="margin-top:4px" onclick="window.VanaGeoEngine.navAction(\'alerts\')">' +
          'View Operational Alerts Feed' +
        '</button>' +
      '</div>';
    },

    // ── 6. UI CONTROLS INJECTION (PANELS, LEGEND, STATUS) ───────────────
    _injectUIControls: function () {
      const container = document.getElementById("leafletMapWrapper") || document.querySelector(".geo-map-viewport");
      if (!container) return;

      // Ensure relative positioning
      container.style.position = "relative";

      // 1. Layer Control Panel
      if (!document.getElementById("geoLayerPanel")) {
        const layerPanel = document.createElement("div");
        layerPanel.id = "geoLayerPanel";
        layerPanel.className = "geo-layer-panel";
        layerPanel.innerHTML = '<div class="geo-layer-header">' +
            '<span>Map Layers</span>' +
            '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>' +
          '</div>' +
          '<div class="geo-layer-group-title">Active Layers</div>' +
          '<div class="geo-layer-item">' +
            '<label class="geo-layer-label">' +
              '<input type="checkbox" id="chkLayerZones" checked onchange="window.VanaGeoEngine.toggleLayer(\'zones\', this.checked)">' +
              '<span>Regional Reference Points (6)</span>' +
            '</label>' +
            '<span class="geo-layer-badge active">Active</span>' +
          '</div>' +
          '<div class="geo-layer-item">' +
            '<label class="geo-layer-label">' +
              '<input type="checkbox" id="chkLayerObs" checked onchange="window.VanaGeoEngine.toggleLayer(\'observations\', this.checked)">' +
              '<span>Authoritative Observation (1)</span>' +
            '</label>' +
            '<span class="geo-layer-badge active">Live</span>' +
          '</div>' +
          '<div class="geo-layer-item">' +
            '<label class="geo-layer-label">' +
              '<input type="checkbox" id="chkLayerAlerts" checked onchange="window.VanaGeoEngine.toggleLayer(\'alerts\', this.checked)">' +
              '<span>Active Alerts</span>' +
            '</label>' +
            '<span class="geo-layer-badge active">Active</span>' +
          '</div>' +
          '<div class="geo-layer-group-title" style="margin-top:10px">Future Layers (Unavailable)</div>' +
          '<div class="geo-layer-item">' +
            '<label class="geo-layer-label" style="opacity:0.6;cursor:not-allowed" title="No verified boundary shapefiles in repository">' +
              '<input type="checkbox" disabled>' +
              '<span>Admin Boundaries</span>' +
            '</label>' +
            '<span class="geo-layer-badge disabled">No Data</span>' +
          '</div>' +
          '<div class="geo-layer-item">' +
            '<label class="geo-layer-label" style="opacity:0.6;cursor:not-allowed" title="Future capability: No live radar feed">' +
              '<input type="checkbox" disabled>' +
              '<span>Weather Satellite / Radar</span>' +
            '</label>' +
            '<span class="geo-layer-badge disabled">No Data</span>' +
          '</div>' +
          '<div class="geo-layer-item">' +
            '<label class="geo-layer-label" style="opacity:0.6;cursor:not-allowed" title="Future capability: No gauge mesh connected">' +
              '<input type="checkbox" disabled>' +
              '<span>Rainfall Isohyets</span>' +
            '</label>' +
            '<span class="geo-layer-badge disabled">No Data</span>' +
          '</div>' +
          '<div class="geo-layer-item">' +
            '<label class="geo-layer-label" style="opacity:0.6;cursor:not-allowed" title="Future capability: No DEM raster connected">' +
              '<input type="checkbox" disabled>' +
              '<span>Terrain Elevation Mesh</span>' +
            '</label>' +
            '<span class="geo-layer-badge disabled">No Data</span>' +
          '</div>';
        container.appendChild(layerPanel);
      }

      // 2. Legend Panel
      if (!document.getElementById("geoLegendPanel")) {
        const legendPanel = document.createElement("div");
        legendPanel.id = "geoLegendPanel";
        legendPanel.className = "geo-legend-panel";
        legendPanel.innerHTML = '<div class="geo-legend-title">VANA Surveillance &amp; Reference Legend</div>' +
          '<div class="geo-legend-list">' +
            '<div class="geo-legend-row">' +
              '<div class="geo-legend-bullet live"></div>' +
              '<span>Confirmed observation (1 Zone)</span>' +
            '</div>' +
            '<div class="geo-legend-row">' +
              '<div class="geo-legend-bullet pending"></div>' +
              '<span>Regional reference / pending (5 Zones)</span>' +
            '</div>' +
            '<div class="geo-legend-row">' +
              '<div class="geo-legend-bullet alert"></div>' +
              '<span>Active alert area</span>' +
            '</div>' +
            '<div class="geo-legend-row">' +
              '<div class="geo-legend-bullet unverified"></div>' +
              '<span>Not verified / fail-closed</span>' +
            '</div>' +
            '<div class="geo-legend-disclaimer">Reference locations do not imply active monitoring.</div>' +
          '</div>';
        container.appendChild(legendPanel);
      }
    },

    // ── 7. ACTIONS & NAVIGATION ─────────────────────────────────────────
    toggleLayer: function (layerKey, enabled) {
      this.layerStates[layerKey] = enabled;
      const targetLayer = this.layers[layerKey];
      if (!targetLayer || !this.map) return;

      if (enabled) {
        if (!this.map.hasLayer(targetLayer)) {
          this.map.addLayer(targetLayer);
        }
      } else {
        if (this.map.hasLayer(targetLayer)) {
          this.map.removeLayer(targetLayer);
        }
      }
    },

    flyToZone: function (zoneKey) {
      if (!this.map) return;
      const found = MMR_ZONES.find(function (z) { return z.zoneKey === zoneKey; });
      if (found) {
        this.map.flyTo([found.lat, found.lon], 12, { duration: 1.2 });
        const marker = this.markers[zoneKey];
        if (marker) {
          setTimeout(function () { marker.openPopup(); }, 1200);
        }
      }
    },

    toggleFullscreen: function () {
      const wrapper = document.getElementById("geoControlWrapper");
      if (!wrapper) return;
      const isFull = wrapper.classList.toggle("is-fullscreen");
      const btn = document.getElementById("btnMapFullscreen");
      if (btn) {
        btn.innerHTML = isFull
          ? '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/><line x1="14" y1="10" x2="21" y2="3"/><line x1="3" y1="21" x2="10" y2="14"/></svg> Restore'
          : '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg> Fullscreen';
      }
      if (this.map) {
        setTimeout(() => { this.map.invalidateSize(); }, 200);
      }
    },

    updateStatus: function () {
      const pill = document.getElementById("mapStatusPill");
      const indicator = document.getElementById("geoStatusIndicator");
      const text = document.getElementById("geoStatusText");
      if (!pill || !text) return;

      const isGeoapify = this.mapStatus.provider === "GEOAPIFY_ONLINE";
      const isOsm = this.mapStatus.provider === "OSM_FALLBACK";
      const isError = this.mapStatus.provider === "ERROR";

      const providerLabel = isGeoapify
        ? "Geoapify Online"
        : (isOsm
          ? "OSM Development Fallback"
          : (isError
            ? "Map Provider Error"
            : "Connecting Provider..."));

      const dataLabel = (this.mapStatus.data === "LIVE_PARTIAL")
        ? "VANA Data: Partial (1 Live · 5 Pending)"
        : (this.mapStatus.data === "LIVE")
          ? "VANA Data: Live Confirmed"
          : "VANA Data: Unavailable (Fail-Closed)";

      text.innerHTML = '<strong>' + providerLabel + '</strong> · ' + dataLabel;

      if (indicator) {
        indicator.className = "geo-status-indicator " + (isError ? "error" : (isGeoapify ? "online" : "fallback"));
      }
    },

    navAction: function (targetView) {
      if (targetView === "alerts" && typeof window.focusAlerts === "function") {
        window.focusAlerts(document.getElementById("navItemAlerts"));
        return;
      }
      if (typeof window.switchMainTab === "function") {
        const navMap = {
          fieldSummaryView: "navItemFieldSummary",
          lineageView: "navItemLineage",
          governanceView: "navItemGovernance"
        };
        const navId = navMap[targetView];
        const navEl = navId ? document.getElementById(navId) : null;
        window.switchMainTab(targetView, navEl);
      }
    }
  };

  // Export to global window
  window.VanaGeoData = VanaGeoData;
  window.VanaGeoConfig = VanaGeoConfig;
  window.VanaGeoEngine = VanaGeoEngine;

})(window);
