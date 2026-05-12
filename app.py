

# --- Flask and SocketIO setup ---
import os
import datetime
import datetime as dt
import binascii
import functools
import hashlib
import hmac
import json
import math
import secrets
import socket
import urllib.error
import urllib.parse
import urllib.request
from flask import (
    Flask,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_socketio import SocketIO, emit, join_room, leave_room
import mysql.connector
from mysql.connector import Error, IntegrityError
from ai_service import AIServiceError, predict_medical_service

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "healthpilot-dev-secret-change-me")
socketio = SocketIO(app)


def ambulance_driver_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not getattr(g, 'current_driver', None):
            flash("Please log in as an ambulance driver.", "warning")
            return redirect(url_for("ambulance_login"))
        return view(*args, **kwargs)

    return wrapped

# Patient books ambulance (assigns ambulance to request)
@app.route('/ambulance/book/<int:ambulance_id>', methods=['POST'])
def ambulance_book(ambulance_id):
    request_id = request.form.get('request_id')
    connection = get_connection()
    cursor = connection.cursor()
    try:
        # Assign ambulance to request
        cursor.execute("""
            UPDATE ambulance_requests
            SET assigned_ambulance_id = %s, status = 'assigned'
            WHERE id = %s
        """, (ambulance_id, request_id))
        # Set ambulance status to busy
        cursor.execute("""
            UPDATE ambulances SET status = 'busy' WHERE id = %s
        """, (ambulance_id,))
        connection.commit()
        flash('Ambulance booked! You can now track it live.', 'success')
    except Exception as e:
        connection.rollback()
        flash(f'Error booking ambulance: {e}', 'danger')
    finally:
        cursor.close()
        connection.close()
    return redirect(url_for('ambulance_request_track', request_id=request_id))

# Ambulance Driver Dashboard
@app.route('/ambulance/driver/<int:driver_id>', methods=['GET'])
@ambulance_driver_required
def ambulance_dashboard(driver_id):
    if g.current_driver and g.current_driver['driver_id'] != driver_id:
        flash('You do not have access to that ambulance dashboard.', 'danger')
        return redirect(url_for('ambulance_dashboard_redirect'))

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    driver = None
    requests = []
    current_assignment = None
    try:
        # Get driver and ambulance info
        cursor.execute("""
            SELECT d.id as driver_id, d.name, d.phone, a.id as ambulance_id, a.vehicle_number,
                   a.status, a.latitude, a.longitude, h.hospital_name
            FROM ambulance_drivers d
            JOIN ambulances a ON d.ambulance_id = a.id
            JOIN hospitals h ON a.hospital_id = h.id
            WHERE d.id = %s
        """, (driver_id,))
        driver = cursor.fetchone()
        if not driver:
            flash("Driver not found.", "danger")
            return redirect(url_for('home'))

        # Get pending requests for this ambulance
        cursor.execute("""
            SELECT * FROM ambulance_requests
            WHERE status = 'pending'
            ORDER BY request_time ASC
        """)
        requests = cursor.fetchall()

        # Get current assignment (if any)
        cursor.execute("""
            SELECT * FROM ambulance_requests
            WHERE assigned_ambulance_id = %s AND status IN ('assigned', 'reached_patient', 'reached_hospital')
            ORDER BY request_time DESC LIMIT 1
        """, (driver['ambulance_id'],))
        current_assignment = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()
    return render_template('ambulance_dashboard.html', driver=driver, requests=requests, current_assignment=current_assignment)


@app.route('/ambulance/dashboard')
@ambulance_driver_required
def ambulance_dashboard_redirect():
    return redirect(url_for('ambulance_dashboard', driver_id=g.current_driver['driver_id']))


@app.route('/ambulance/register', methods=['GET', 'POST'])
def ambulance_register():
    hospitals = fetch_all("SELECT id, hospital_name, city FROM hospitals WHERE status = 'approved' ORDER BY hospital_name")
    if request.method == 'POST':
        hospital_id = request.form.get('hospital_id')
        driver_name = request.form.get('driver_name', '').strip()
        phone = request.form.get('phone', '').strip()
        vehicle_number = request.form.get('vehicle_number', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not hospital_id or not driver_name or not vehicle_number or not username or not password:
            flash('Please fill in all required fields.', 'warning')
            return render_template('ambulance_register.html', hospitals=hospitals)

        existing = fetch_one('SELECT id FROM ambulance_drivers WHERE username = %s', (username,))
        if existing:
            flash('That username is already taken.', 'danger')
            return render_template('ambulance_register.html', hospitals=hospitals)

        try:
            ambulance_id = execute(
                "INSERT INTO ambulances (hospital_id, driver_name, driver_phone, vehicle_number, status) VALUES (%s, %s, %s, %s, 'available')",
                (hospital_id, driver_name, phone, vehicle_number),
            )
            execute(
                "INSERT INTO ambulance_drivers (ambulance_id, username, password, name, phone) VALUES (%s, %s, %s, %s, %s)",
                (ambulance_id, username, hash_password(password), driver_name, phone),
            )
            flash('Ambulance driver registered successfully. You can now log in.', 'success')
            return redirect(url_for('ambulance_login'))
        except Exception as e:
            flash(f'Error creating ambulance registration: {e}', 'danger')
            return render_template('ambulance_register.html', hospitals=hospitals)

    return render_template('ambulance_register.html', hospitals=hospitals)


@app.route('/ambulance/login', methods=['GET', 'POST'])
def ambulance_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        driver = fetch_one('SELECT * FROM ambulance_drivers WHERE username = %s', (username,))
        if driver and verify_password(driver['password'], password):
            session.clear()
            session['ambulance_driver_id'] = driver['id']
            flash('Ambulance driver logged in.', 'success')
            return redirect(url_for('ambulance_dashboard_redirect'))
        flash('Invalid username or password.', 'danger')
    return render_template('ambulance_login.html')


@app.route('/ambulance/logout')
def ambulance_logout():
    session.pop('ambulance_driver_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))


@app.route('/ambulance/accept/<int:request_id>', methods=['POST'])
@ambulance_driver_required
def ambulance_accept(request_id):
    driver = g.current_driver
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT status FROM ambulance_requests WHERE id = %s", (request_id,))
        row = cursor.fetchone()
        if not row or row[0] != 'pending':
            flash('This request is no longer available.', 'warning')
            return redirect(url_for('ambulance_dashboard_redirect'))
        cursor.execute(
            "UPDATE ambulance_requests SET assigned_ambulance_id = %s, status = 'assigned', hospital_id = %s WHERE id = %s",
            (driver['ambulance_id'], driver['hospital_id'], request_id),
        )
        cursor.execute("UPDATE ambulances SET status = 'busy' WHERE id = %s", (driver['ambulance_id'],))
        connection.commit()
        flash('Request accepted. Proceed to the patient location.', 'success')
    except Exception as e:
        connection.rollback()
        flash(f'Error accepting request: {e}', 'danger')
    finally:
        cursor.close()
        connection.close()
    return redirect(url_for('ambulance_dashboard_redirect'))


@app.route('/ambulance/request/<int:request_id>/status', methods=['POST'])
@ambulance_driver_required
def ambulance_update_request_status(request_id):
    next_status = request.form.get('next_status')
    valid_updates = {
        'reached_patient': 'assigned',
        'reached_hospital': 'reached_patient',
        'completed': 'reached_hospital'
    }
    if next_status not in valid_updates:
        flash('Invalid status update.', 'danger')
        return redirect(url_for('ambulance_dashboard_redirect'))

    driver = g.current_driver
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, status, assigned_ambulance_id FROM ambulance_requests WHERE id = %s",
            (request_id,)
        )
        request_row = cursor.fetchone()
        if not request_row or request_row['assigned_ambulance_id'] != driver['ambulance_id']:
            flash('Request not found or not assigned to you.', 'warning')
            return redirect(url_for('ambulance_dashboard_redirect'))
        if request_row['status'] != valid_updates[next_status]:
            flash('This status cannot be updated from the current state.', 'warning')
            return redirect(url_for('ambulance_dashboard_redirect'))

        cursor.execute(
            "UPDATE ambulance_requests SET status = %s WHERE id = %s",
            (next_status, request_id)
        )
        if next_status == 'completed':
            cursor.execute(
                "UPDATE ambulances SET status = 'available' WHERE id = %s",
                (driver['ambulance_id'],)
            )
        connection.commit()
        flash('Booking status updated.', 'success')
    except Exception as e:
        connection.rollback()
        flash(f'Error updating booking status: {e}', 'danger')
    finally:
        cursor.close()
        connection.close()
    return redirect(url_for('ambulance_dashboard_redirect'))


@app.route('/ambulance/dashboard/status')
@ambulance_driver_required
def ambulance_dashboard_status():
    driver = g.current_driver
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT a.latitude, a.longitude, a.status, a.vehicle_number, a.hospital_id \n"
            "FROM ambulance_drivers d \n"
            "JOIN ambulances a ON d.ambulance_id = a.id \n"
            "WHERE d.id = %s",
            (driver['driver_id'],),
        )
        ambulance = cursor.fetchone() or {}
        cursor.execute(
            "SELECT patient_name, latitude, longitude, status \n"
            "FROM ambulance_requests \n"
            "WHERE assigned_ambulance_id = %s AND status IN ('assigned', 'reached_patient', 'reached_hospital') \n"
            "ORDER BY request_time DESC LIMIT 1",
            (driver['ambulance_id'],),
        )
        assignment = cursor.fetchone()

        if ambulance.get('status') == 'busy' and assignment is None:
            cursor.execute(
                "UPDATE ambulances SET status = 'available' WHERE id = %s",
                (driver['ambulance_id'],),
            )
            connection.commit()
            ambulance['status'] = 'available'

        return jsonify({
            'driver': {
                'lat': ambulance.get('latitude'),
                'lng': ambulance.get('longitude'),
                'status': ambulance.get('status'),
                'vehicle_number': ambulance.get('vehicle_number'),
            },
            'assignment': assignment and {
                'patient_name': assignment['patient_name'],
                'lat': assignment['latitude'],
                'lng': assignment['longitude'],
                'status': assignment['status'],
            },
        })
    finally:
        cursor.close()
        connection.close()


# Emergency Ambulance Request (no login required)
@app.route('/ambulance/request', methods=['GET', 'POST'])
def ambulance_request():
    if request.method == 'POST':
        patient_name = request.form.get('patient_name')
        mobile_number = request.form.get('mobile_number')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        request_time = datetime.datetime.now()
        # Save request to DB
        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO ambulance_requests (patient_name, mobile_number, latitude, longitude, request_time, status)
                VALUES (%s, %s, %s, %s, %s, 'pending')
            """, (patient_name, mobile_number, latitude, longitude, request_time))
            request_id = cursor.lastrowid
            connection.commit()
        except Exception as e:
            connection.rollback()
            flash(f'Error saving ambulance request: {e}', 'danger')
            return redirect(url_for('ambulance_request'))
        finally:
            cursor.close()
            connection.close()
        flash('Ambulance request submitted! Select a nearby ambulance to send the request or broadcast to all nearby ambulances.', 'success')
        return redirect(url_for('ambulance_nearby', lat=latitude, lng=longitude, request_id=request_id))
    return render_template('ambulance_request.html')

# Show nearby ambulances and hospitals
@app.route('/ambulance/nearby')
def ambulance_nearby():
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    request_id = request.args.get('request_id', type=int)
    ambulances = []
    fallback_distance = False
    if lat is not None and lng is not None:
        try:
            connection = get_connection()
            cursor = connection.cursor(dictionary=True)
            # Find available ambulances within 10km radius, sorted by distance
            query = '''
                SELECT a.id, a.driver_name, a.driver_phone, a.vehicle_number, a.latitude, a.longitude, a.status,
                       h.hospital_name,
                       (6371 * ACOS(
                           COS(RADIANS(%s)) * COS(RADIANS(a.latitude)) *
                           COS(RADIANS(a.longitude) - RADIANS(%s)) +
                           SIN(RADIANS(%s)) * SIN(RADIANS(a.latitude))
                       )) AS distance
                FROM ambulances a
                JOIN hospitals h ON a.hospital_id = h.id
                WHERE a.status = 'available' AND a.latitude IS NOT NULL AND a.longitude IS NOT NULL
                HAVING distance <= 10
                ORDER BY distance ASC
                LIMIT 10
            '''
            cursor.execute(query, (lat, lng, lat))
            ambulances = cursor.fetchall()
            if not ambulances:
                fallback_distance = True
                fallback_query = '''
                    SELECT a.id, a.driver_name, a.driver_phone, a.vehicle_number, a.latitude, a.longitude, a.status,
                           h.hospital_name,
                           (6371 * ACOS(
                               COS(RADIANS(%s)) * COS(RADIANS(a.latitude)) *
                               COS(RADIANS(a.longitude) - RADIANS(%s)) +
                               SIN(RADIANS(%s)) * SIN(RADIANS(a.latitude))
                           )) AS distance
                    FROM ambulances a
                    JOIN hospitals h ON a.hospital_id = h.id
                    WHERE a.status = 'available' AND a.latitude IS NOT NULL AND a.longitude IS NOT NULL
                    ORDER BY distance ASC
                    LIMIT 10
                '''
                cursor.execute(fallback_query, (lat, lng, lat))
                ambulances = cursor.fetchall()
        except Exception as e:
            flash(f"Error fetching ambulances: {e}", "danger")
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'connection' in locals():
                connection.close()
    return render_template('ambulance_nearby.html', ambulances=ambulances, lat=lat, lng=lng, request_id=request_id, fallback_distance=fallback_distance)

@app.route('/ambulance/request/send_all/<int:request_id>', methods=['POST'])
def ambulance_request_send_to_all(request_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    request_row = None
    try:
        cursor.execute(
            "SELECT id, status, assigned_ambulance_id, latitude, longitude FROM ambulance_requests WHERE id = %s",
            (request_id,),
        )
        request_row = cursor.fetchone()
        if not request_row:
            flash('Ambulance request not found.', 'danger')
            return redirect(url_for('ambulance_request'))
        if request_row['assigned_ambulance_id'] is not None or request_row['status'] != 'pending':
            cursor.execute(
                "UPDATE ambulance_requests SET assigned_ambulance_id = NULL, status = 'pending' WHERE id = %s",
                (request_id,),
            )
            connection.commit()
            flash('Request broadcast to all nearby ambulances.', 'success')
        else:
            flash('Request is already pending and available to nearby ambulances.', 'info')
    except Exception as e:
        connection.rollback()
        flash(f'Error broadcasting request: {e}', 'danger')
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('ambulance_request_track', request_id=request_id))

@app.route('/ambulance/request/<int:request_id>/track')
def ambulance_request_track(request_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT r.id, r.patient_name, r.mobile_number, r.latitude AS patient_lat, r.longitude AS patient_lng,
                   r.status, r.assigned_ambulance_id,
                   a.latitude AS ambulance_lat, a.longitude AS ambulance_lng, a.vehicle_number,
                   h.hospital_name
            FROM ambulance_requests r
            LEFT JOIN ambulances a ON r.assigned_ambulance_id = a.id
            LEFT JOIN hospitals h ON a.hospital_id = h.id
            WHERE r.id = %s
            """,
            (request_id,),
        )
        request_data = cursor.fetchone()
        if not request_data:
            flash('Ambulance request not found.', 'danger')
            return redirect(url_for('ambulance_request'))
    finally:
        cursor.close()
        connection.close()

    return render_template('ambulance_request_track.html', request_data=request_data)

@app.route('/api/ambulance/request/<int:request_id>/status')
def api_ambulance_request_status(request_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT r.id, r.status, r.patient_name, r.mobile_number, r.latitude AS patient_lat, r.longitude AS patient_lng,
                   r.assigned_ambulance_id,
                   a.latitude AS ambulance_lat, a.longitude AS ambulance_lng, a.vehicle_number,
                   h.hospital_name
            FROM ambulance_requests r
            LEFT JOIN ambulances a ON r.assigned_ambulance_id = a.id
            LEFT JOIN hospitals h ON a.hospital_id = h.id
            WHERE r.id = %s
            """,
            (request_id,),
        )
        request_data = cursor.fetchone()
        if not request_data:
            return jsonify({'error': 'Request not found.'}), 404
        return jsonify({
            'id': request_data['id'],
            'status': request_data['status'],
            'patient_lat': request_data['patient_lat'],
            'patient_lng': request_data['patient_lng'],
            'assigned_ambulance_id': request_data['assigned_ambulance_id'],
            'ambulance_lat': request_data['ambulance_lat'],
            'ambulance_lng': request_data['ambulance_lng'],
            'vehicle_number': request_data['vehicle_number'],
            'hospital_name': request_data['hospital_name'],
        })
    finally:
        cursor.close()
        connection.close()

# --- Real-time tracking and notifications ---
# Driver updates ambulance location (called from driver app/dashboard)
@app.route('/ambulance/update_location', methods=['POST'])
def ambulance_update_location():
    ambulance_id = request.form.get('ambulance_id')
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')
    # Update ambulance location in DB
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            UPDATE ambulances SET latitude = %s, longitude = %s, last_update = NOW() WHERE id = %s
        """, (latitude, longitude, ambulance_id))
        connection.commit()
        # Emit real-time update to all clients in the ambulance room
        socketio.emit('ambulance_location', {
            'ambulance_id': ambulance_id,
            'latitude': latitude,
            'longitude': longitude
        }, room=f"ambulance_{ambulance_id}")
        flash('Ambulance location updated successfully.', 'success')
    except Exception as e:
        connection.rollback()
        flash(f'Error updating ambulance location: {e}', 'danger')
    finally:
        cursor.close()
        connection.close()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return ('', 204)
    return redirect(url_for('ambulance_dashboard_redirect'))

# Patient/driver join ambulance room for live updates
@socketio.on('join_ambulance_room')
def handle_join_ambulance_room(data):
    ambulance_id = data.get('ambulance_id')
    join_room(f"ambulance_{ambulance_id}")

# In-app notification event (for booking, assignment, etc.)
def send_notification(user_type, user_id, message):
    # user_type: 'driver', 'hospital', 'patient'
    # user_id: driver_id, hospital_id, or request_id
    socketio.emit('notification', {
        'user_type': user_type,
        'user_id': user_id,
        'message': message
    }, room=f"notify_{user_type}_{user_id}")

DB_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "localhost"),
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", ""),
    "database": os.environ.get("MYSQL_DATABASE", "healthpilot"),
}

MAPPLS_WEB_API_KEY = os.environ.get("MAPPLS_WEB_API_KEY") or os.environ.get("MAPPLS_API_KEY", "")
MAPPLS_REST_API_KEY = os.environ.get("MAPPLS_REST_API_KEY") or os.environ.get("MAPPLS_API_KEY", "")

COMMON_SYMPTOMS = [
    "fever",
    "cough",
    "cold",
    "body pain",
    "weakness",
    "headache",
    "chest pain",
    "sweating",
    "breathing problem",
    "tooth pain",
    "gum bleeding",
    "eye pain",
    "blurred vision",
    "skin rash",
    "itching",
    "allergy",
    "stomach pain",
    "vomiting",
    "bone pain",
    "fracture",
    "pregnancy",
    "women health",
    "heavy bleeding",
    "unconsciousness",
]

SYMPTOM_RULES = [
    {
        "service": "Emergency",
        "keywords": ["chest pain", "breathing problem", "heavy bleeding", "unconsciousness", "severe pain"],
        "reason": "Severe symptoms need immediate emergency attention.",
        "urgent": True,
    },
    {
        "service": "General Physician",
        "keywords": ["fever", "cough", "cold", "body pain", "fatigue", "sore throat"],
        "reason": "Primary care is suitable for fever, cough, cold, and body pain.",
        "urgent": False,
    },
    {
        "service": "Fever Clinic",
        "keywords": ["fever", "weakness", "headache", "chills", "viral"],
        "reason": "A fever clinic can triage fever with weakness or headache.",
        "urgent": False,
    },
    {
        "service": "Blood Test",
        "keywords": ["fever", "weakness", "headache", "infection", "fatigue"],
        "reason": "A blood test may help identify infection or deficiency.",
        "urgent": False,
    },
    {
        "service": "Cardiologist",
        "keywords": ["chest pain", "sweating", "breathing problem", "palpitation", "heart"],
        "reason": "Cardiology is recommended for chest pain, sweating, or breathing difficulty.",
        "urgent": False,
    },
    {
        "service": "Dentist",
        "keywords": ["tooth pain", "gum bleeding", "toothache", "cavity", "oral"],
        "reason": "Dental care is recommended for tooth pain or gum bleeding.",
        "urgent": False,
    },
    {
        "service": "Eye Specialist",
        "keywords": ["eye pain", "blurred vision", "red eye", "vision", "watery eyes"],
        "reason": "An eye specialist can evaluate pain, redness, or blurred vision.",
        "urgent": False,
    },
    {
        "service": "Dermatologist",
        "keywords": ["skin rash", "itching", "allergy", "acne", "hives"],
        "reason": "Dermatology is recommended for rash, itching, and allergy symptoms.",
        "urgent": False,
    },
    {
        "service": "Gastroenterologist",
        "keywords": ["stomach pain", "vomiting", "acidity", "diarrhea", "nausea"],
        "reason": "Digestive symptoms are best reviewed by a gastroenterologist.",
        "urgent": False,
    },
    {
        "service": "Orthopedic",
        "keywords": ["bone pain", "fracture", "joint pain", "sprain", "injury"],
        "reason": "Orthopedic care is suitable for bone pain, fracture, and injuries.",
        "urgent": False,
    },
    {
        "service": "Gynecologist",
        "keywords": ["pregnancy", "women health", "period pain", "menstrual", "gynecology"],
        "reason": "Gynecology is recommended for pregnancy and women health concerns.",
        "urgent": False,
    },
]

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def get_connection(use_database=True):
    config = DB_CONFIG.copy()
    if not use_database:
        config.pop("database", None)
    return mysql.connector.connect(**config)


def execute_schema():
    schema_path = os.path.join(BASE_DIR, "database", "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as schema_file:
        sql = schema_file.read()

    connection = get_connection(use_database=False)
    cursor = connection.cursor()
    try:
        for statement in sql.split(";"):
            statement = statement.strip()
            if statement:
                cursor.execute(statement)
        connection.commit()
    finally:
        cursor.close()
        connection.close()


def fetch_all(sql, params=None):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(sql, params or ())
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def fetch_one(sql, params=None):
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def execute(sql, params=None):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(sql, params or ())
        connection.commit()
        return cursor.lastrowid
    finally:
        cursor.close()
        connection.close()


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 260000)
    return f"pbkdf2_sha256$260000${salt}${binascii.hexlify(digest).decode('ascii')}"


def verify_password(stored_password, supplied_password):
    try:
        algorithm, iterations, salt, stored_hash = stored_password.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            supplied_password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        )
        return hmac.compare_digest(binascii.hexlify(digest).decode("ascii"), stored_hash)
    except (ValueError, TypeError):
        return False


def role_required(*roles):
    def decorator(view):
        @functools.wraps(view)
        def wrapped(*args, **kwargs):
            if not g.user:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("home"))
            if roles and g.user["role"] not in roles:
                flash("You do not have permission to access that page.", "danger")
                return redirect(default_dashboard(g.user["role"]))
            return view(*args, **kwargs)

        return wrapped

    return decorator


def default_dashboard(role):
    if role == "patient":
        return url_for("patient_dashboard")
    if role == "hospital_admin":
        return url_for("hospital_dashboard")
    if role == "super_admin":
        return url_for("super_admin_dashboard")
    return url_for("home")


@app.before_request
def load_current_user():
    g.user = None
    g.current_driver = None
    user_id = session.get("user_id")
    if user_id:
        g.user = fetch_one("SELECT id, name, email, role, phone FROM users WHERE id = %s", (user_id,))

    driver_id = session.get("ambulance_driver_id")
    if driver_id:
        g.current_driver = fetch_one(
            """
            SELECT d.id AS driver_id, d.username, d.name, d.phone, d.ambulance_id,
                   a.vehicle_number, a.status AS ambulance_status, a.latitude, a.longitude,
                   a.hospital_id, h.hospital_name
            FROM ambulance_drivers d
            JOIN ambulances a ON d.ambulance_id = a.id
            JOIN hospitals h ON a.hospital_id = h.id
            WHERE d.id = %s
            """,
            (driver_id,),
        )


@app.context_processor
def inject_globals():
    return {
        "current_user": g.get("user"),
        "current_driver": g.get("current_driver"),
        "today": dt.date.today().isoformat(),
        "mappls_web_api_key": MAPPLS_WEB_API_KEY,
        "patient_location": get_patient_location(),
    }


@app.template_filter("time_input")
def time_input(value):
    if not value:
        return ""
    if isinstance(value, dt.timedelta):
        total_seconds = int(value.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"
    if isinstance(value, dt.time):
        return value.strftime("%H:%M")
    return str(value)[:5]


@app.template_filter("date_input")
def date_input(value):
    if isinstance(value, (dt.date, dt.datetime)):
        return value.strftime("%Y-%m-%d")
    return value or ""


def parse_float(value, fallback=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def get_patient_location():
    location = session.get("patient_location")
    if not isinstance(location, dict):
        return None
    try:
        lat = float(location["lat"])
        lng = float(location["lng"])
    except (KeyError, TypeError, ValueError):
        return None
    return {
        "lat": lat,
        "lng": lng,
        "source": location.get("source", "manual"),
    }


def haversine_km(lat1, lon1, lat2, lon2):
    radius = 6371.0
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    delta_phi = math.radians(float(lat2) - float(lat1))
    delta_lambda = math.radians(float(lon2) - float(lon1))
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return radius * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def hospital_score(hospital_rating, doctor_rating, waiting_time, travel_time):
    waiting = max(float(waiting_time or 1), 1.0)
    travel = max(float(travel_time or 1), 1.0)
    return (float(hospital_rating or 0) * 0.4) + (float(doctor_rating or 0) * 0.2) + ((1 / waiting) * 0.2) + ((1 / travel) * 0.2)


def recommend_services_from_symptoms(symptoms):
    normalized = (symptoms or "").lower()
    scored = []
    emergency_match = False

    for rule in SYMPTOM_RULES:
        matches = [keyword for keyword in rule["keywords"] if keyword in normalized]
        if matches:
            scored.append({**rule, "matches": matches, "score": len(matches)})
            if rule["service"] == "Emergency":
                emergency_match = True

    if not scored:
        scored.append(
            {
                "service": "General Physician",
                "keywords": [],
                "matches": [],
                "score": 1,
                "reason": "A general physician can evaluate broad symptoms and guide next steps.",
                "urgent": False,
            }
        )

    scored.sort(key=lambda item: (item["urgent"], item["score"]), reverse=True)
    if emergency_match:
        emergency = [item for item in scored if item["service"] == "Emergency"]
        others = [item for item in scored if item["service"] != "Emergency"]
        scored = emergency + others[:2]

    recommendations = []
    seen = set()
    for item in scored:
        if item["service"] in seen:
            continue
        service = fetch_one("SELECT id, service_name, description FROM services WHERE service_name = %s", (item["service"],))
        if service:
            recommendations.append({**item, **service})
            seen.add(item["service"])
        if len(recommendations) == 3:
            break
    return recommendations


def admin_hospital():
    if not g.user:
        return None
    return fetch_one("SELECT * FROM hospitals WHERE admin_id = %s LIMIT 1", (g.user["id"],))


def service_hospital_rows(service_id, lat=None, lng=None):
    rows = fetch_all(
        """
        SELECT h.id AS hospital_id, h.hospital_name, h.address, h.city, h.latitude, h.longitude,
               h.contact, h.opening_time, h.closing_time, h.rating AS hospital_rating,
               d.id AS doctor_id, d.doctor_name, d.specialization, d.consultation_fee,
               d.rating AS doctor_rating, s.id AS service_id, s.service_name,
               COALESCE(q.current_queue, 0) AS current_queue,
               COALESCE(q.estimated_waiting_time, 15) AS estimated_waiting_time
        FROM hospitals h
        JOIN doctors d ON d.hospital_id = h.id
        JOIN doctor_services ds ON ds.doctor_id = d.id
        JOIN services s ON s.id = ds.service_id
        LEFT JOIN queues q ON q.hospital_id = h.id AND q.service_id = s.id
        WHERE h.status = 'approved' AND s.id = %s
        ORDER BY h.rating DESC, d.rating DESC
        """,
        (service_id,),
    )

    best_by_hospital = {}
    for row in rows:
        key = row["hospital_id"]
        current = best_by_hospital.get(key)
        if not current or float(row["doctor_rating"] or 0) > float(current["doctor_rating"] or 0):
            best_by_hospital[key] = row

    hospitals = []
    for row in best_by_hospital.values():
        distance = None
        travel_time = None
        if lat is not None and lng is not None:
            distance = haversine_km(lat, lng, row["latitude"], row["longitude"])
            travel_time = max(1, round((distance / 35) * 60))
        score = hospital_score(row["hospital_rating"], row["doctor_rating"], row["estimated_waiting_time"], travel_time or 999)
        hospitals.append(
            {
                "hospital_id": row["hospital_id"],
                "hospital_name": row["hospital_name"],
                "address": row["address"],
                "city": row["city"],
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "contact": row["contact"],
                "opening_time": time_input(row["opening_time"]),
                "closing_time": time_input(row["closing_time"]),
                "hospital_rating": float(row["hospital_rating"] or 0),
                "doctor_id": row["doctor_id"],
                "doctor_name": row["doctor_name"],
                "specialization": row["specialization"],
                "consultation_fee": float(row["consultation_fee"] or 0),
                "doctor_rating": float(row["doctor_rating"] or 0),
                "service_id": row["service_id"],
                "service_name": row["service_name"],
                "current_queue": int(row["current_queue"] or 0),
                "estimated_waiting_time": int(row["estimated_waiting_time"] or 0),
                "distance_km": round(distance, 2) if distance is not None else None,
                "travel_time_minutes": int(travel_time) if travel_time is not None else None,
                "final_score": round(score, 4),
            }
        )

    hospitals.sort(key=lambda item: item["final_score"], reverse=True)
    return hospitals


def service_by_name(service_name):
    return fetch_one(
        "SELECT * FROM services WHERE LOWER(service_name) = LOWER(%s) LIMIT 1",
        (service_name,),
    )


def service_choices():
    return fetch_all("SELECT id, service_name FROM services ORDER BY service_name")


def refresh_ratings(hospital_id, doctor_id):
    hospital = fetch_one(
        """
        SELECT AVG((rating + cleanliness_rating + waiting_rating + staff_rating) / 4) AS avg_rating
        FROM feedback
        WHERE hospital_id = %s
        """,
        (hospital_id,),
    )
    doctor = fetch_one("SELECT AVG(rating) AS avg_rating FROM feedback WHERE doctor_id = %s", (doctor_id,))
    if hospital and hospital["avg_rating"]:
        execute("UPDATE hospitals SET rating = %s WHERE id = %s", (round(float(hospital["avg_rating"]), 2), hospital_id))
    if doctor and doctor["avg_rating"]:
        execute("UPDATE doctors SET rating = %s WHERE id = %s", (round(float(doctor["avg_rating"]), 2), doctor_id))


def quality_scores():
    hospitals = fetch_all(
        """
        SELECT h.id, h.hospital_name, h.city, h.status, h.rating,
               COALESCE((SELECT AVG(estimated_waiting_time) FROM queues q WHERE q.hospital_id = h.id), 0) AS avg_wait,
               COALESCE((SELECT COUNT(*) FROM complaints c WHERE c.hospital_id = h.id AND c.status <> 'resolved'), 0) AS open_complaints,
               COALESCE((SELECT COUNT(*) FROM appointments a WHERE a.hospital_id = h.id), 0) AS total_appointments,
               COALESCE((SELECT COUNT(*) FROM appointments a WHERE a.hospital_id = h.id AND a.status = 'completed'), 0) AS completed_appointments
        FROM hospitals h
        ORDER BY h.rating DESC, h.hospital_name
        """
    )
    results = []
    for hospital in hospitals:
        completion_rate = 0
        if hospital["total_appointments"]:
            completion_rate = hospital["completed_appointments"] / hospital["total_appointments"]
        raw_score = (float(hospital["rating"] or 0) * 16) + (completion_rate * 20) - (float(hospital["avg_wait"] or 0) * 0.25) - (int(hospital["open_complaints"] or 0) * 4)
        hospital["quality_score"] = max(0, min(100, round(raw_score, 1)))
        results.append(hospital)
    return results


def hospital_improvement_tips(complaints, feedback_summary, wait_summary):
    text = " ".join((row.get("complaint_text") or "").lower() for row in complaints)
    avg_wait = float((wait_summary or {}).get("avg_wait") or 0)
    waiting_rating = float((feedback_summary or {}).get("avg_waiting_rating") or 0)
    staff_rating = float((feedback_summary or {}).get("avg_staff_rating") or 0)
    cleanliness_rating = float((feedback_summary or {}).get("avg_cleanliness_rating") or 0)

    tips = []
    if any(word in text for word in ["wait", "waiting", "queue", "delay", "late", "token"]) or avg_wait >= 30 or (waiting_rating and waiting_rating < 3.5):
        tips.append(
            {
                "title": "Reduce waiting friction",
                "detail": "Review queue updates, token movement, and front-desk communication for high-wait services.",
                "icon": "bi-hourglass-split",
            }
        )
    if any(word in text for word in ["staff", "rude", "behavior", "behaviour", "reception", "nurse"]) or (staff_rating and staff_rating < 3.5):
        tips.append(
            {
                "title": "Improve staff experience",
                "detail": "Use complaint notes in staff briefings and set a clear response standard for reception and nursing teams.",
                "icon": "bi-people",
            }
        )
    if any(word in text for word in ["clean", "dirty", "hygiene", "washroom", "sanitation"]) or (cleanliness_rating and cleanliness_rating < 3.5):
        tips.append(
            {
                "title": "Audit cleanliness",
                "detail": "Increase checks around consultation rooms, waiting areas, and washrooms during peak hours.",
                "icon": "bi-droplet",
            }
        )
    if any(word in text for word in ["fee", "bill", "billing", "cost", "charge", "payment"]):
        tips.append(
            {
                "title": "Clarify fees",
                "detail": "Make consultation fees and extra charges visible before appointment confirmation.",
                "icon": "bi-cash-coin",
            }
        )
    if any(word in text for word in ["appointment", "booking", "cancel", "reschedule"]):
        tips.append(
            {
                "title": "Tighten appointment handling",
                "detail": "Track rejected, delayed, and rescheduled bookings to identify process gaps.",
                "icon": "bi-calendar2-check",
            }
        )

    if not tips:
        tips.append(
            {
                "title": "Maintain service quality",
                "detail": "No strong complaint pattern is visible yet. Continue monitoring reviews and open complaints weekly.",
                "icon": "bi-shield-check",
            }
        )
    return tips[:3]


def get_lan_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("8.8.8.8", 80))
            return probe.getsockname()[0]
    except OSError:
        return "YOUR-PC-IP"


@app.route("/")
def home():
    stats = {
        "hospitals": fetch_one("SELECT COUNT(*) AS count FROM hospitals WHERE status = 'approved'")["count"],
        "services": fetch_one("SELECT COUNT(*) AS count FROM services")["count"],
        "appointments": fetch_one("SELECT COUNT(*) AS count FROM appointments")["count"],
    }
    return render_template("home.html", stats=stats)


def handle_login(role, template_title):
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = fetch_one("SELECT * FROM users WHERE email = %s AND role = %s", (email, role))
        if user and verify_password(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            flash(f"Welcome back, {user['name']}.", "success")
            if role == "patient":
                return redirect(url_for("patient_location"))
            return redirect(default_dashboard(role))
        flash("Invalid email or password.", "danger")
    return render_template("auth_login.html", role=role, title=template_title)


@app.route("/patient/login", methods=["GET", "POST"])
def patient_login():
    return handle_login("patient", "Patient Login")


@app.route("/hospital/login", methods=["GET", "POST"])
def hospital_login():
    return handle_login("hospital_admin", "Hospital Admin Login")


@app.route("/super-admin/login", methods=["GET", "POST"])
def super_admin_login():
    return handle_login("super_admin", "Super Admin Login")


@app.route("/patient/register", methods=["GET", "POST"])
def patient_register():
    if request.method == "POST":
        try:
            execute(
                "INSERT INTO users (name, email, password, role, phone) VALUES (%s, %s, %s, 'patient', %s)",
                (
                    request.form.get("name", "").strip(),
                    request.form.get("email", "").strip().lower(),
                    hash_password(request.form.get("password", "")),
                    request.form.get("phone", "").strip(),
                ),
            )
            flash("Patient account created. You can log in now.", "success")
            return redirect(url_for("patient_login"))
        except IntegrityError:
            flash("That email is already registered.", "danger")
    return render_template("patient_register.html")


@app.route("/hospital/register", methods=["GET", "POST"])
def hospital_register():
    if request.method == "POST":
        try:
            admin_id = execute(
                "INSERT INTO users (name, email, password, role, phone) VALUES (%s, %s, %s, 'hospital_admin', %s)",
                (
                    request.form.get("admin_name", "").strip(),
                    request.form.get("email", "").strip().lower(),
                    hash_password(request.form.get("password", "")),
                    request.form.get("phone", "").strip(),
                ),
            )
            execute(
                """
                INSERT INTO hospitals
                    (admin_id, hospital_name, address, city, latitude, longitude, contact, opening_time, closing_time, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
                """,
                (
                    admin_id,
                    request.form.get("hospital_name", "").strip(),
                    request.form.get("address", "").strip(),
                    request.form.get("city", "").strip(),
                    parse_float(request.form.get("latitude"), 40.758),
                    parse_float(request.form.get("longitude"), -73.9855),
                    request.form.get("contact", "").strip(),
                    request.form.get("opening_time") or "09:00",
                    request.form.get("closing_time") or "18:00",
                ),
            )
            flash("Hospital registration submitted. Super admin approval is required before patients can find it.", "success")
            return redirect(url_for("hospital_login"))
        except IntegrityError:
            flash("That email is already registered.", "danger")
    return render_template("hospital_register.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))


@app.route("/patient/dashboard")
@role_required("patient")
def patient_dashboard():
    appointments = fetch_all(
        """
        SELECT a.*, h.hospital_name, d.doctor_name, s.service_name
        FROM appointments a
        JOIN hospitals h ON h.id = a.hospital_id
        JOIN doctors d ON d.id = a.doctor_id
        JOIN services s ON s.id = a.service_id
        WHERE a.patient_id = %s
        ORDER BY a.created_at DESC
        LIMIT 5
        """,
        (g.user["id"],),
    )
    totals = fetch_one(
        """
        SELECT COUNT(*) AS total,
               SUM(status = 'pending') AS pending,
               SUM(status = 'completed') AS completed
        FROM appointments
        WHERE patient_id = %s
        """,
        (g.user["id"],),
    )
    return render_template("patient_dashboard.html", appointments=appointments, totals=totals)


@app.route("/patient/location", methods=["GET", "POST"])
@role_required("patient")
def patient_location():
    if request.method == "POST":
        lat = request.form.get("latitude", type=float)
        lng = request.form.get("longitude", type=float)
        source = request.form.get("source", "manual")
        if lat is None or lng is None:
            flash("Please allow precise location or select a location manually on the map.", "warning")
            return redirect(url_for("patient_location"))
        session["patient_location"] = {
            "lat": lat,
            "lng": lng,
            "source": source if source in {"gps", "manual"} else "manual",
        }
        session.modified = True
        flash("Patient location saved for hospital search and navigation.", "success")
        return redirect(url_for("patient_dashboard"))

    return render_template("patient_location.html")


@app.route("/patient/symptoms", methods=["GET", "POST"])
@role_required("patient")
def symptom_input():
    if request.method == "POST":
        symptoms = request.form.get("symptoms", "").strip()
        recommendations = recommend_services_from_symptoms(symptoms)
        return render_template("suggested_service.html", symptoms=symptoms, recommendations=recommendations)
    return render_template("symptoms.html", common_symptoms=COMMON_SYMPTOMS)


@app.route("/predict-service", methods=["POST"])
@role_required("patient")
def predict_service():
    symptoms = request.form.get("symptoms", "").strip()
    if not symptoms:
        flash("Please enter symptoms before requesting a service suggestion.", "warning")
        return redirect(request.referrer or url_for("patient_dashboard"))

    prediction = None
    prediction_error = None
    service = None
    hospitals = []

    try:
        prediction = predict_medical_service(symptoms)
        service = service_by_name(prediction["service"])
        if service:
            location = get_patient_location()
            hospitals = service_hospital_rows(
                service["id"],
                location["lat"] if location else None,
                location["lng"] if location else None,
            )
    except ValueError as exc:
        flash(str(exc), "warning")
        return redirect(request.referrer or url_for("patient_dashboard"))
    except AIServiceError as exc:
        prediction_error = str(exc)

    return render_template(
        "service_results.html",
        symptoms=symptoms,
        prediction=prediction,
        prediction_error=prediction_error,
        service=service,
        hospitals=hospitals,
        suggested_services=service_choices(),
    )


@app.route("/patient/hospitals/<int:service_id>")
@role_required("patient")
def nearby_hospitals(service_id):
    service = fetch_one("SELECT * FROM services WHERE id = %s", (service_id,))
    if not service:
        flash("Service not found.", "danger")
        return redirect(url_for("symptom_input"))
    return render_template("nearby_hospitals.html", service=service)


@app.route("/api/hospitals")
@role_required("patient")
def hospitals_api():
    service_id = request.args.get("service_id", type=int)
    lat = request.args.get("lat", type=float)
    lng = request.args.get("lng", type=float)
    if not service_id:
        return jsonify({"hospitals": []})
    return jsonify({"hospitals": service_hospital_rows(service_id, lat, lng)})


@app.route("/api/mappls/route")
def mappls_route_api():
    if not MAPPLS_REST_API_KEY:
        return jsonify({"error": "MAPPLS_API_KEY or MAPPLS_REST_API_KEY is not configured."}), 400

    start_lat = request.args.get("start_lat", type=float)
    start_lng = request.args.get("start_lng", type=float)
    end_lat = request.args.get("end_lat", type=float)
    end_lng = request.args.get("end_lng", type=float)
    if None in {start_lat, start_lng, end_lat, end_lng}:
        return jsonify({"error": "start_lat, start_lng, end_lat, and end_lng are required."}), 400

    coordinates = f"{start_lng},{start_lat};{end_lng},{end_lat}"
    query = urllib.parse.urlencode(
        {
            "geometries": "geojson",
            "overview": "full",
            "steps": "false",
            "rtype": "0",
            "access_token": MAPPLS_REST_API_KEY,
        }
    )
    route_url = f"https://route.mappls.com/route/direction/route_adv/driving/{coordinates}?{query}"
    try:
        with urllib.request.urlopen(route_url, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return jsonify(payload)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return jsonify({"error": "Could not fetch route from Mappls.", "detail": str(exc)}), 502


@app.route("/patient/hospital/<int:hospital_id>/<int:service_id>")
@role_required("patient")
def hospital_detail(hospital_id, service_id):
    hospital = fetch_one("SELECT * FROM hospitals WHERE id = %s AND status = 'approved'", (hospital_id,))
    service = fetch_one("SELECT * FROM services WHERE id = %s", (service_id,))
    if not hospital or not service:
        flash("Hospital or service not found.", "danger")
        return redirect(url_for("symptom_input"))
    doctors = fetch_all(
        """
        SELECT d.*, GROUP_CONCAT(CONCAT(da.day, ' ', TIME_FORMAT(da.start_time, '%H:%i'), '-', TIME_FORMAT(da.end_time, '%H:%i')) ORDER BY FIELD(da.day, 'Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday') SEPARATOR ', ') AS availability
        FROM doctors d
        JOIN doctor_services ds ON ds.doctor_id = d.id
        LEFT JOIN doctor_availability da ON da.doctor_id = d.id
        WHERE d.hospital_id = %s AND ds.service_id = %s
        GROUP BY d.id
        ORDER BY d.rating DESC
        """,
        (hospital_id, service_id),
    )
    queue = fetch_one("SELECT * FROM queues WHERE hospital_id = %s AND service_id = %s", (hospital_id, service_id))
    feedback_rows = fetch_all(
        """
        SELECT f.*, u.name AS patient_name
        FROM feedback f
        JOIN users u ON u.id = f.patient_id
        WHERE f.hospital_id = %s
        ORDER BY f.created_at DESC
        LIMIT 5
        """,
        (hospital_id,),
    )
    return render_template("hospital_detail.html", hospital=hospital, service=service, doctors=doctors, queue=queue, feedback_rows=feedback_rows)


@app.route("/patient/book/<int:hospital_id>/<int:doctor_id>/<int:service_id>", methods=["GET", "POST"])
@role_required("patient")
def book_appointment(hospital_id, doctor_id, service_id):
    details = fetch_one(
        """
        SELECT h.hospital_name, h.address, h.latitude, h.longitude, h.contact,
               d.doctor_name, d.specialization, d.consultation_fee, d.rating AS doctor_rating,
               s.service_name
        FROM hospitals h
        JOIN doctors d ON d.hospital_id = h.id
        JOIN doctor_services ds ON ds.doctor_id = d.id
        JOIN services s ON s.id = ds.service_id
        WHERE h.id = %s AND d.id = %s AND s.id = %s AND h.status = 'approved'
        """,
        (hospital_id, doctor_id, service_id),
    )
    if not details:
        flash("Selected appointment option is not available.", "danger")
        return redirect(url_for("symptom_input"))

    if request.method == "POST":
        appointment_date = request.form.get("appointment_date")
        appointment_time = request.form.get("appointment_time")
        token_count = fetch_one(
            """
            SELECT COUNT(*) AS count
            FROM appointments
            WHERE hospital_id = %s AND service_id = %s AND appointment_date = %s
            """,
            (hospital_id, service_id, appointment_date),
        )["count"]
        token_number = f"HP-{service_id:02d}-{appointment_date.replace('-', '')}-{int(token_count) + 1:03d}"
        appointment_id = execute(
            """
            INSERT INTO appointments
                (patient_id, hospital_id, doctor_id, service_id, appointment_date, appointment_time, token_number)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (g.user["id"], hospital_id, doctor_id, service_id, appointment_date, appointment_time, token_number),
        )
        execute(
            """
            INSERT INTO queues (hospital_id, service_id, current_queue, estimated_waiting_time)
            VALUES (%s, %s, 1, 10)
            ON DUPLICATE KEY UPDATE
                current_queue = current_queue + 1,
                estimated_waiting_time = GREATEST(estimated_waiting_time, current_queue * 8)
            """,
            (hospital_id, service_id),
        )
        flash(f"Appointment booked. Your token number is {token_number}.", "success")
        return redirect(url_for("appointment_route", appointment_id=appointment_id))

    return render_template("book_appointment.html", details=details, hospital_id=hospital_id, doctor_id=doctor_id, service_id=service_id)


def patient_appointment(appointment_id):
    return fetch_one(
        """
        SELECT a.*, h.hospital_name, h.address, h.latitude, h.longitude, h.contact,
               d.doctor_name, d.specialization, d.consultation_fee, s.service_name
        FROM appointments a
        JOIN hospitals h ON h.id = a.hospital_id
        JOIN doctors d ON d.id = a.doctor_id
        JOIN services s ON s.id = a.service_id
        WHERE a.id = %s AND a.patient_id = %s
        """,
        (appointment_id, g.user["id"]),
    )


@app.route("/patient/route/<int:appointment_id>")
@role_required("patient")
def appointment_route(appointment_id):
    appointment = patient_appointment(appointment_id)
    if not appointment:
        flash("Appointment not found.", "danger")
        return redirect(url_for("patient_appointments"))
    return render_template("route.html", appointment=appointment)


@app.route("/patient/appointments")
@role_required("patient")
def patient_appointments():
    appointments = fetch_all(
        """
        SELECT a.*, h.hospital_name, d.doctor_name, s.service_name
        FROM appointments a
        JOIN hospitals h ON h.id = a.hospital_id
        JOIN doctors d ON d.id = a.doctor_id
        JOIN services s ON s.id = a.service_id
        WHERE a.patient_id = %s
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
        """,
        (g.user["id"],),
    )
    return render_template("patient_appointments.html", appointments=appointments)


@app.route("/patient/feedback/<int:appointment_id>", methods=["GET", "POST"])
@role_required("patient")
def feedback(appointment_id):
    appointment = patient_appointment(appointment_id)
    if not appointment:
        flash("Appointment not found.", "danger")
        return redirect(url_for("patient_appointments"))
    if request.method == "POST":
        execute(
            """
            INSERT INTO feedback
                (patient_id, hospital_id, doctor_id, rating, cleanliness_rating, waiting_rating, staff_rating, comment)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                g.user["id"],
                appointment["hospital_id"],
                appointment["doctor_id"],
                int(request.form.get("rating", 5)),
                int(request.form.get("cleanliness_rating", 5)),
                int(request.form.get("waiting_rating", 5)),
                int(request.form.get("staff_rating", 5)),
                request.form.get("comment", "").strip(),
            ),
        )
        refresh_ratings(appointment["hospital_id"], appointment["doctor_id"])
        flash("Thank you for your feedback.", "success")
        return redirect(url_for("patient_appointments"))
    return render_template("feedback.html", appointment=appointment)


@app.route("/patient/complaint/<int:hospital_id>", methods=["GET", "POST"])
@role_required("patient")
def submit_complaint(hospital_id):
    hospital = fetch_one("SELECT * FROM hospitals WHERE id = %s", (hospital_id,))
    if not hospital:
        flash("Hospital not found.", "danger")
        return redirect(url_for("patient_appointments"))
    if request.method == "POST":
        execute(
            "INSERT INTO complaints (patient_id, hospital_id, complaint_text) VALUES (%s, %s, %s)",
            (g.user["id"], hospital_id, request.form.get("complaint_text", "").strip()),
        )
        flash("Complaint submitted for review.", "success")
        return redirect(url_for("patient_appointments"))
    return render_template("complaint.html", hospital=hospital)


@app.route("/hospital/dashboard")
@role_required("hospital_admin")
def hospital_dashboard():
    hospital = admin_hospital()
    if not hospital:
        flash("No hospital profile is linked to this account.", "warning")
        return redirect(url_for("home"))
    stats = fetch_one(
        """
        SELECT COUNT(*) AS total,
               COALESCE(SUM(status = 'pending'), 0) AS pending,
               COALESCE(SUM(status = 'completed'), 0) AS completed
        FROM appointments
        WHERE hospital_id = %s
        """,
        (hospital["id"],),
    )
    rating = fetch_one("SELECT AVG(rating) AS avg_rating FROM feedback WHERE hospital_id = %s", (hospital["id"],))
    wait = fetch_one("SELECT AVG(estimated_waiting_time) AS avg_wait FROM queues WHERE hospital_id = %s", (hospital["id"],))
    most_booked = fetch_one(
        """
        SELECT s.service_name, COUNT(*) AS total
        FROM appointments a
        JOIN services s ON s.id = a.service_id
        WHERE a.hospital_id = %s
        GROUP BY s.id
        ORDER BY total DESC
        LIMIT 1
        """,
        (hospital["id"],),
    )
    status_rows = fetch_all(
        "SELECT status, COUNT(*) AS total FROM appointments WHERE hospital_id = %s GROUP BY status",
        (hospital["id"],),
    )
    service_rows = fetch_all(
        """
        SELECT s.service_name, COUNT(*) AS total
        FROM appointments a
        JOIN services s ON s.id = a.service_id
        WHERE a.hospital_id = %s
        GROUP BY s.service_name
        ORDER BY total DESC
        LIMIT 6
        """,
        (hospital["id"],),
    )
    feedback_summary = fetch_one(
        """
        SELECT COUNT(*) AS total_reviews,
               AVG(rating) AS avg_doctor_rating,
               AVG(cleanliness_rating) AS avg_cleanliness_rating,
               AVG(waiting_rating) AS avg_waiting_rating,
               AVG(staff_rating) AS avg_staff_rating
        FROM feedback
        WHERE hospital_id = %s
        """,
        (hospital["id"],),
    )
    recent_feedback = fetch_all(
        """
        SELECT f.*, u.name AS patient_name, d.doctor_name
        FROM feedback f
        JOIN users u ON u.id = f.patient_id
        JOIN doctors d ON d.id = f.doctor_id
        WHERE f.hospital_id = %s
        ORDER BY f.created_at DESC
        LIMIT 4
        """,
        (hospital["id"],),
    )
    complaint_summary = fetch_one(
        """
        SELECT COUNT(*) AS total_complaints,
               COALESCE(SUM(status = 'open'), 0) AS open_complaints,
               COALESCE(SUM(status = 'in_review'), 0) AS in_review_complaints,
               COALESCE(SUM(status = 'resolved'), 0) AS resolved_complaints
        FROM complaints
        WHERE hospital_id = %s
        """,
        (hospital["id"],),
    )
    recent_complaints = fetch_all(
        """
        SELECT c.*, u.name AS patient_name
        FROM complaints c
        JOIN users u ON u.id = c.patient_id
        WHERE c.hospital_id = %s
        ORDER BY FIELD(c.status, 'open', 'in_review', 'resolved'), c.created_at DESC
        LIMIT 5
        """,
        (hospital["id"],),
    )
    complaint_insight_rows = fetch_all(
        "SELECT complaint_text, status FROM complaints WHERE hospital_id = %s ORDER BY created_at DESC LIMIT 50",
        (hospital["id"],),
    )
    return render_template(
        "hospital_dashboard.html",
        hospital=hospital,
        stats=stats,
        rating=rating,
        wait=wait,
        most_booked=most_booked,
        status_labels=[row["status"].title() for row in status_rows],
        status_values=[int(row["total"]) for row in status_rows],
        service_labels=[row["service_name"] for row in service_rows],
        service_values=[int(row["total"]) for row in service_rows],
        feedback_summary=feedback_summary,
        recent_feedback=recent_feedback,
        complaint_summary=complaint_summary,
        recent_complaints=recent_complaints,
        improvement_tips=hospital_improvement_tips(complaint_insight_rows, feedback_summary, wait),
    )


@app.route("/hospital/profile", methods=["GET", "POST"])
@role_required("hospital_admin")
def hospital_profile():
    hospital = admin_hospital()
    if not hospital:
        flash("No hospital profile is linked to this account.", "warning")
        return redirect(url_for("hospital_dashboard"))
    if request.method == "POST":
        execute(
            """
            UPDATE hospitals
            SET hospital_name = %s, address = %s, city = %s, latitude = %s, longitude = %s,
                contact = %s, opening_time = %s, closing_time = %s
            WHERE id = %s
            """,
            (
                request.form.get("hospital_name", "").strip(),
                request.form.get("address", "").strip(),
                request.form.get("city", "").strip(),
                parse_float(request.form.get("latitude")),
                parse_float(request.form.get("longitude")),
                request.form.get("contact", "").strip(),
                request.form.get("opening_time"),
                request.form.get("closing_time"),
                hospital["id"],
            ),
        )
        flash("Hospital profile updated.", "success")
        return redirect(url_for("hospital_profile"))
    return render_template("hospital_profile.html", hospital=hospital)


@app.route("/hospital/doctors", methods=["GET", "POST"])
@role_required("hospital_admin")
def doctor_management():
    hospital = admin_hospital()
    if not hospital:
        flash("Hospital profile not found.", "danger")
        return redirect(url_for("hospital_dashboard"))
    if request.method == "POST":
        doctor_id = execute(
            """
            INSERT INTO doctors (hospital_id, doctor_name, specialization, qualification, experience, consultation_fee, rating)
            VALUES (%s, %s, %s, %s, %s, %s, 4.00)
            """,
            (
                hospital["id"],
                request.form.get("doctor_name", "").strip(),
                request.form.get("specialization", "").strip(),
                request.form.get("qualification", "").strip(),
                int(request.form.get("experience") or 0),
                float(request.form.get("consultation_fee") or 0),
            ),
        )
        for service_id in request.form.getlist("services"):
            execute("INSERT IGNORE INTO doctor_services (doctor_id, service_id) VALUES (%s, %s)", (doctor_id, int(service_id)))
            execute(
                """
                INSERT IGNORE INTO queues (hospital_id, service_id, current_queue, estimated_waiting_time)
                VALUES (%s, %s, 0, 15)
                """,
                (hospital["id"], int(service_id)),
            )
        start_time = request.form.get("start_time") or "09:00"
        end_time = request.form.get("end_time") or "17:00"
        for day in request.form.getlist("days"):
            execute(
                "INSERT INTO doctor_availability (doctor_id, day, start_time, end_time) VALUES (%s, %s, %s, %s)",
                (doctor_id, day, start_time, end_time),
            )
        flash("Doctor added successfully.", "success")
        return redirect(url_for("doctor_management"))

    doctors = fetch_all(
        """
        SELECT d.*,
               GROUP_CONCAT(DISTINCT s.service_name ORDER BY s.service_name SEPARATOR ', ') AS services,
               GROUP_CONCAT(DISTINCT CONCAT(da.day, ' ', TIME_FORMAT(da.start_time, '%H:%i'), '-', TIME_FORMAT(da.end_time, '%H:%i')) ORDER BY FIELD(da.day, 'Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday') SEPARATOR ', ') AS availability
        FROM doctors d
        LEFT JOIN doctor_services ds ON ds.doctor_id = d.id
        LEFT JOIN services s ON s.id = ds.service_id
        LEFT JOIN doctor_availability da ON da.doctor_id = d.id
        WHERE d.hospital_id = %s
        GROUP BY d.id
        ORDER BY d.doctor_name
        """,
        (hospital["id"],),
    )
    services = fetch_all("SELECT * FROM services ORDER BY service_name")
    return render_template("doctor_management.html", hospital=hospital, doctors=doctors, services=services, days=DAYS)


@app.route("/hospital/services", methods=["GET", "POST"])
@role_required("hospital_admin")
def service_management():
    hospital = admin_hospital()
    if not hospital:
        flash("Hospital profile not found.", "danger")
        return redirect(url_for("hospital_dashboard"))
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            service_name = request.form.get("service_name", "").strip()
            description = request.form.get("description", "").strip()
            if service_name:
                service = fetch_one("SELECT id FROM services WHERE service_name = %s", (service_name,))
                if service:
                    execute("UPDATE services SET description = %s WHERE id = %s", (description, service["id"]))
                    service_id = service["id"]
                else:
                    service_id = execute("INSERT INTO services (service_name, description) VALUES (%s, %s)", (service_name, description))
                flash("Service saved.", "success")
                doctor_id = request.form.get("doctor_id", type=int)
                if doctor_id:
                    execute("INSERT IGNORE INTO doctor_services (doctor_id, service_id) VALUES (%s, %s)", (doctor_id, service_id))
                    execute("INSERT IGNORE INTO queues (hospital_id, service_id, current_queue, estimated_waiting_time) VALUES (%s, %s, 0, 15)", (hospital["id"], service_id))
        elif action == "assign":
            doctor_id = request.form.get("doctor_id", type=int)
            service_id = request.form.get("service_id", type=int)
            if doctor_id and service_id:
                doctor = fetch_one("SELECT id FROM doctors WHERE id = %s AND hospital_id = %s", (doctor_id, hospital["id"]))
                if doctor:
                    execute("INSERT IGNORE INTO doctor_services (doctor_id, service_id) VALUES (%s, %s)", (doctor_id, service_id))
                    execute("INSERT IGNORE INTO queues (hospital_id, service_id, current_queue, estimated_waiting_time) VALUES (%s, %s, 0, 15)", (hospital["id"], service_id))
                    flash("Service assigned to doctor.", "success")
        return redirect(url_for("service_management"))

    services = fetch_all("SELECT * FROM services ORDER BY service_name")
    doctors = fetch_all("SELECT id, doctor_name, specialization FROM doctors WHERE hospital_id = %s ORDER BY doctor_name", (hospital["id"],))
    assigned = fetch_all(
        """
        SELECT d.doctor_name, s.service_name
        FROM doctors d
        JOIN doctor_services ds ON ds.doctor_id = d.id
        JOIN services s ON s.id = ds.service_id
        WHERE d.hospital_id = %s
        ORDER BY d.doctor_name, s.service_name
        """,
        (hospital["id"],),
    )
    return render_template("service_management.html", hospital=hospital, services=services, doctors=doctors, assigned=assigned)


@app.route("/hospital/queues", methods=["GET", "POST"])
@role_required("hospital_admin")
def queue_management():
    hospital = admin_hospital()
    if not hospital:
        flash("Hospital profile not found.", "danger")
        return redirect(url_for("hospital_dashboard"))
    if request.method == "POST":
        service_id = request.form.get("service_id", type=int)
        current_queue = max(0, request.form.get("current_queue", type=int) or 0)
        waiting_time = max(0, request.form.get("estimated_waiting_time", type=int) or 0)
        execute(
            """
            INSERT INTO queues (hospital_id, service_id, current_queue, estimated_waiting_time)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE current_queue = VALUES(current_queue), estimated_waiting_time = VALUES(estimated_waiting_time)
            """,
            (hospital["id"], service_id, current_queue, waiting_time),
        )
        flash("Queue updated.", "success")
        return redirect(url_for("queue_management"))

    queues = fetch_all(
        """
        SELECT q.*, s.service_name
        FROM queues q
        JOIN services s ON s.id = q.service_id
        WHERE q.hospital_id = %s
        ORDER BY s.service_name
        """,
        (hospital["id"],),
    )
    services = fetch_all(
        """
        SELECT DISTINCT s.*
        FROM services s
        JOIN doctor_services ds ON ds.service_id = s.id
        JOIN doctors d ON d.id = ds.doctor_id
        WHERE d.hospital_id = %s
        ORDER BY s.service_name
        """,
        (hospital["id"],),
    )
    return render_template("queue_management.html", hospital=hospital, queues=queues, services=services)


@app.route("/hospital/appointments", methods=["GET", "POST"])
@role_required("hospital_admin")
def hospital_appointments():
    hospital = admin_hospital()
    if not hospital:
        flash("Hospital profile not found.", "danger")
        return redirect(url_for("hospital_dashboard"))
    if request.method == "POST":
        appointment_id = request.form.get("appointment_id", type=int)
        action = request.form.get("action", "status")
        status = request.form.get("status")
        appointment = fetch_one("SELECT * FROM appointments WHERE id = %s AND hospital_id = %s", (appointment_id, hospital["id"]))
        if appointment and action == "delete":
            execute("DELETE FROM appointments WHERE id = %s", (appointment_id,))
            if appointment["status"] not in {"completed", "rejected"}:
                execute(
                    """
                    UPDATE queues
                    SET current_queue = GREATEST(current_queue - 1, 0)
                    WHERE hospital_id = %s AND service_id = %s
                    """,
                    (hospital["id"], appointment["service_id"]),
                )
            flash("Appointment deleted.", "success")
        elif appointment and status in {"accepted", "rejected", "completed"}:
            previous_status = appointment["status"]
            execute("UPDATE appointments SET status = %s WHERE id = %s", (status, appointment_id))
            if status in {"completed", "rejected"} and previous_status not in {"completed", "rejected"}:
                execute(
                    """
                    UPDATE queues
                    SET current_queue = GREATEST(current_queue - 1, 0)
                    WHERE hospital_id = %s AND service_id = %s
                    """,
                    (hospital["id"], appointment["service_id"]),
                )
            flash("Appointment status updated.", "success")
        return redirect(url_for("hospital_appointments"))

    appointments = fetch_all(
        """
        SELECT a.*, u.name AS patient_name, u.phone AS patient_phone, d.doctor_name, s.service_name
        FROM appointments a
        JOIN users u ON u.id = a.patient_id
        JOIN doctors d ON d.id = a.doctor_id
        JOIN services s ON s.id = a.service_id
        WHERE a.hospital_id = %s
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
        """,
        (hospital["id"],),
    )
    return render_template("hospital_appointments.html", hospital=hospital, appointments=appointments)


@app.route("/hospital/feedback")
@role_required("hospital_admin")
def hospital_feedback():
    hospital = admin_hospital()
    feedback_rows = fetch_all(
        """
        SELECT f.*, u.name AS patient_name, d.doctor_name
        FROM feedback f
        JOIN users u ON u.id = f.patient_id
        JOIN doctors d ON d.id = f.doctor_id
        WHERE f.hospital_id = %s
        ORDER BY f.created_at DESC
        """,
        (hospital["id"],),
    )
    return render_template("hospital_feedback.html", hospital=hospital, feedback_rows=feedback_rows)


@app.route("/hospital/complaints")
@role_required("hospital_admin")
def hospital_complaints():
    hospital = admin_hospital()
    complaints = fetch_all(
        """
        SELECT c.*, u.name AS patient_name
        FROM complaints c
        JOIN users u ON u.id = c.patient_id
        WHERE c.hospital_id = %s
        ORDER BY c.created_at DESC
        """,
        (hospital["id"],),
    )
    return render_template("hospital_complaints.html", hospital=hospital, complaints=complaints)


@app.route("/super-admin/dashboard")
@role_required("super_admin")
def super_admin_dashboard():
    stats = {
        "hospitals": fetch_one("SELECT COUNT(*) AS count FROM hospitals")["count"],
        "pending": fetch_one("SELECT COUNT(*) AS count FROM hospitals WHERE status = 'pending'")["count"],
        "appointments": fetch_one("SELECT COUNT(*) AS count FROM appointments")["count"],
        "complaints": fetch_one("SELECT COUNT(*) AS count FROM complaints WHERE status <> 'resolved'")["count"],
    }
    hospitals = fetch_all("SELECT h.*, u.name AS admin_name, u.email AS admin_email FROM hospitals h LEFT JOIN users u ON u.id = h.admin_id ORDER BY h.status, h.hospital_name")
    complaints = fetch_all(
        """
        SELECT c.*, h.hospital_name, u.name AS patient_name
        FROM complaints c
        JOIN hospitals h ON h.id = c.hospital_id
        JOIN users u ON u.id = c.patient_id
        ORDER BY c.created_at DESC
        LIMIT 20
        """
    )
    status_rows = fetch_all("SELECT status, COUNT(*) AS total FROM appointments GROUP BY status")
    hospital_status_rows = fetch_all("SELECT status, COUNT(*) AS total FROM hospitals GROUP BY status")
    return render_template(
        "super_dashboard.html",
        stats=stats,
        hospitals=hospitals,
        complaints=complaints,
        quality_rows=quality_scores(),
        appointment_labels=[row["status"].title() for row in status_rows],
        appointment_values=[int(row["total"]) for row in status_rows],
        hospital_labels=[row["status"].title() for row in hospital_status_rows],
        hospital_values=[int(row["total"]) for row in hospital_status_rows],
    )


@app.route("/super-admin/hospital/<int:hospital_id>/status", methods=["POST"])
@role_required("super_admin")
def update_hospital_status(hospital_id):
    status = request.form.get("status")
    if status in {"pending", "approved", "rejected"}:
        execute("UPDATE hospitals SET status = %s WHERE id = %s", (status, hospital_id))
        flash("Hospital status updated.", "success")
    return redirect(url_for("super_admin_dashboard"))


@app.route("/super-admin/hospital/<int:hospital_id>/delete", methods=["POST"])
@role_required("super_admin")
def delete_hospital(hospital_id):
    hospital = fetch_one("SELECT hospital_name FROM hospitals WHERE id = %s", (hospital_id,))
    if not hospital:
        flash("Hospital not found or already deleted.", "warning")
        return redirect(url_for("super_admin_dashboard"))

    execute("DELETE FROM hospitals WHERE id = %s", (hospital_id,))
    flash(f"{hospital['hospital_name']} has been deleted from the platform.", "success")
    return redirect(url_for("super_admin_dashboard"))


@app.route("/super-admin/complaint/<int:complaint_id>/status", methods=["POST"])
@role_required("super_admin")
def update_complaint_status(complaint_id):
    status = request.form.get("status")
    if status in {"open", "in_review", "resolved"}:
        execute("UPDATE complaints SET status = %s WHERE id = %s", (status, complaint_id))
        flash("Complaint status updated.", "success")
    return redirect(url_for("super_admin_dashboard"))


if __name__ == "__main__":
    try:
        execute_schema()
    except Error as exc:
        print("Could not initialize the MySQL database.")
        print("Start XAMPP MySQL and check MYSQL_HOST, MYSQL_PORT, MYSQL_USER, and MYSQL_PASSWORD.")
        raise exc
    debug_mode = os.environ.get("FLASK_DEBUG", "1").lower() in {"1", "true", "yes"}
    server_host = os.environ.get("FLASK_HOST", "0.0.0.0")
    server_port = int(os.environ.get("FLASK_PORT", "5000"))
    lan_ip = get_lan_ip()
    print(f"HealthPilot local URL: http://127.0.0.1:{server_port}")
    print(f"HealthPilot WiFi URL:  http://{lan_ip}:{server_port}")
    app.run(host=server_host, port=server_port, debug=debug_mode)
