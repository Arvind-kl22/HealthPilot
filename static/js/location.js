(function () {
    const config = window.HealthPilotLocationPicker;
    const mapElement = document.getElementById("locationPickerMap");
    const statusElement = document.getElementById("locationPickerStatus");
    const gpsButton = document.getElementById("useGpsLocation");
    const latInput = document.getElementById("latitude");
    const lngInput = document.getElementById("longitude");
    const sourceInput = document.getElementById("locationSource");
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
            popupHtml: "<strong>Selected patient location</strong>",
            popupOptions: { openPopup: true },
            fitbounds: true,
            fitboundOptions: { padding: 120, duration: 500 }
        });
        if (marker && typeof marker.addListener === "function") {
            marker.addListener("dragend", function (event) {
                const selected = extractLatLng(event);
                if (selected && Number.isFinite(selected.lat) && Number.isFinite(selected.lng)) {
                    setLocation(selected.lat, selected.lng, "manual", "Location updated from marker drag.");
                }
            });
        }
    }

    function setLocation(lat, lng, source, message) {
        if (!Number.isFinite(Number(lat)) || !Number.isFinite(Number(lng))) {
            setStatus("Could not read that location. Please try again.", "bi-exclamation-triangle");
            return;
        }
        const cleanLat = Number(lat).toFixed(7);
        const cleanLng = Number(lng).toFixed(7);
        latInput.value = cleanLat;
        lngInput.value = cleanLng;
        sourceInput.value = source;
        setStatus(message || `Selected ${cleanLat}, ${cleanLng}`, source === "gps" ? "bi-crosshair" : "bi-geo-alt");
        updateMarker(Number(cleanLat), Number(cleanLng));
    }

    function createMap() {
        if (!mapplsReady()) {
            mapElement.innerHTML = `
                <div class="map-placeholder">
                    <i class="bi bi-map"></i>
                    <strong>Mappls API key needed</strong>
                    <span>Enter latitude and longitude manually, or set MAPPLS_API_KEY to select on map.</span>
                </div>
            `;
            return null;
        }
        return new mappls.Map("locationPickerMap", {
            center: { lat: config.defaultCenter[0], lng: config.defaultCenter[1] },
            zoom: 13,
            zoomControl: true,
            location: true
        });
    }

    gpsButton.addEventListener("click", function () {
        if (!navigator.geolocation) {
            setStatus("This browser does not support precise location.", "bi-exclamation-triangle");
            return;
        }
        setStatus("Requesting precise location permission...", "bi-crosshair");
        navigator.geolocation.getCurrentPosition(
            function (position) {
                setLocation(position.coords.latitude, position.coords.longitude, "gps", "Precise location selected.");
            },
            function () {
                setStatus("Precise location was not allowed. Click the map or enter coordinates manually.", "bi-exclamation-triangle");
            },
            { enableHighAccuracy: true, timeout: 12000, maximumAge: 30000 }
        );
    });

    latInput.addEventListener("change", function () {
        setLocation(Number(latInput.value), Number(lngInput.value), "manual", "Manual location updated.");
    });
    lngInput.addEventListener("change", function () {
        setLocation(Number(latInput.value), Number(lngInput.value), "manual", "Manual location updated.");
    });

    map = createMap();

    function initializeMapSelection() {
        if (!map) {
            if (config.existingLocation) {
                setStatus("Saved location loaded. Map selection needs a Mappls API key.", "bi-check2-circle");
            }
            return;
        }
        if (typeof map.addListener === "function") {
            map.addListener("click", function (event) {
                const selected = extractLatLng(event);
                if (selected && Number.isFinite(selected.lat) && Number.isFinite(selected.lng)) {
                    setLocation(selected.lat, selected.lng, "manual", "Location selected from map.");
                } else {
                    setStatus("Could not read map click location. Try again.", "bi-exclamation-triangle");
                }
            });
        }
        if (config.existingLocation) {
            setLocation(Number(config.existingLocation.lat), Number(config.existingLocation.lng), config.existingLocation.source || "manual", "Saved location loaded.");
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
