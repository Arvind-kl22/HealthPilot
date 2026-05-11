-- Ambulance and Emergency Request Tables

CREATE TABLE IF NOT EXISTS ambulances (
    id INT AUTO_INCREMENT PRIMARY KEY,
    hospital_id INT NOT NULL,
    driver_name VARCHAR(120) NOT NULL,
    driver_phone VARCHAR(30) NOT NULL,
    vehicle_number VARCHAR(40) NOT NULL,
    status ENUM('available', 'busy', 'offline') DEFAULT 'available',
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),
    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_ambulance_hospital FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ambulance_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_name VARCHAR(120) NOT NULL,
    mobile_number VARCHAR(30) NOT NULL,
    latitude DECIMAL(10, 7) NOT NULL,
    longitude DECIMAL(10, 7) NOT NULL,
    request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('pending', 'assigned', 'completed', 'cancelled') DEFAULT 'pending',
    assigned_ambulance_id INT,
    hospital_id INT,
    FOREIGN KEY (assigned_ambulance_id) REFERENCES ambulances(id) ON DELETE SET NULL,
    FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE SET NULL
);

-- For ambulance driver login, add a new table
CREATE TABLE IF NOT EXISTS ambulance_drivers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ambulance_id INT NOT NULL,
    username VARCHAR(80) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(120) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    FOREIGN KEY (ambulance_id) REFERENCES ambulances(id) ON DELETE CASCADE
);
