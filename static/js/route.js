(function () {
    const config = window.HealthPilotRoute;
    if (!config || !document.getElementById("routeMap")) {
        return;
    }

    const mapElement = document.getElementById("routeMap");
    const distanceEl = document.getElementById("routeDistance");
    const durationEl = document.getElementById("routeDuration");
    const navLink = document.getElementById("openNavigation");
    let map = null;

    function mapplsReady() {
        return Boolean(config.mapplsEnabled && window.mappls && typeof window.mappls.Map === "function");
    }

    function createMap() {
        if (!mapplsReady()) {
            mapElement.innerHTML = `
                <div class="map-placeholder">
                    <i class="bi bi-map"></i>
                    <strong>Mappls API key needed</strong>
                    <span>Set MAPPLS_API_KEY and restart Flask to load Mappls MapmyIndia navigation.</span>
                </div>
            `;
            return null;
        }

        return new mappls.Map("routeMap", {
            center: { lat: Number(config.hospitalLat), lng: Number(config.hospitalLng) },
            zoom: 12,
            zoomControl: true,
            location: true
        });
    }

    function fallbackDistanceKm(lat1, lon1, lat2, lon2) {
        const radius = 6371;
        const phi1 = lat1 * Math.PI / 180;
        const phi2 = lat2 * Math.PI / 180;
        const deltaPhi = (lat2 - lat1) * Math.PI / 180;
        const deltaLambda = (lon2 - lon1) * Math.PI / 180;
        const a = Math.sin(deltaPhi / 2) ** 2 + Math.cos(phi1) * Math.cos(phi2) * Math.sin(deltaLambda / 2) ** 2;
        return radius * (2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)));
    }

    function drawFallback(patientLat, patientLng) {
        const hospital = [Number(config.hospitalLat), Number(config.hospitalLng)];
        if (map) {
            new mappls.Marker({
                map,
                position: { lat: patientLat, lng: patientLng },
                popupHtml: "<strong>Your location</strong>"
            });
            new mappls.Marker({
                map,
                position: { lat: hospital[0], lng: hospital[1] },
                popupHtml: `<strong>${config.hospitalName}</strong>`
            });
            new mappls.Polyline({
                map,
                paths: [
                    { lat: patientLat, lng: patientLng },
                    { lat: hospital[0], lng: hospital[1] }
                ],
                strokeColor: "#1266d6",
                strokeOpacity: 0.85,
                strokeWeight: 5,
                fitbounds: true,
                fitboundOptions: { padding: 120, duration: 1000 }
            });
        }
        const distance = fallbackDistanceKm(patientLat, patientLng, hospital[0], hospital[1]);
        distanceEl.textContent = distance.toFixed(2);
        durationEl.textContent = Math.max(1, Math.round((distance / 35) * 60));
    }

    async function drawRoute(patientLat, patientLng) {
        const hospitalLat = Number(config.hospitalLat);
        const hospitalLng = Number(config.hospitalLng);
        const start = `${patientLat},${patientLng},Your Location`;
        const end = `${hospitalLat},${hospitalLng},${config.hospitalName}`;
        navLink.href = `https://mappls.com/direction?places=${encodeURIComponent(start + ";" + end)}`;

        if (!map) {
            drawFallback(patientLat, patientLng);
            return;
        }

        new mappls.Marker({
            map,
            position: { lat: patientLat, lng: patientLng },
            popupHtml: "<strong>Your location</strong>"
        });
        new mappls.Marker({
            map,
            position: { lat: hospitalLat, lng: hospitalLng },
            popupHtml: `<strong>${config.hospitalName}</strong>`,
            popupOptions: { openPopup: true }
        });

        const params = new URLSearchParams({
            start_lat: patientLat,
            start_lng: patientLng,
            end_lat: hospitalLat,
            end_lng: hospitalLng
        });
        try {
            const response = await fetch(`/api/mappls/route?${params.toString()}`);
            if (!response.ok) {
                throw new Error("Mappls route unavailable");
            }
            const data = await response.json();
            const route = data.routes && data.routes[0];
            const geometry = route && route.geometry;
            if (!route || !geometry || geometry.type !== "LineString" || !Array.isArray(geometry.coordinates)) {
                throw new Error("Route unavailable");
            }
            const path = geometry.coordinates.map((point) => ({ lat: point[1], lng: point[0] }));
            new mappls.Polyline({
                map,
                paths: path,
                strokeColor: "#1266d6",
                strokeOpacity: 0.9,
                strokeWeight: 6,
                fitbounds: true,
                fitboundOptions: { padding: 120, duration: 1000 },
                popupHtml: "Route to hospital"
            });
            distanceEl.textContent = (route.distance / 1000).toFixed(2);
            durationEl.textContent = Math.max(1, Math.round(route.duration / 60));
        } catch (error) {
            drawFallback(patientLat, patientLng);
        }
    }

    function useFallback() {
        drawRoute(config.defaultCenter[0], config.defaultCenter[1]);
    }

    map = createMap();

    function startNavigationFlow() {
        if (config.patientLocation && Number.isFinite(Number(config.patientLocation.lat)) && Number.isFinite(Number(config.patientLocation.lng))) {
            drawRoute(Number(config.patientLocation.lat), Number(config.patientLocation.lng));
            return;
        }

        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => drawRoute(position.coords.latitude, position.coords.longitude),
                useFallback,
                { enableHighAccuracy: true, timeout: 9000, maximumAge: 60000 }
            );
        } else {
            useFallback();
        }
    }

    if (map && typeof map.addListener === "function") {
        let started = false;
        const startOnce = () => {
            if (!started) {
                started = true;
                startNavigationFlow();
            }
        };
        map.addListener("load", startOnce);
        setTimeout(startOnce, 2500);
    } else {
        startNavigationFlow();
    }
})();
