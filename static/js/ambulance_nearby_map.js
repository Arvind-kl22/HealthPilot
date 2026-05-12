(function () {
    const config = window.HealthPilotNearby;
    if (!config || !document.getElementById('ambulanceNearbyMap')) {
        return;
    }

    const mapElement = document.getElementById('ambulanceNearbyMap');
    let map = null;

    function mapplsReady() {
        return Boolean(config.mapplsEnabled && window.mappls && typeof window.mappls.Map === 'function');
    }

    function createMap() {
        if (!mapplsReady()) {
            mapElement.innerHTML = `
                <div class="map-placeholder">
                    <i class="bi bi-map"></i>
                    <strong>Mappls API key needed</strong>
                    <span>Set MAPPLS_WEB_API_KEY and restart Flask to load the nearby ambulance map.</span>
                </div>
            `;
            return null;
        }

        return new mappls.Map('ambulanceNearbyMap', {
            center: { lat: config.defaultCenter[0], lng: config.defaultCenter[1] },
            zoom: 12,
            zoomControl: true,
            location: true
        });
    }

    function addMarker(options) {
        return new mappls.Marker({
            map,
            position: options.position,
            popupHtml: options.popupHtml,
            popupOptions: { openPopup: options.openPopup || false }
        });
    }

    function renderMarkers() {
        if (!map) {
            return;
        }

        const bounds = new mappls.LatLngBounds();
        const patient = config.patientLocation;

        if (patient && Number.isFinite(Number(patient.lat)) && Number.isFinite(Number(patient.lng))) {
            const patientMarker = addMarker({
                position: { lat: Number(patient.lat), lng: Number(patient.lng) },
                popupHtml: `<strong>Patient location</strong><br>Lat: ${Number(patient.lat).toFixed(6)}, Lng: ${Number(patient.lng).toFixed(6)}`,
                openPopup: true
            });
            bounds.extend(patientMarker.getPosition());
        }

        (config.ambulances || []).forEach((amb) => {
            if (!Number.isFinite(Number(amb.latitude)) || !Number.isFinite(Number(amb.longitude))) {
                return;
            }
            const marker = addMarker({
                position: { lat: Number(amb.latitude), lng: Number(amb.longitude) },
                popupHtml: `
                    <strong>Ambulance #${amb.id}</strong><br>
                    Hospital: ${amb.hospital_name}<br>
                    Driver: ${amb.driver_name}<br>
                    Distance: ${Number(amb.distance || 0).toFixed(2)} km
                `,
                openPopup: false
            });
            bounds.extend(marker.getPosition());
        });

        if (bounds && bounds.getCount && bounds.getCount() > 0) {
            map.fitBounds(bounds, { padding: 80, duration: 600 });
        }
    }

    map = createMap();
    renderMarkers();
})();
