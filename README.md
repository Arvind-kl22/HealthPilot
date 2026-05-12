# HealthPilot

HealthPilot is an AI-based healthcare service platform designed to connect patients, hospitals, and administrators. It provides intelligent service recommendations, hospital comparisons, queue management, and route navigation to improve healthcare accessibility and efficiency.

## Features

- **AI-Powered Service Recommendation**: Predicts the required medical service based on patient symptoms.
- **Hospital Management**: Enables hospitals to manage doctors, services, appointments, and queues.
- **Queue Comparison**: Allows patients to compare hospitals based on waiting times, ratings, and distance.
- **Appointment Booking**: Simplifies the process of booking appointments with hospitals.
- **Route Navigation**: Provides navigation to the selected hospital using Mappls APIs.
- **Ambulance Management**: Real-time ambulance booking with nearby search, live tracking, and driver management.
- **Admin Dashboard**: Allows administrators to monitor hospital performance and approve new hospitals.

## Ambulance Management System

HealthPilot includes a comprehensive ambulance management system with the following features:

- **Nearby Ambulance Search**: Patients can search for ambulances from nearby hospitals, sorted by distance using Haversine formula.
- **Flexible Booking Options**: Choose specific ambulances or broadcast requests to all ambulances within 10km radius.
- **Interactive Maps**: Visual representation of patient and ambulance locations using Mappls API.
- **Real-time Tracking**: Live location updates and route visualization after ambulance acceptance.
- **Driver Management**: Ambulance drivers can accept/reject requests and update their status.
- **Status Management**: Automatic status reset to prevent ambulances from being stuck in "busy" state.

### Ambulance Workflow

1. Patient requests ambulance from nearby page
2. System displays available ambulances sorted by distance
3. Patient can book specific ambulance or broadcast to all
4. Drivers receive notifications and can accept requests
5. Patient gets live tracking with route visualization
6. Ambulance status updates throughout the process

## Project Structure

- **Backend**: Flask-based backend for handling requests and managing the database.
- **AI Service**: Predicts medical services using a trained KNN model and Sentence Transformers.
- **Frontend**: HTML, CSS, and JavaScript for user interaction, with Chart.js for analytics and Mappls for navigation.
- **Ambulance System**: Real-time ambulance booking with SocketIO for live tracking and Mappls for route visualization.
- **Database**: MySQL database for storing user, hospital, appointment, and ambulance data.

## Setup Instructions

### Prerequisites

- Python 3.10+
- MySQL Server
- Virtual Environment (recommended)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd HealthPilot
   ```

2. Set up a virtual environment:
   ```bash
   python -m venv venv1
   source venv1/Scripts/activate  # On Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure the database:
   - Update `DB_CONFIG` in `app.py` with your MySQL credentials.
   - Run the main schema script:
     ```bash
     mysql -u <username> -p <database_name> < database/schema.sql
     ```
   - Run the ambulance schema script:
     ```bash
     mysql -u <username> -p <database_name> < database/ambulance_schema.sql
     ```

5. Train the AI model:
   ```bash
   python train_model.py
   ```

6. Run the application:
   ```bash
   python app.py
   ```

7. Access the application at `http://127.0.0.1:5000`.

## Key Files

- `app.py`: Main Flask application with ambulance management routes.
- `ai_service.py`: AI service for symptom analysis and service prediction.
- `train_model.py`: Script to train the KNN model.
- `templates/`: HTML templates for the frontend, including ambulance pages.
- `static/`: Static assets (CSS, JavaScript, images) including ambulance tracking scripts.
- `database/schema.sql`: Database schema including ambulance tables.
- `database/ambulance_schema.sql`: Ambulance-specific database schema.

## Technologies Used

- **Backend**: Flask, MySQL, SocketIO
- **AI**: Sentence Transformers, scikit-learn, pandas
- **Frontend**: HTML, CSS, JavaScript, Chart.js, Mappls APIs
- **Real-time Features**: SocketIO for live ambulance tracking
- **Other**: Joblib for model persistence

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgments

- Mappls for navigation APIs
- Sentence Transformers for AI modeling
- Flask for backend development