(function () {
    const config = window.HealthPilotRequestTrack;
    const mapElement = document.getElementById('ambulanceTrackMap');
    const mapWrapper = document.getElementById('ambulanceTrackMapWrapper');
    const pendingState = document.getElementById('trackingPendingState');
    if (!config || !mapElement) {
        return;
    }

    const TRACKABLE_STATUSES = new Set(['assigned', 'reached_patient', 'reached_hospital', 'completed']);

    let map = null;
    let patientMarker = null;
    let ambulanceMarker = null;
    let routeLine = null;
    let refreshTimer = null;
    let trackingEnabled = Boolean(config.trackingEnabled);

    function mapplsReady() {
        return Boolean(config.mapplsEnabled && window.mappls && typeof window.mappls.Map === 'function');
    }

    function shouldTrack(state) {
        const status = String(state.status || '').toLowerCase();
        return Boolean(state.assigned_ambulance_id) && TRACKABLE_STATUSES.has(status);
    }

    function setTrackingVisibility(enabled) {
        if (mapWrapper) {
            mapWrapper.classList.toggle('d-none', !enabled);
        }
        if (pendingState) {
            pendingState.classList.toggle('d-none', enabled);
        }
    }

    function createMap() {
        if (!mapplsReady()) {
            mapElement.innerHTML = `
                <div class="map-placeholder">
                    <i class="bi bi-map"></i>
                    <strong>Mappls API key required</strong>
                    <span>Set MAPPLS_WEB_API_KEY to show the live ambulance tracking map.</span>
                </div>
            `;
            return null;
        }
        return new mappls.Map('ambulanceTrackMap', {
            center: { lat: Number(config.patientLocation.lat), lng: Number(config.patientLocation.lng) },
            zoom: 13,
            zoomControl: true,
            location: true
        });
    }

    function removeLayer(layer) {
        if (layer && typeof layer.remove === 'function') {
            layer.remove();
        }
    }

    function clearMapLayers() {
        removeLayer(patientMarker);
        removeLayer(ambulanceMarker);
        removeLayer(routeLine);
        patientMarker = null;
        ambulanceMarker = null;
        routeLine = null;
    }

    function addMarker(opts) {
        return new mappls.Marker({
            map,
            position: opts.position,
            popupHtml: opts.popupHtml,
            popupOptions: { openPopup: opts.openPopup || false }
        });
    }

    function updateStatusMessage(message) {
        const el = document.getElementById('trackingMessage');
        if (el) {
            el.textContent = message;
        }
    }

    async function drawRoute(ambulanceLat, ambulanceLng, patientLat, patientLng) {
        removeLayer(routeLine);
        if (!map || ambulanceLat == null || ambulanceLng == null) {
            return;
        }
        const params = new URLSearchParams({
            start_lat: Number(ambulanceLat),
            start_lng: Number(ambulanceLng),
            end_lat: Number(patientLat),
            end_lng: Number(patientLng)
        });

        try {
            const response = await fetch(`/api/mappls/route?${params.toString()}`);
            if (!response.ok) {
                throw new Error('Route service unavailable');
            }
            const data = await response.json();
            const route = data.routes && data.routes[0];
            if (!route || !route.geometry || route.geometry.type !== 'LineString') {
                throw new Error('Invalid route geometry');
            }
            const path = route.geometry.coordinates.map((coord) => ({ lat: coord[1], lng: coord[0] }));
            routeLine = new mappls.Polyline({
                map,
                paths: path,
                strokeColor: '#198754',
                strokeOpacity: 0.9,
                strokeWeight: 6,
                fitbounds: true,
                fitboundOptions: { padding: 100, duration: 500 }
            });
        } catch (error) {
            console.warn('Unable to draw route:', error);
        }
    }

    function renderMap(state) {
        if (!map) {
            return;
        }
        clearMapLayers();

        const bounds = new mappls.LatLngBounds();
        patientMarker = addMarker({
            position: { lat: Number(state.patient_lat), lng: Number(state.patient_lng) },
            popupHtml: '<strong>Patient Location</strong>',
            openPopup: true
        });
        bounds.extend(patientMarker.getPosition());

        if (Number.isFinite(Number(state.ambulance_lat)) && Number.isFinite(Number(state.ambulance_lng))) {
            ambulanceMarker = addMarker({
                position: { lat: Number(state.ambulance_lat), lng: Number(state.ambulance_lng) },
                popupHtml: `<strong>Ambulance #${state.assigned_ambulance_id}</strong><br>${state.hospital_name || 'Hospital'}<br>${state.vehicle_number || 'Vehicle'}`,
                openPopup: false
            });
            bounds.extend(ambulanceMarker.getPosition());
            drawRoute(state.ambulance_lat, state.ambulance_lng, state.patient_lat, state.patient_lng);

            if (String(state.status || '').toLowerCase() === 'completed') {
                updateStatusMessage('Ride completed. Displaying last known route and location.');
            } else {
                updateStatusMessage('Driver accepted. Live ambulance tracking is active.');
            }
        } else {
            updateStatusMessage('Driver accepted. Waiting for ambulance location update...');
        }

        if (bounds && bounds.getCount && bounds.getCount() > 0) {
            map.fitBounds(bounds, { padding: 100, duration: 500 });
        }
    }

    async function refreshRequestStatus() {
        try {
            const response = await fetch(`/api/ambulance/request/${config.requestId}/status`);
            if (!response.ok) {
                throw new Error('Unable to load request status');
            }
            const data = await response.json();
            const statusText = data.status ? data.status.replace(/_/g, ' ').replace(/\b\w/g, (m) => m.toUpperCase()) : 'Unknown';
            const statusEl = document.getElementById('requestStatus');
            if (statusEl) {
                statusEl.textContent = statusText;
            }

            const enableTrackingNow = shouldTrack(data);
            if (!enableTrackingNow) {
                trackingEnabled = false;
                setTrackingVisibility(false);
                clearMapLayers();
                updateStatusMessage('Waiting for driver acceptance. Live tracking will start automatically after acceptance.');
                return;
            }

            if (!trackingEnabled) {
                trackingEnabled = true;
                setTrackingVisibility(true);
            }
            if (!map) {
                map = createMap();
            }
            renderMap(data);
        } catch (error) {
            console.warn('Tracking refresh failed:', error);
        }
    }

    setTrackingVisibility(trackingEnabled);
    if (trackingEnabled) {
        map = createMap();
    }
    refreshRequestStatus();
    refreshTimer = setInterval(refreshRequestStatus, 7000);
})();
