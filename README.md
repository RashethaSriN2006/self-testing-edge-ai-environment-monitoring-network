# 🚗 PARKSMART AI — Smart Parking & Urban Traffic Management System

A full-stack, real-time smart city web application that connects **city traffic monitoring** with **smart parking reservations** to eliminate parking search time and reduce urban traffic congestion.

---

## 🌟 Key Features

### 1. 🚦 Real-Time City Traffic Monitoring
- **Live Interactive Map (Leaflet.js)**: Displays major city traffic corridors with color-coded congestion overlays (Green: Smooth, Amber: Moderate, Red: Heavy crawl).
- **Traffic Congestion Index Ticker**: Real-time traffic condition updates directly in the portal header.
- **AI Traffic-Avoidance Route Planner**: Automatically recommends the fastest parking hubs that bypass congested corridors, saving up to 25+ minutes of commuting delays.

### 2. 🅿️ Smart Parking Hubs & 2D Visual Bay Grid
- **Multi-Hub Monitoring**: Real-time vacancy metrics across city hubs (Downtown Metro, Cyber Tech Park, Harborfront Plaza, Civic Center Terminal, Westside Arena).
- **Interactive 2D Parking Lot Layout**:
  - Color-coded bays: **Green (Available)**, **Red (Occupied)**, **Purple (Reserved)**, **Cyan (EV Charger)**.
  - Multi-level filtering: Ground Floor, Floor 1, Basement.
  - One-click slot booking: click any green bay directly on the layout to reserve it instantly.

### 3. 🚗 Multi-Vehicle Slot Allocation
- Tailored slots and pricing for different vehicle categories:
  - 🚗 **Car** (Sedan, Hatchback)
  - 🏍️ **Bike** (Motorcycles, Scooters, Two-wheelers)
  - ⚡ **Electric Vehicle (EV)** (Equipped with Level 3 fast charging plugs)
  - 🚙 **SUV / Large Vehicle** (Wide bays)

### 4. 🔐 User Authentication (New & Existing Users)
- **Custom User Registration**: Users can register with their own unique username, password, email, full name, and license plate.
- **Secure Authentication**: Passwords hashed using industry-standard `werkzeug.security` (PBKDF2 SHA-256).
- **Instant Demo Login**: One-click demo profiles available for Car drivers, Bike riders, and EV users.

### 5. 🎫 Digital Parking Pass & "My Bookings" Dashboard
- **Instant Digital Pass**: Generates a scannable QR code and barcode pass with boom barrier access credentials.
- **Live Countdown Timer**: Real-time countdown tracking remaining parking duration.
- **Pass Management**: Extend parking time (+1 hour) or cancel reservations anytime to free the slot for other drivers.

### 6. 📊 Smart City IoT & Traffic Sensor Simulator
- Operator controls to trigger live traffic pulse steps or continuous auto-pulse (every 5 seconds) to simulate realistic vehicle arrivals, departures, and traffic flow changes.

---

## 🚀 How to Run the Application

### Method 1: Using Python
```powershell
cd C:\Sentrienv\smart_parking_system
python run.py
```

### Method 2: Accessing the Portal
Once launched, open your web browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🧪 Running the Automated Tests
```powershell
cd C:\Sentrienv\smart_parking_system
python -m unittest test_app.py
```
*(All 6 integration test suites verify user registration, login, slot filtering, reservation, pass generation, countdown, and traffic routing).*

---

## 📁 Project Architecture
```
smart_parking_system/
├── app.py                 # Flask server & REST API endpoints
├── models.py              # SQLite database schema, initialization & seed data
├── traffic_engine.py      # City traffic calculator & AI parking recommender
├── run.py                 # Production runner script
├── test_app.py            # Complete automated test suite
├── smart_parking.db       # Embedded SQLite database
├── templates/
│   └── index.html         # Modern single-page portal template
└── static/
    ├── css/
    │   └── styles.css     # Glassmorphic cyber dark-mode styles
    └── js/
        └── app.js         # Interactive map, visual bay grid, QR pass, countdowns
```
