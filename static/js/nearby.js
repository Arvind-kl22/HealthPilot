(function () {
    const config = window.HealthPilotNearby;
    if (!config || !document.getElementById("hospitalMap")) {
        return;
    }

    const mapElement = document.getElementById("hospitalMap");
    const list = document.getElementById("hospitalResults");
    const status = document.getElementById("locationStatus");
    let map = null;
    let patientPosition = null;
    let markersAdded = false;

    function escapeHtml(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function scoreHospital(hospital) {
        const waiting = Math.max(Number(hospital.estimated_waiting_time || 1), 1);
        const travel = Math.max(Number(hospital.travel_time_minutes || 1), 1);
        return (Number(hospital.hospital_rating || 0) * 0.4)
            + (Number(hospital.doctor_rating || 0) * 0.2)
            + ((1 / waiting) * 0.2)
            + ((1 / travel) * 0.2);
    }

    function setStatus(message, icon = "bi-crosshair") {
        status.innerHTML = `<i class="bi ${icon}"></i><span>${escapeHtml(message)}</span>`;
    }

    function mapplsReady() {
        return Boolean(config.mapplsEnabled && window.mappls && typeof window.mappls.Map === "function");
    }

    function createMap() {
        if (!mapplsReady()) {
            mapElement.innerHTML = `
                <div class="map-placeholder">
                    <i class="bi bi-map"></i>
                    <strong>Mappls API key needed</strong>
                    <span>Set MAPPLS_API_KEY and restart Flask to load Mappls MapmyIndia maps.</span>
                </div>
            `;
            setStatus("Mappls API key is missing. Hospital ranking still works with approximate distance.", "bi-info-circle");
            return null;
        }

        return new mappls.Map("hospitalMap", {
            center: { lat: config.defaultCenter[0], lng: config.defaultCenter[1] },
            zoom: 12,
            zoomControl: true,
            location: true
        });
    }

    function navigationUrl(hospital) {
        if (!patientPosition) {
            return "#";
        }
        const [lat, lng] = patientPosition;
        const start = `${lat},${lng},Your Location`;
        const end = `${hospital.latitude},${hospital.longitude},${hospital.hospital_name}`;
        return `https://mappls.com/direction?places=${encodeURIComponent(start + ";" + end)}`;
    }

    function addMarkers(hospitals) {
        if (!map || markersAdded) {
            return;
        }
        markersAdded = true;

        if (patientPosition) {
            new mappls.Marker({
                map,
                position: { lat: patientPosition[0], lng: patientPosition[1] },
                popupHtml: "<strong>Your location</strong>",
                popupOptions: { openPopup: false }
            });
            map.setCenter({ lat: patientPosition[0], lng: patientPosition[1] });
        }

        hospitals.forEach((hospital, index) => {
            new mappls.Marker({
                map,
                position: { lat: hospital.latitude, lng: hospital.longitude },
                popupHtml: `<strong>${escapeHtml(hospital.hospital_name)}</strong><br>${escapeHtml(hospital.service_name)}<br>${hospital.travel_time_minutes || "--"} min travel`,
                popupOptions: { openPopup: index === 0, autoClose: true }
            });
        });
    }

    function renderHospitals(hospitals) {
        if (!hospitals.length) {
            list.innerHTML = `<div class="empty-state"><i class="bi bi-hospital"></i><p>No approved hospital currently offers this service.</p></div>`;
            addMarkers([]);
            return;
        }

        hospitals.sort((a, b) => scoreHospital(b) - scoreHospital(a));
        addMarkers(hospitals);
        list.innerHTML = hospitals.map((hospital, index) => {
            const best = index === 0;
            return `
                <article class="hospital-card ${best ? "best" : ""}">
                    <div class="hospital-card-header">
                        <div>
                            <h2>${escapeHtml(hospital.hospital_name)}</h2>
                            <p class="small text-muted mb-0">${escapeHtml(hospital.address)}, ${escapeHtml(hospital.city)}</p>
                        </div>
                        ${best ? `<span class="hospital-badge">Best match</span>` : ""}
                    </div>
                    <div class="hospital-meta">
                        <span><i class="bi bi-star-fill text-warning"></i> Hospital ${hospital.hospital_rating.toFixed(1)}</span>
                        <span><i class="bi bi-person-vcard"></i> ${escapeHtml(hospital.doctor_name)}</span>
                        <span><i class="bi bi-star"></i> Doctor ${hospital.doctor_rating.toFixed(1)}</span>
                        <span><i class="bi bi-cash-coin"></i> $${Number(hospital.consultation_fee || 0).toFixed(2)}</span>
                        <span><i class="bi bi-people"></i> Queue ${hospital.current_queue}</span>
                        <span><i class="bi bi-hourglass-split"></i> ${hospital.estimated_waiting_time} min wait</span>
                        <span><i class="bi bi-geo"></i> ${hospital.distance_km ?? "--"} km</span>
                        <span><i class="bi bi-clock-history"></i> ${hospital.travel_time_minutes ?? "--"} min travel</span>
                    </div>
                    <div class="d-flex flex-wrap gap-2">
                        <a class="btn btn-primary" href="/patient/book/${hospital.hospital_id}/${hospital.doctor_id}/${hospital.service_id}"><i class="bi bi-calendar2-plus"></i> Book</a>
                        <a class="btn btn-outline-primary" href="/patient/hospital/${hospital.hospital_id}/${hospital.service_id}"><i class="bi bi-info-circle"></i> Details</a>
                        <a class="btn btn-outline-success ${patientPosition ? "" : "disabled"}" href="${navigationUrl(hospital)}" target="_blank" rel="noreferrer"><i class="bi bi-map"></i> Open Map</a>
                    </div>
                </article>
            `;
        }).join("");
    }

    async function mapplsSummary(hospital) {
        if (!patientPosition) {
            return null;
        }
        const [lat, lng] = patientPosition;
        const params = new URLSearchParams({
            start_lat: lat,
            start_lng: lng,
            end_lat: hospital.latitude,
            end_lng: hospital.longitude
        });
        try {
            const response = await fetch(`/api/mappls/route?${params.toString()}`);
            if (!response.ok) {
                return null;
            }
            const data = await response.json();
            const route = data.routes && data.routes[0];
            if (!route) {
                return null;
            }
            return {
                distance_km: Number((route.distance / 1000).toFixed(2)),
                travel_time_minutes: Math.max(1, Math.round(route.duration / 60))
            };
        } catch (error) {
            return null;
        }
    }

    async function enrichWithMappls(hospitals) {
        const enriched = await Promise.all(hospitals.map(async (hospital) => {
            const summary = await mapplsSummary(hospital);
            return summary ? { ...hospital, ...summary } : hospital;
        }));
        renderHospitals(enriched);
        setStatus("Route times updated with Mappls MapmyIndia.", "bi-route");
    }

    async function loadHospitals(lat, lng) {
        setStatus("Finding hospitals for your location...");
        const url = `/api/hospitals?service_id=${config.serviceId}&lat=${encodeURIComponent(lat)}&lng=${encodeURIComponent(lng)}`;
        const response = await fetch(url);
        const data = await response.json();
        renderHospitals(data.hospitals || []);
        if (config.mapplsEnabled) {
            enrichWithMappls(data.hospitals || []);
        }
    }

    function useFallbackLocation() {
        patientPosition = config.defaultCenter;
        setStatus("Using demo location. Allow browser location for nearby ranking.", "bi-info-circle");
        loadHospitals(patientPosition[0], patientPosition[1]);
    }

    function startLocationFlow() {
        if (config.patientLocation && Number.isFinite(Number(config.patientLocation.lat)) && Number.isFinite(Number(config.patientLocation.lng))) {
            patientPosition = [Number(config.patientLocation.lat), Number(config.patientLocation.lng)];
            setStatus(`Using saved ${config.patientLocation.source || "patient"} location for ranking and navigation.`, "bi-geo-alt");
            loadHospitals(patientPosition[0], patientPosition[1]);
            return;
        }

        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    patientPosition = [position.coords.latitude, position.coords.longitude];
                    setStatus("Location found. Ranking hospitals now.", "bi-check2-circle");
                    loadHospitals(patientPosition[0], patientPosition[1]);
                },
                useFallbackLocation,
                { enableHighAccuracy: true, timeout: 9000, maximumAge: 60000 }
            );
        } else {
            useFallbackLocation();
        }
    }

    map = createMap();
    if (map && typeof map.addListener === "function") {
        let started = false;
        const startOnce = () => {
            if (!started) {
                started = true;
                startLocationFlow();
            }
        };
        map.addListener("load", startOnce);
        setTimeout(startOnce, 2500);
    } else {
        startLocationFlow();
    }
})();
