(function () {
    const config = window.HealthPilotAmbulanceDashboard;
    const mapElement = document.getElementById('ambulanceDashboardMap');
    if (!config || !mapElement) {
        return;
    }

    let map = null;
    let driverMarker = null;
    let patientMarker = null;
    let routeLine = null;
    let refreshTimer = null;
    let mapClickRegistered = false;

    function mapplsReady() {
        return Boolean(config.mapplsEnabled && window.mappls && typeof window.mappls.Map === 'function');
    }

    function createMap() {
        if (!mapplsReady()) {
            mapElement.innerHTML = `
                <div class="map-placeholder">
                    <i class="bi bi-map"></i>
                    <strong>Mappls API key required</strong>
                    <span>Add MAPPLS_API_KEY to your environment to show the live ambulance map.</span>
                </div>
            `;
            return null;
        }
        return new mappls.Map('ambulanceDashboardMap', {
            center: { lat: Number(config.defaultCenter[0]), lng: Number(config.defaultCenter[1]) },
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

    function extractLatLng(event) {
        const raw = event && (event.lngLat || event.latLng || event.latlng);
        if (!raw) {
            return null;
        }
        if (Array.isArray(raw) && raw.length >= 2) {
            return { lat: Number(raw[1]), lng: Number(raw[0]) };
        }
        if (typeof raw === 'object') {
            const lat = raw.lat ?? raw.latitude;
            const lng = raw.lng ?? raw.lon ?? raw.longitude;
            if (lat !== undefined && lng !== undefined) {
                return { lat: Number(lat), lng: Number(lng) };
            }
        }
        return null;
    }

    function updateLatLngInputs(lat, lng) {
        const latitudeInput = document.getElementById('latitude');
        const longitudeInput = document.getElementById('longitude');
        if (latitudeInput && longitudeInput) {
            latitudeInput.value = Number(lat).toFixed(7);
            longitudeInput.value = Number(lng).toFixed(7);
        }
        const statusEl = document.getElementById('locationDetectStatus');
        if (statusEl) {
            statusEl.textContent = 'Location selected from map. Submit to save.';
            statusEl.className = 'small text-success';
        }
    }

    function addMarker(map, info) {
        const draggable = info.draggable || false;
        const markerOptions = {
            map,
            position: { lat: Number(info.lat), lng: Number(info.lng) },
            popupHtml: `<strong>${info.title}</strong><br>${info.subtitle || ''}`,
            draggable,
            popupOptions: { openPopup: true }
        };
        if (info.iconUrl) {
            markerOptions.icon = info.iconUrl;
        }
        let marker;
        try {
            marker = new mappls.Marker(markerOptions);
        } catch (error) {
            console.warn('Mappls marker icon failed, using default marker.', error);
            delete markerOptions.icon;
            marker = new mappls.Marker(markerOptions);
        }
        if (draggable && typeof marker.addListener === 'function') {
            marker.addListener('dragend', function (event) {
                const pos = extractLatLng(event);
                if (pos && Number.isFinite(pos.lat) && Number.isFinite(pos.lng)) {
                    updateLatLngInputs(pos.lat, pos.lng);
                }
            });
        }
        return marker;
    }

    async function drawRouteLine(map, driverInfo, assignment) {
        removeLayer(routeLine);
        if (!assignment) {
            return null;
        }

        const params = new URLSearchParams({
            start_lat: Number(driverInfo.lat),
            start_lng: Number(driverInfo.lng),
            end_lat: Number(assignment.lat),
            end_lng: Number(assignment.lng)
        });

        try {
            const response = await fetch(`/api/mappls/route?${params.toString()}`);
            if (!response.ok) {
                throw new Error('Route request failed');
            }
            const data = await response.json();
            const route = data.routes && data.routes[0];
            const geometry = route && route.geometry;
            if (!route || !geometry || geometry.type !== 'LineString' || !Array.isArray(geometry.coordinates)) {
                throw new Error('Route geometry unavailable');
            }
            const path = geometry.coordinates.map((point) => ({ lat: point[1], lng: point[0] }));
            routeLine = new mappls.Polyline({
                map,
                paths: path,
                strokeColor: '#dc3545',
                strokeOpacity: 0.9,
                strokeWeight: 6,
                fitbounds: true,
                fitboundOptions: { padding: 100, duration: 500 }
            });
            return routeLine;
        } catch (error) {
            console.warn('Mappls route fetch failed, drawing straight line fallback.', error);
            routeLine = new mappls.Polyline({
                map,
                paths: [
                    { lat: Number(driverInfo.lat), lng: Number(driverInfo.lng) },
                    { lat: Number(assignment.lat), lng: Number(assignment.lng) }
                ],
                strokeColor: '#dc3545',
                strokeOpacity: 0.8,
                strokeWeight: 5,
                fitbounds: true,
                fitboundOptions: { padding: 100, duration: 500 }
            });
            return routeLine;
        }
    }

    function registerMapClickHandler() {
        if (!map || mapClickRegistered || typeof map.addListener !== 'function') {
            return;
        }
        map.addListener('click', function (event) {
            const pos = extractLatLng(event);
            if (pos && Number.isFinite(pos.lat) && Number.isFinite(pos.lng)) {
                updateLatLngInputs(pos.lat, pos.lng);
                if (driverMarker && typeof driverMarker.setPosition === 'function') {
                    driverMarker.setPosition({ lat: pos.lat, lng: pos.lng });
                }
            }
        });
        mapClickRegistered = true;
    }

    async function updateMap(data) {
        if (!map) {
            return;
        }
        removeLayer(driverMarker);
        removeLayer(patientMarker);
        removeLayer(routeLine);

        if (!data || !data.driver) {
            console.warn('Ambulance dashboard status response missing driver data', data);
            return;
        }
        const driverLat = Number(data.driver.lat);
        const driverLng = Number(data.driver.lng);
        if (!Number.isFinite(driverLat) || !Number.isFinite(driverLng)) {
            console.warn('Ambulance dashboard status response has invalid driver coordinates', data.driver);
            return;
        }

        driverMarker = addMarker(map, {
            lat: data.driver.lat,
            lng: data.driver.lng,
            title: `Ambulance: ${data.driver.vehicle_number || 'Vehicle'}`,
            subtitle: `Status: ${data.driver.status || 'unknown'}`,
            draggable: true
        });

        registerMapClickHandler();

        let bounds = new mappls.LatLngBounds();
        bounds.extend(driverMarker.getPosition());

        if (data.assignment && Number.isFinite(Number(data.assignment.lat)) && Number.isFinite(Number(data.assignment.lng))) {
            patientMarker = addMarker(map, {
                lat: data.assignment.lat,
                lng: data.assignment.lng,
                title: 'Current assignment',
                subtitle: `Patient: ${data.assignment.patient_name || 'unknown'}`,
                draggable: false
            });
            bounds.extend(patientMarker.getPosition());
            routeLine = await drawRouteLine(map, data.driver, data.assignment);
        }

        if (bounds && bounds.getCount && bounds.getCount() > 0) {
            map.fitBounds(bounds, { padding: 100, duration: 500 });
        }
    }

    async function refreshStatus() {
        try {
            const response = await fetch('/ambulance/dashboard/status');
            if (!response.ok) {
                throw new Error('Unable to fetch ambulance status');
            }
            const data = await response.json();
            await updateMap(data);
        } catch (error) {
            console.warn('Ambulance dashboard refresh failed:', error);
        }
    }

    function setDetectionStatus(message, severity) {
        const statusEl = document.getElementById('locationDetectStatus');
        if (!statusEl) {
            return;
        }
        statusEl.textContent = message;
        statusEl.className = `small text-${severity}`;
    }

    function detectCurrentLocation() {
        const button = document.getElementById('detectLocationButton');
        if (!navigator.geolocation) {
            setDetectionStatus('Geolocation is not supported by this browser.', 'danger');
            return;
        }
        if (button) {
            button.disabled = true;
            button.textContent = 'Detecting...';
        }
        setDetectionStatus('Acquiring current location...', 'muted');
        navigator.geolocation.getCurrentPosition(
            function (position) {
                const latitudeInput = document.getElementById('latitude');
                const longitudeInput = document.getElementById('longitude');
                if (latitudeInput && longitudeInput) {
                    latitudeInput.value = position.coords.latitude.toFixed(7);
                    longitudeInput.value = position.coords.longitude.toFixed(7);
                }
                setDetectionStatus('Location detected. Submit to save.', 'success');
                if (button) {
                    button.disabled = false;
                    button.innerHTML = '<i class="bi bi-geo-alt"></i> Use Current Location';
                }
                if (map) {
                    map.setCenter({ lat: position.coords.latitude, lng: position.coords.longitude });
                }
            },
            function (error) {
                setDetectionStatus('Unable to detect location. Please check permissions.', 'danger');
                if (button) {
                    button.disabled = false;
                    button.innerHTML = '<i class="bi bi-geo-alt"></i> Use Current Location';
                }
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 30000
            }
        );
    }

    function startRefreshLoop() {
        if (refreshTimer) {
            clearInterval(refreshTimer);
        }
        refreshTimer = setInterval(refreshStatus, 5000);
    }

    map = createMap();

    if (map && typeof map.addListener === 'function') {
        map.addListener('load', function () {
            refreshStatus();
            startRefreshLoop();
        });
        setTimeout(function () {
            refreshStatus();
            startRefreshLoop();
        }, 1500);
    } else {
        refreshStatus();
    }

    const detectButton = document.getElementById('detectLocationButton');
    if (detectButton) {
        detectButton.addEventListener('click', function () {
            detectCurrentLocation();
        });
    }
})();