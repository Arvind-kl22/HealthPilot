CREATE DATABASE IF NOT EXISTS healthpilot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE healthpilot;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(160) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('patient', 'hospital_admin', 'super_admin') NOT NULL,
    phone VARCHAR(30),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS hospitals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT NULL,
    hospital_name VARCHAR(180) NOT NULL,
    address VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    latitude DECIMAL(10, 7) NOT NULL,
    longitude DECIMAL(10, 7) NOT NULL,
    contact VARCHAR(40),
    opening_time TIME,
    closing_time TIME,
    rating DECIMAL(3, 2) DEFAULT 4.00,
    status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    CONSTRAINT fk_hospitals_admin FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    hospital_id INT NOT NULL,
    department_name VARCHAR(120) NOT NULL,
    description TEXT,
    CONSTRAINT fk_departments_hospital FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE CASCADE,
    UNIQUE KEY uq_department_hospital (hospital_id, department_name)
);

CREATE TABLE IF NOT EXISTS doctors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    hospital_id INT NOT NULL,
    doctor_name VARCHAR(140) NOT NULL,
    specialization VARCHAR(140) NOT NULL,
    qualification VARCHAR(140),
    experience INT DEFAULT 0,
    consultation_fee DECIMAL(10, 2) DEFAULT 0,
    rating DECIMAL(3, 2) DEFAULT 4.00,
    CONSTRAINT fk_doctors_hospital FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS services (
    id INT AUTO_INCREMENT PRIMARY KEY,
    service_name VARCHAR(120) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS doctor_services (
    id INT AUTO_INCREMENT PRIMARY KEY,
    doctor_id INT NOT NULL,
    service_id INT NOT NULL,
    CONSTRAINT fk_doctor_services_doctor FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE,
    CONSTRAINT fk_doctor_services_service FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
    UNIQUE KEY uq_doctor_service (doctor_id, service_id)
);

CREATE TABLE IF NOT EXISTS doctor_availability (
    id INT AUTO_INCREMENT PRIMARY KEY,
    doctor_id INT NOT NULL,
    day VARCHAR(20) NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    CONSTRAINT fk_availability_doctor FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS appointments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    hospital_id INT NOT NULL,
    doctor_id INT NOT NULL,
    service_id INT NOT NULL,
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    token_number VARCHAR(40) NOT NULL,
    status ENUM('pending', 'accepted', 'rejected', 'completed') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_appointments_patient FOREIGN KEY (patient_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_appointments_hospital FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE CASCADE,
    CONSTRAINT fk_appointments_doctor FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE,
    CONSTRAINT fk_appointments_service FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS queues (
    id INT AUTO_INCREMENT PRIMARY KEY,
    hospital_id INT NOT NULL,
    service_id INT NOT NULL,
    current_queue INT DEFAULT 0,
    estimated_waiting_time INT DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_queues_hospital FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE CASCADE,
    CONSTRAINT fk_queues_service FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
    UNIQUE KEY uq_queue_service (hospital_id, service_id)
);

CREATE TABLE IF NOT EXISTS feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    hospital_id INT NOT NULL,
    doctor_id INT NOT NULL,
    rating INT NOT NULL,
    cleanliness_rating INT NOT NULL,
    waiting_rating INT NOT NULL,
    staff_rating INT NOT NULL,
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_feedback_patient FOREIGN KEY (patient_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_feedback_hospital FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE CASCADE,
    CONSTRAINT fk_feedback_doctor FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS complaints (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    hospital_id INT NOT NULL,
    complaint_text TEXT NOT NULL,
    status ENUM('open', 'in_review', 'resolved') DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_complaints_patient FOREIGN KEY (patient_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_complaints_hospital FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE CASCADE
);

INSERT IGNORE INTO users (id, name, email, password, role, phone) VALUES
(1, 'Avery Patient', 'patient@healthpilot.local', 'pbkdf2_sha256$260000$patient-demo$fbf00b26ebe09b54733889b6d48c187791650f01d89f7b7a7b224f576166d07f', 'patient', '+1-555-0100'),
(2, 'Maya Hospital Admin', 'hospital@healthpilot.local', 'pbkdf2_sha256$260000$hospital-demo$0d0cb0d4128e2331a0decbb4ab53f254e13ddd5b1918327df4bc3fd12cdd30ac', 'hospital_admin', '+1-555-0110'),
(3, 'Noah Green Admin', 'greenvalley@healthpilot.local', 'pbkdf2_sha256$260000$hospital-demo$0d0cb0d4128e2331a0decbb4ab53f254e13ddd5b1918327df4bc3fd12cdd30ac', 'hospital_admin', '+1-555-0120'),
(4, 'Lena Northside Admin', 'northside@healthpilot.local', 'pbkdf2_sha256$260000$hospital-demo$0d0cb0d4128e2331a0decbb4ab53f254e13ddd5b1918327df4bc3fd12cdd30ac', 'hospital_admin', '+1-555-0130'),
(5, 'Owen Bright Admin', 'brightsmile@healthpilot.local', 'pbkdf2_sha256$260000$hospital-demo$0d0cb0d4128e2331a0decbb4ab53f254e13ddd5b1918327df4bc3fd12cdd30ac', 'hospital_admin', '+1-555-0140'),
(6, 'HealthPilot Super Admin', 'super@healthpilot.local', 'pbkdf2_sha256$260000$super-demo$a9499b8f2a69e11faebf7d59168fd87958bde18253d987ed4010e365fac6fb2e', 'super_admin', '+1-555-0199');

INSERT IGNORE INTO hospitals (id, admin_id, hospital_name, address, city, latitude, longitude, contact, opening_time, closing_time, rating, status) VALUES
(1, 2, 'CityCare Medical Center', '100 Health Ave, Midtown', 'New York', 40.7580000, -73.9855000, '+1-555-2100', '08:00:00', '21:00:00', 4.60, 'approved'),
(2, 3, 'Green Valley Multispeciality Hospital', '42 Wellness Street, Queens', 'New York', 40.7306000, -73.9352000, '+1-555-2200', '07:30:00', '22:00:00', 4.40, 'approved'),
(3, 4, 'Northside Emergency & Diagnostics', '18 Care Lane, Upper West Side', 'New York', 40.8075000, -73.9626000, '+1-555-2300', '00:00:00', '23:59:00', 4.20, 'approved'),
(4, 5, 'Bright Smile & Eye Clinic', '75 Harbor Road, Downtown', 'New York', 40.7060000, -74.0090000, '+1-555-2400', '09:00:00', '19:00:00', 4.70, 'approved');

INSERT IGNORE INTO departments (id, hospital_id, department_name, description) VALUES
(1, 1, 'General Medicine', 'Primary care, fever clinic, diagnostics, and preventive consultation.'),
(2, 1, 'Cardiology', 'Heart and emergency chest-pain care.'),
(3, 2, 'Dermatology', 'Skin, allergy, rash, and cosmetic dermatology care.'),
(4, 2, 'Gastroenterology', 'Digestive health, stomach pain, and vomiting care.'),
(5, 3, 'Emergency', '24x7 emergency and urgent diagnostic care.'),
(6, 3, 'Orthopedics', 'Bone pain, fracture, and injury care.'),
(7, 4, 'Dental', 'Dental pain, gum care, and oral health services.'),
(8, 4, 'Ophthalmology', 'Eye pain, blurred vision, and routine eye consultation.'),
(9, 3, 'ENT', 'Ear, nose, throat, hearing, and sinus care.');

INSERT IGNORE INTO services (id, service_name, description) VALUES
(1, 'General Physician', 'General consultation for fever, cough, cold, fatigue, body pain, and primary care.'),
(2, 'Blood Test', 'Lab testing and routine blood investigations.'),
(3, 'X-ray', 'Diagnostic X-ray imaging service.'),
(4, 'Dentist', 'Dental pain, gum bleeding, cleaning, and oral health consultation.'),
(5, 'Eye Specialist', 'Eye pain, blurred vision, and ophthalmology consultation.'),
(6, 'Cardiologist', 'Heart consultation for chest pain, sweating, breathing difficulty, and cardiac risk.'),
(7, 'Dermatologist', 'Skin rash, allergy, itching, and dermatology consultation.'),
(8, 'Emergency', 'Immediate urgent care for severe symptoms and life-threatening situations.'),
(9, 'Fever Clinic', 'Fever, weakness, headache, viral symptoms, and infection triage.'),
(10, 'Gastroenterologist', 'Stomach pain, vomiting, acidity, digestive and liver care.'),
(11, 'Orthopedic', 'Bone pain, fracture, joint pain, and injury consultation.'),
(12, 'Gynecologist', 'Pregnancy care, women health, and gynecology consultation.'),
(13, 'ENT Specialist', 'Ear pain, hearing problems, throat pain, sinus, and ENT consultation.');

INSERT IGNORE INTO doctors (id, hospital_id, doctor_name, specialization, qualification, experience, consultation_fee, rating) VALUES
(1, 1, 'Dr. Emily Carter', 'General Physician', 'MD Internal Medicine', 12, 80.00, 4.70),
(2, 1, 'Dr. Marcus Lee', 'Cardiologist', 'DM Cardiology', 15, 150.00, 4.60),
(3, 1, 'Dr. Nina Patel', 'Gynecologist', 'MS Obstetrics and Gynecology', 10, 120.00, 4.50),
(4, 2, 'Dr. Priya Shah', 'Dermatologist', 'MD Dermatology', 9, 110.00, 4.40),
(5, 2, 'Dr. Omar Hassan', 'Gastroenterologist', 'DM Gastroenterology', 14, 135.00, 4.30),
(6, 3, 'Dr. Rachel Evans', 'Orthopedic', 'MS Orthopedics', 11, 125.00, 4.20),
(7, 3, 'Dr. Victor Chen', 'Emergency Physician', 'MD Emergency Medicine', 13, 100.00, 4.10),
(8, 4, 'Dr. Sophia Nguyen', 'Dentist', 'DDS', 8, 90.00, 4.80),
(9, 4, 'Dr. Daniel Kim', 'Eye Specialist', 'MS Ophthalmology', 10, 95.00, 4.70),
(20, 3, 'Dr. Aisha Rahman', 'ENT Specialist', 'MS ENT', 9, 85.00, 4.50);

INSERT IGNORE INTO doctor_services (doctor_id, service_id) VALUES
(1, 1), (1, 2), (1, 9),
(2, 6), (2, 8),
(3, 12),
(4, 7),
(5, 10), (5, 2),
(6, 11), (6, 3),
(7, 8), (7, 3),
(8, 4),
(9, 5),
(20, 13);

INSERT IGNORE INTO doctor_availability (id, doctor_id, day, start_time, end_time) VALUES
(1, 1, 'Monday', '09:00:00', '14:00:00'),
(2, 1, 'Wednesday', '09:00:00', '14:00:00'),
(3, 1, 'Friday', '10:00:00', '16:00:00'),
(4, 2, 'Monday', '11:00:00', '17:00:00'),
(5, 2, 'Thursday', '10:00:00', '16:00:00'),
(6, 3, 'Tuesday', '10:00:00', '15:00:00'),
(7, 3, 'Saturday', '09:00:00', '13:00:00'),
(8, 4, 'Tuesday', '09:00:00', '15:00:00'),
(9, 4, 'Friday', '11:00:00', '18:00:00'),
(10, 5, 'Monday', '10:00:00', '16:00:00'),
(11, 5, 'Thursday', '11:00:00', '17:00:00'),
(12, 6, 'Wednesday', '09:00:00', '15:00:00'),
(13, 6, 'Saturday', '10:00:00', '14:00:00'),
(14, 7, 'Monday', '00:00:00', '23:59:00'),
(15, 7, 'Tuesday', '00:00:00', '23:59:00'),
(16, 8, 'Tuesday', '09:00:00', '17:00:00'),
(17, 8, 'Thursday', '09:00:00', '17:00:00'),
(18, 9, 'Monday', '09:00:00', '14:00:00'),
(19, 9, 'Friday', '10:00:00', '16:00:00'),
(20, 20, 'Wednesday', '10:00:00', '15:00:00'),
(21, 20, 'Saturday', '09:00:00', '13:00:00');

INSERT IGNORE INTO queues (id, hospital_id, service_id, current_queue, estimated_waiting_time) VALUES
(1, 1, 1, 8, 35),
(2, 1, 2, 12, 45),
(3, 1, 6, 5, 30),
(4, 1, 8, 3, 12),
(5, 1, 9, 10, 40),
(6, 1, 12, 4, 25),
(7, 2, 7, 6, 28),
(8, 2, 10, 7, 35),
(9, 2, 2, 9, 32),
(10, 3, 11, 5, 24),
(11, 3, 3, 4, 20),
(12, 3, 8, 2, 8),
(13, 4, 4, 6, 26),
(14, 4, 5, 5, 22),
(15, 3, 13, 4, 18);
