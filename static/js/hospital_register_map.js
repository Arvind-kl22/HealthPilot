(function () {
    const config = window.HealthPilotHospitalRegisterMap;
    const mapElement = document.getElementById("hospitalRegisterMap");
    const statusElement = document.getElementById("hospitalRegisterLocationStatus");
    const gpsButton = document.getElementById("useHospitalCurrentLocation");
    const latInput = document.getElementById("latitude");
    const lngInput = document.getElementById("longitude");
    if (!config || !mapElement || !latInput || !lngInput) {
        return;
    }

    let map = null;
    let marker = null;

    function escapeHtml(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function setStatus(message, icon = "bi-info-circle") {
        statusElement.innerHTML = `<i class="bi ${icon}"></i><span>${escapeHtml(message)}</span>`;
    }

    function mapplsReady() {
        return Boolean(config.mapplsEnabled && window.mappls && typeof window.mappls.Map === "function");
    }

    function extractLatLng(event) {
        const raw = event && (event.lngLat || event.latLng || event.latlng);
        if (!raw) {
            return null;
        }
        if (Array.isArray(raw) && raw.length >= 2) {
            return { lng: Number(raw[0]), lat: Number(raw[1]) };
        }
        if (typeof raw === "object") {
            const lat = raw.lat ?? raw.latitude;
            const lng = raw.lng ?? raw.lon ?? raw.longitude;
            if (lat !== undefined && lng !== undefined) {
                return { lat: Number(lat), lng: Number(lng) };
            }
        }
        if (typeof raw === "string") {
            const values = raw.match(/-?\d+(\.\d+)?/g);
            if (values && values.length >= 2) {
                return { lng: Number(values[0]), lat: Number(values[1]) };
            }
        }
        return null;
    }

    function updateMarker(lat, lng) {
        if (!map) {
            return;
        }
        if (marker && typeof marker.remove === "function") {
            marker.remove();
        }
        marker = new mappls.Marker({
            map,
            position: { lat, lng },
            draggable: true,
            popupHtml: "<strong>Selected hospital location</strong>",
            popupOptions: { openPopup: true },
            fitbounds: true,
            fitboundOptions: { padding: 120, duration: 500 }
        });
        if (marker && typeof marker.addListener === "function") {
            marker.addListener("dragend", function (event) {
                const selected = extractLatLng(event);
                if (selected && Number.isFinite(selected.lat) && Number.isFinite(selected.lng)) {
                    setLocation(selected.lat, selected.lng, "Location updated from marker drag.");
                }
            });
        }
    }

    function setLocation(lat, lng, message) {
        if (!Number.isFinite(Number(lat)) || !Number.isFinite(Number(lng))) {
            setStatus("Could not read that location. Please try again.", "bi-exclamation-triangle");
            return;
        }
        const cleanLat = Number(lat).toFixed(7);
        const cleanLng = Number(lng).toFixed(7);
        latInput.value = cleanLat;
        lngInput.value = cleanLng;
        setStatus(message || `Selected ${cleanLat}, ${cleanLng}`, "bi-geo-alt");
        updateMarker(Number(cleanLat), Number(cleanLng));
    }

    function createMap() {
        if (!mapplsReady()) {
            mapElement.innerHTML = `
                <div class="map-placeholder">
                    <i class="bi bi-map"></i>
                    <strong>Mappls API key needed</strong>
                    <span>Enter latitude and longitude manually, or set MAPPLS_API_KEY to select from map.</span>
                </div>
            `;
            setStatus("Map key missing. Latitude and longitude can still be entered manually.", "bi-info-circle");
            return null;
        }
        return new mappls.Map("hospitalRegisterMap", {
            center: { lat: config.defaultCenter[0], lng: config.defaultCenter[1] },
            zoom: 12,
            zoomControl: true,
            location: true
        });
    }

    if (gpsButton) {
        gpsButton.addEventListener("click", function () {
            if (!navigator.geolocation) {
                setStatus("This browser does not support current location.", "bi-exclamation-triangle");
                return;
            }
            setStatus("Requesting current location permission...", "bi-crosshair");
            navigator.geolocation.getCurrentPosition(
                function (position) {
                    setLocation(position.coords.latitude, position.coords.longitude, "Current location selected.");
                },
                function () {
                    setStatus("Current location was not allowed. Click the map or enter coordinates manually.", "bi-exclamation-triangle");
                },
                { enableHighAccuracy: true, timeout: 12000, maximumAge: 30000 }
            );
        });
    }

    latInput.addEventListener("change", function () {
        setLocation(Number(latInput.value), Number(lngInput.value), "Manual location updated.");
    });
    lngInput.addEventListener("change", function () {
        setLocation(Number(latInput.value), Number(lngInput.value), "Manual location updated.");
    });

    map = createMap();

    function initializeMapSelection() {
        if (!map) {
            return;
        }
        if (typeof map.addListener === "function") {
            map.addListener("click", function (event) {
                const selected = extractLatLng(event);
                if (selected && Number.isFinite(selected.lat) && Number.isFinite(selected.lng)) {
                    setLocation(selected.lat, selected.lng, "Hospital location selected from map.");
                } else {
                    setStatus("Could not read map click location. Try again.", "bi-exclamation-triangle");
                }
            });
        }
    }

    if (map && typeof map.addListener === "function") {
        let initialized = false;
        const initializeOnce = function () {
            if (!initialized) {
                initialized = true;
                initializeMapSelection();
            }
        };
        map.addListener("load", initializeOnce);
        setTimeout(initializeOnce, 2500);
    } else {
        initializeMapSelection();
    }
})();
