# HealthPilot Viva-Oriented Technical Documentation

This document explains the theory and working concepts behind the technology stack used in **HealthPilot: AI-Based Healthcare Service, Queue & Route Management Platform**. It is written for viva/project explanation, so the focus is on **what each technology does, why it is used, and how it works conceptually**.

## 1. Project Concept

HealthPilot is a centralized healthcare platform that connects patients, hospitals, and super admins.

The main idea is:

```text
Symptoms -> AI service recommendation -> nearby hospitals -> queue comparison -> appointment booking -> route navigation
```

The system solves common healthcare access problems:

- Patients may not know which medical department or service they need.
- Patients need to compare hospitals based on waiting queue, rating, and distance.
- Hospitals need to manage doctors, services, appointments, and queues.
- Admins need to approve hospitals and monitor service quality.

HealthPilot combines web development, database management, artificial intelligence, map services, routing APIs, and dashboard analytics.

## 2. Overall Architecture

HealthPilot follows a typical **three-tier web application architecture**.

### Presentation Layer

This is the frontend visible to users.

Technologies:

- HTML
- CSS
- JavaScript
- Bootstrap
- Bootstrap Icons
- Chart.js
- Mappls Web JS SDK

Responsibilities:

- Display forms, dashboards, tables, maps, buttons, and alerts
- Collect user input
- Show AI results
- Show hospital lists
- Show appointment and queue details
- Interact with map and navigation services

### Application Layer

This is the backend logic layer.

Technology:

- Python Flask

Responsibilities:

- Handle routes and requests
- Manage login sessions
- Apply role-based access control
- Run AI prediction
- Query database
- Process bookings
- Generate token numbers
- Calculate ranking scores
- Communicate with Mappls Route API

### Data Layer

This layer stores permanent data.

Technology:

- MySQL using XAMPP

Responsibilities:

- Store users
- Store hospitals
- Store doctors
- Store services
- Store appointments
- Store queues
- Store feedback
- Store complaints

## 3. Python

Python is used as the main backend programming language.

### Why Python?

Python is suitable for this project because:

- It has simple syntax.
- It is widely used in web development.
- It has strong AI and machine learning libraries.
- It integrates well with databases and APIs.
- Flask, pandas, scikit-learn, and sentence-transformers are Python-based.

### Role in HealthPilot

Python is used to:

- Create Flask backend routes
- Connect to MySQL
- Process patient symptoms
- Run AI prediction
- Calculate hospital ranking
- Generate appointment tokens
- Call external APIs

## 4. Flask

Flask is a lightweight Python web framework.

### What Is a Web Framework?

A web framework provides ready-made tools to build web applications. It helps developers handle:

- URLs
- HTTP requests
- HTTP responses
- templates
- forms
- sessions
- routing
- redirects

Without a framework, the developer would need to manually handle many low-level web server tasks.

### Why Flask Is Used

Flask is used because:

- It is lightweight and easy to understand.
- It gives control over project structure.
- It is good for academic and medium-size projects.
- It supports templates using Jinja2.
- It can easily connect with MySQL and AI modules.

### Flask Working in HealthPilot

When a user opens a page, the browser sends an HTTP request to Flask.

Example:

```text
GET /patient/dashboard
```

Flask checks the route in `app.py`, runs the related Python function, fetches data from MySQL, renders an HTML template, and sends the final HTML response back to the browser.

### Flask Route Concept

A route maps a URL to a Python function.

Example:

```python
@app.route("/patient/dashboard")
def patient_dashboard():
    ...
```

This means when the browser requests `/patient/dashboard`, Flask executes the `patient_dashboard()` function.

### Flask Sessions

Sessions store temporary user-specific data.

In HealthPilot, sessions store:

- logged-in user ID
- patient selected location

Example:

```python
session["user_id"] = user["id"]
session["patient_location"] = {"lat": ..., "lng": ...}
```

Sessions help the system remember who is logged in while moving between pages.

### Flask Templates

Flask uses Jinja2 templates to generate dynamic HTML.

Example:

```html
{{ current_user.name }}
```

This value is filled by Flask before sending the page to the browser.

## 5. MySQL

MySQL is a relational database management system.

### What Is a Relational Database?

A relational database stores data in tables. Tables have rows and columns.

Example:

```text
users table
id | name | email | role
```

Relationships are created using primary keys and foreign keys.

### Why MySQL Is Used

MySQL is used because:

- It is reliable and widely used.
- It supports structured data.
- It is suitable for hospital, doctor, appointment, and user records.
- It supports relationships between tables.
- It works well with XAMPP for local development.

### Role of MySQL in HealthPilot

MySQL stores:

- patient accounts
- hospital admin accounts
- hospital profiles
- doctors
- services
- appointment records
- queue counts
- feedback
- complaints

### Primary Key

A primary key uniquely identifies each row in a table.

Example:

```text
users.id
```

Each user has a unique ID.

### Foreign Key

A foreign key connects one table to another.

Example:

```text
hospitals.admin_id -> users.id
```

This means a hospital is linked to a hospital admin user.

### Many-to-Many Relationship

A doctor can provide multiple services, and a service can be provided by multiple doctors.

This is handled using a bridge table:

```text
doctor_services
```

This table connects:

```text
doctors.id <-> services.id
```

## 6. XAMPP

XAMPP is a local server package.

### Why XAMPP Is Used

XAMPP provides MySQL locally, so the project can run on a personal computer without needing an online database server.

In this project:

- MySQL runs through XAMPP.
- Flask connects to MySQL using `localhost:3306`.

### Role in Development

XAMPP is useful for:

- local testing
- database creation
- phpMyAdmin database viewing
- easy MySQL startup and shutdown

## 7. HTML

HTML stands for HyperText Markup Language.

### Role of HTML

HTML creates the structure of web pages.

In HealthPilot, HTML is used for:

- forms
- tables
- dashboards
- hospital cards
- navigation bars
- map containers
- appointment pages

Example:

```html
<form method="post">
    <textarea name="symptoms"></textarea>
</form>
```

This creates a form where the patient can enter symptoms.

## 8. CSS

CSS stands for Cascading Style Sheets.

### Role of CSS

CSS controls the visual appearance of the website.

In HealthPilot, CSS controls:

- colors
- spacing
- layout
- cards
- buttons
- mobile responsiveness
- dashboard design
- home page design

Main CSS file:

```text
static/css/styles.css
```

### Why CSS Is Important

CSS improves usability and professionalism. For healthcare software, clean design is important because users must quickly understand information such as:

- waiting time
- hospital rating
- emergency warning
- appointment status

## 9. JavaScript

JavaScript is used for client-side interactivity.

### Why JavaScript Is Used

HTML and CSS alone create static pages. JavaScript makes pages interactive without always reloading the page.

### Role in HealthPilot

JavaScript is used for:

- getting browser location
- selecting location on map
- displaying hospital markers
- drawing routes
- calling backend API endpoints
- updating travel time
- rendering charts

Important JavaScript files:

```text
static/js/location.js
static/js/nearby.js
static/js/route.js
static/js/charts.js
```

## 10. Bootstrap

Bootstrap is a frontend CSS framework.

### Why Bootstrap Is Used

Bootstrap provides ready-made responsive components.

Examples:

- buttons
- forms
- cards
- grids
- tables
- alerts
- navbar

### Bootstrap Grid System

Bootstrap uses a 12-column responsive grid system.

This helps create layouts like:

```text
3 cards in one row on desktop
1 card per row on mobile
```

### Role in HealthPilot

Bootstrap helps make the UI:

- responsive
- consistent
- mobile-friendly
- faster to develop

## 11. Bootstrap Icons

Bootstrap Icons is an icon library.

### Why Icons Are Used

Icons improve readability and make the UI more intuitive.

Examples in HealthPilot:

- `bi-hospital` for hospitals
- `bi-star` for rating
- `bi-people` for queue
- `bi-clock` for waiting time
- `bi-signpost-2` for route
- `bi-calendar` for appointment

Icons help users understand information quickly.

## 12. Chart.js

Chart.js is a JavaScript charting library.

### Why Chart.js Is Used

Admin dashboards need visual analytics. Charts are easier to understand than raw numbers.

### Role in HealthPilot

Chart.js shows:

- appointment status distribution
- most booked services
- hospital status analytics
- platform statistics

### Conceptual Working

Flask sends chart labels and values to the HTML template. JavaScript receives the data and Chart.js renders charts on `<canvas>` elements.

Example data:

```text
labels = ["Pending", "Completed"]
values = [5, 10]
```

Chart.js converts this data into visual charts.

## 13. Mappls MapmyIndia

Mappls MapmyIndia is used for maps and navigation.

### Why Mappls Is Used

This project requires:

- map display
- patient location selection
- hospital markers
- route calculation
- distance and travel time
- navigation links

Mappls provides APIs and SDKs for these features.

### Mappls Web JS SDK

The Web JS SDK displays interactive maps in the browser.

In HealthPilot, it is used in:

```text
patient_location.html
nearby_hospitals.html
route.html
```

### Patient Location Selection

The patient can:

- allow browser GPS
- click manually on Mappls map
- type latitude and longitude manually

The selected location becomes the starting point for hospital search and route drawing.

### Hospital Markers

Hospital coordinates are stored in MySQL:

```text
latitude
longitude
```

JavaScript reads these coordinates and places markers on the map.

### Mappls Route API

The Route API calculates:

- route path
- distance
- travel duration

In HealthPilot, Flask calls the Mappls Route API through:

```text
/api/mappls/route
```

### Why Route API Is Called Through Flask

Calling the route API through Flask is useful because:

- backend can control API requests
- frontend code stays simpler
- errors can be handled in one place
- API key management is cleaner

### Mappls Direction URL

HealthPilot also creates external navigation links:

```text
https://mappls.com/direction
```

This opens route navigation in Mappls.

## 14. Browser Geolocation

Browser geolocation is a web API that gives the user's current location.

### How It Works

The browser asks the user for permission. If the user allows it, the browser returns:

- latitude
- longitude
- accuracy

In JavaScript:

```javascript
navigator.geolocation.getCurrentPosition(...)
```

### Role in HealthPilot

It is used to get the patient's precise location for:

- hospital search
- travel distance
- route starting point

### Limitation

Some browsers require HTTPS for precise location. On local WiFi, manual map selection is provided as an alternative.

## 15. AI and Machine Learning Module

HealthPilot uses a machine learning approach for symptom-to-service recommendation.

### Why AI Is Used

Patients may type symptoms in different ways:

```text
I have fever and cough
fevr couhg body pain
high temperature and weakness
```

A simple keyword system may fail when:

- spelling mistakes occur
- symptoms are written naturally
- words are not exactly matched

AI helps by comparing meaning rather than only exact words.

## 16. Sentence Transformer

Sentence Transformer is a deep learning model that converts text into numerical vectors called embeddings.

### What Is an Embedding?

An embedding is a list of numbers representing the meaning of text.

Example:

```text
"fever cough cold" -> [0.12, -0.45, 0.88, ...]
```

Texts with similar meaning have similar vectors.

Example:

```text
"fever cough cold"
"high temperature and cough"
```

These two sentences should have close embeddings because their meanings are similar.

### Model Used

```text
all-MiniLM-L6-v2
```

### Why This Model Is Used

It is:

- lightweight
- fast
- good for semantic similarity
- suitable for small and medium projects
- commonly used for sentence embedding tasks

## 17. KNN Similarity Search

KNN means K-Nearest Neighbors.

### Concept

KNN finds the closest example from stored training data.

In HealthPilot:

1. Dataset symptoms are converted into embeddings.
2. Patient symptoms are converted into an embedding.
3. KNN compares the patient embedding with stored embeddings.
4. The nearest matching dataset row is selected.
5. The service and first-aid text from that row are returned.

### Why Cosine Similarity Is Used

Cosine similarity compares direction of vectors instead of their size.

For text embeddings, direction is more important because it represents semantic meaning.

Cosine distance:

```text
0 means very similar
1 means less similar
```

Confidence is calculated from distance:

```text
confidence = (1 - distance) * 100
```

## 18. AI Training Process

Training file:

```text
train_model.py
```

Dataset:

```text
symptom_service_dataset.csv
```

Training steps:

```text
Load CSV
-> clean symptoms text
-> load SentenceTransformer
-> convert symptoms into embeddings
-> train NearestNeighbors model
-> save model using joblib
```

Generated files:

```text
service_knn.pkl
service_data.pkl
```

### Why joblib Is Used

Training the model every time the app starts would be slow. Joblib saves the trained model to disk so Flask can load it later.

## 19. AI Prediction Process

Prediction file:

```text
ai_service.py
```

Function:

```python
predict_medical_service(symptoms)
```

Prediction steps:

```text
Take patient symptom text
-> check emergency keywords
-> convert text into embedding
-> search nearest dataset example using KNN
-> return service, confidence, first-aid, emergency flag
```

### Emergency Rule

Emergency symptoms should not depend only on ML similarity.

So the system first checks emergency keywords:

```text
chest pain
breathing problem
shortness of breath
unconscious
heavy bleeding
stroke
heart attack
severe burn
seizure
```

If found, the system immediately recommends Emergency with 100% confidence.

This is a safety rule.

## 20. Hospital Ranking Logic

After AI suggests a service, HealthPilot finds hospitals that provide that service.

Hospitals are ranked using:

```text
Final Score =
(hospital_rating * 0.4)
+ (doctor_rating * 0.2)
+ ((1 / waiting_time) * 0.2)
+ ((1 / travel_time) * 0.2)
```

### Meaning of the Formula

- Hospital rating has high importance.
- Doctor rating also affects ranking.
- Lower waiting time gives better score.
- Lower travel time gives better score.

### Why Inverse Is Used

Waiting time and travel time should reduce the score when they increase.

Using:

```text
1 / waiting_time
1 / travel_time
```

means smaller time gives larger value.

## 21. Appointment Token Generation

When a patient books an appointment, the system generates a token number.

Example format:

```text
HP-01-20260430-001
```

This includes:

- project prefix
- service ID
- appointment date
- sequence number

### Why Token Is Needed

Token helps:

- patients track their appointment
- hospitals manage order
- queue management become easier

## 22. Queue Management

Queue table stores:

- hospital ID
- service ID
- current queue count
- estimated waiting time

When appointment is booked:

- queue count increases

When appointment is completed or rejected:

- queue count decreases

This gives patients real-time waiting information.

## 23. Feedback and Rating System

Patients can rate:

- doctor
- cleanliness
- waiting experience
- staff support

These ratings help update hospital and doctor quality.

### Why Feedback Is Important

Feedback improves:

- hospital transparency
- patient trust
- service quality monitoring
- super admin quality analysis

## 24. Complaints Module

Patients can submit complaints against hospitals.

Complaint status:

```text
open
in_review
resolved
```

Super admin can monitor and update complaint status.

This creates accountability in the platform.

## 25. Role-Based Access Control

HealthPilot has three roles:

```text
patient
hospital_admin
super_admin
```

Each role has different permissions.

### Why RBAC Is Needed

Without role-based access:

- patients might access admin pages
- hospital admins might approve hospitals
- unauthorized users could modify data

RBAC protects the system by allowing users to access only their relevant modules.

## 26. Security Concepts

### Password Hashing

Passwords are not stored as plain text.

HealthPilot uses PBKDF2 hashing.

### Why Hashing Is Important

If the database is exposed, plain passwords would be dangerous. Hashing makes it difficult to recover original passwords.

### Session Security

After login, Flask stores the user ID in session. Each protected route checks whether the logged-in user has permission.

## 27. APIs Used

### Internal Flask APIs

```text
/api/hospitals
```

Returns hospitals that provide a selected service.

```text
/api/mappls/route
```

Returns route data from patient location to hospital.

### External APIs

Mappls APIs:

- Web JS SDK
- Route API
- Direction URL

Browser API:

- Geolocation API

## 28. Why This Tech Stack Is Suitable

### Flask

Good for backend logic and API handling.

### MySQL

Good for structured healthcare records.

### Sentence Transformer

Good for natural-language symptom understanding.

### KNN

Simple and effective for matching symptoms to known examples.

### Mappls

Good for maps, location, routing, and navigation.

### Chart.js

Good for dashboard analytics.

### Bootstrap

Good for fast, responsive UI development.

## 29. Possible Viva Questions and Answers

### Q1. Why did you use Flask?

Flask is lightweight, easy to understand, and flexible. It allows us to define routes, handle forms, manage sessions, render templates, and connect with MySQL and AI modules.

### Q2. Why did you use MySQL?

MySQL is a relational database suitable for structured data like users, hospitals, doctors, services, appointments, queues, feedback, and complaints. It supports table relationships using primary and foreign keys.

### Q3. What is the role of AI in this project?

AI is used to understand patient symptoms written in natural language and recommend the most suitable medical service. It also provides first-aid guidance and identifies emergency symptoms.

### Q4. Why use Sentence Transformer?

Sentence Transformer converts symptom sentences into semantic embeddings. This allows the system to compare meaning, not just exact keywords, so it can handle natural language and spelling mistakes better.

### Q5. What is KNN?

KNN stands for K-Nearest Neighbors. It finds the closest matching symptom example from the dataset based on embedding similarity and returns the related medical service.

### Q6. Why use cosine similarity?

Cosine similarity is useful for text embeddings because it compares direction of vectors, which represents semantic meaning.

### Q7. Why is there an emergency keyword rule?

Emergency cases should not depend only on machine learning prediction. If symptoms like chest pain, unconsciousness, or heavy bleeding are detected, the system immediately recommends Emergency.

### Q8. How is hospital ranking calculated?

Hospitals are ranked using hospital rating, doctor rating, waiting time, and travel time. Higher ratings improve score, while higher waiting and travel times reduce score.

### Q9. What is Mappls used for?

Mappls is used to display maps, select patient location, show hospital markers, calculate route distance and travel time, draw navigation route, and open external navigation.

### Q10. Why use Chart.js?

Chart.js is used to show analytics visually in admin dashboards, such as appointment status and most booked services.

### Q11. How does appointment booking work?

The patient selects a hospital, doctor, service, date, and time. The backend creates an appointment record, generates a token number, updates the queue, and redirects the patient to the route page.

### Q12. How is patient location used?

Patient location is stored in session and used as the starting point for hospital ranking, travel time calculation, navigation links, and route drawing.

### Q13. What is role-based access control?

Role-based access control restricts pages and actions based on user roles. Patients, hospital admins, and super admins can access only their own modules.

### Q14. How can the AI model be improved?

The AI model can be improved by adding more symptom examples to the dataset, including regional language symptoms, more spelling variations, and real medical consultation data.

### Q15. Does this system replace doctors?

No. HealthPilot only provides service suggestions and basic first-aid guidance. It does not replace professional medical advice or diagnosis.

## 30. Summary

HealthPilot combines:

- Flask for backend logic
- MySQL for database storage
- Bootstrap and CSS for frontend design
- JavaScript for interactivity
- Mappls for maps and routing
- Chart.js for analytics
- Sentence Transformer and KNN for AI symptom recommendation

The project demonstrates how web development, database systems, AI, APIs, and user-interface design can work together to improve healthcare service access.
