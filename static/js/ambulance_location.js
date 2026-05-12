// ambulance_location.js
// Handles Maple Map API for ambulance request location

document.addEventListener('DOMContentLoaded', function () {
    // Initialize Maple Map
    var map = new MapleMap('maple-map', {
        center: { lat: 28.6139, lng: 77.2090 }, // Default to Delhi, update as needed
        zoom: 14
    });

    var latInput = document.getElementById('latitude');
    var lngInput = document.getElementById('longitude');
    var initialLat = parseFloat(latInput.value);
    var initialLng = parseFloat(lngInput.value);

    // Add marker for manual adjustment
    var marker = map.addMarker({
        position: map.getCenter(),
        draggable: true
    });

    if (!isNaN(initialLat) && !isNaN(initialLng)) {
        map.setCenter({ lat: initialLat, lng: initialLng });
        setLatLng(initialLat, initialLng);
    } else if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function (position) {
            var lat = position.coords.latitude;
            var lng = position.coords.longitude;
            map.setCenter({ lat: lat, lng: lng });
            setLatLng(lat, lng);
        });
    }

    marker.on('dragend', function (e) {
        var pos = marker.getPosition();
        setLatLng(pos.lat, pos.lng);
    });

    // Update hidden fields
    function setLatLng(lat, lng) {
        document.getElementById('latitude').value = lat;
        document.getElementById('longitude').value = lng;
        marker.setPosition({ lat: lat, lng: lng });
    }

    // Allow clicking on map to move marker
    map.on('click', function (e) {
        setLatLng(e.latLng.lat, e.latLng.lng);
    });
});
