"""
Smart Parking Management & City Traffic Control System
Database Schema and Model Helpers
"""
import sqlite3
import os
import json
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "smart_parking.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        vehicle_plate TEXT,
        preferred_vehicle TEXT DEFAULT 'Car',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Parking Locations / Hubs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS parking_locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        address TEXT NOT NULL,
        zone TEXT NOT NULL,
        lat REAL NOT NULL,
        lng REAL NOT NULL,
        total_slots INTEGER NOT NULL,
        hourly_car REAL DEFAULT 40.0,
        hourly_bike REAL DEFAULT 15.0,
        hourly_ev REAL DEFAULT 50.0,
        hourly_suv REAL DEFAULT 60.0,
        amenities TEXT,
        traffic_status TEXT DEFAULT 'Normal',
        congestion_index INTEGER DEFAULT 25,
        rating REAL DEFAULT 4.7
    );
    """)

    # Parking Slots
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS parking_slots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location_id INTEGER NOT NULL,
        slot_number TEXT NOT NULL,
        floor TEXT NOT NULL,
        vehicle_type TEXT NOT NULL, -- 'Car', 'Bike', 'EV', 'SUV'
        status TEXT DEFAULT 'Available', -- 'Available', 'Occupied', 'Reserved'
        is_ev_charger INTEGER DEFAULT 0,
        is_accessible INTEGER DEFAULT 0,
        current_booking_id INTEGER,
        FOREIGN KEY (location_id) REFERENCES parking_locations(id)
    );
    """)

    # City Traffic Corridors / Roads
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS traffic_corridors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        corridor_name TEXT NOT NULL,
        from_area TEXT NOT NULL,
        to_area TEXT NOT NULL,
        congestion_level TEXT NOT NULL, -- 'Smooth', 'Moderate', 'Heavy'
        congestion_pct INTEGER NOT NULL, -- 0-100%
        avg_speed_kmh REAL NOT NULL,
        delay_minutes INTEGER DEFAULT 0,
        polyline_coords TEXT NOT NULL,
        incident_report TEXT,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Bookings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_code TEXT UNIQUE NOT NULL,
        user_id INTEGER NOT NULL,
        slot_id INTEGER NOT NULL,
        location_id INTEGER NOT NULL,
        vehicle_type TEXT NOT NULL,
        vehicle_plate TEXT NOT NULL,
        start_time TIMESTAMP NOT NULL,
        end_time TIMESTAMP NOT NULL,
        duration_hours INTEGER NOT NULL,
        total_amount REAL NOT NULL,
        status TEXT DEFAULT 'Active', -- 'Active', 'Completed', 'Cancelled'
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (slot_id) REFERENCES parking_slots(id),
        FOREIGN KEY (location_id) REFERENCES parking_locations(id)
    );
    """)

    conn.commit()
    conn.close()

def seed_data_if_empty():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if data exists
    cursor.execute("SELECT COUNT(*) FROM parking_locations")
    count = cursor.fetchone()[0]

    if count == 0:
        # 1. Create Default Demo Users
        users = [
            ("driver1", generate_password_hash("password123"), "Alex Mercer", "alex@urbanmobility.org", "+1-555-0192", "CA-78-MK-9021", "Car"),
            ("biker_sarah", generate_password_hash("password123"), "Sarah Chen", "sarah.c@cityfast.io", "+1-555-0144", "BK-99-TR-4412", "Bike"),
            ("ev_james", generate_password_hash("password123"), "James Rodriguez", "james.ev@ecodrive.com", "+1-555-0188", "EV-50-PL-1010", "EV"),
            ("admin", generate_password_hash("admin123"), "City Traffic Administrator", "admin@smartcity.gov", "+1-555-0100", "GOV-01-SM-0001", "SUV")
        ]
        cursor.executemany("""
            INSERT INTO users (username, password_hash, full_name, email, phone, vehicle_plate, preferred_vehicle)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, users)

        # 2. Create Parking Locations across city
        locations = [
            (
                "Downtown Metro Central Hub",
                "104 Financial District Blvd, Central City",
                "Downtown Core",
                40.7128, -74.0060,
                32,
                50.0, 20.0, 60.0, 70.0,
                "Covered Parking, 24/7 Security, High-Speed EV Chargers, Valet Available, Metro Direct Connect",
                "Smooth",
                28,
                4.9
            ),
            (
                "Cyber Tech Park & Innovation Center",
                "450 Silicon Avenue, Tech Quarter",
                "Tech District",
                40.7282, -73.9942,
                28,
                40.0, 15.0, 50.0, 55.0,
                "Solar Canopies, Automated Barrier, Fast EV Bay, Bike Lockers, Cafe Onsite",
                "Moderate",
                52,
                4.8
            ),
            (
                "Harborfront Grand Plaza Parking",
                "88 Marina Esplanade, Waterfront",
                "Harbor Zone",
                40.7028, -74.0150,
                24,
                35.0, 15.0, 45.0, 50.0,
                "Scenic Views, CCTV Monitored, Wheelchair Accessible, Water Taxi Terminal Link",
                "Smooth",
                18,
                4.6
            ),
            (
                "Civic Center & City Hall Terminal",
                "210 Government Way, Civic Quarter",
                "North Gate",
                40.7350, -74.0010,
                26,
                45.0, 18.0, 55.0, 65.0,
                "Covered Multi-Level, License Plate Recognition, Security Patrol, Bus Terminal Transfer",
                "Heavy",
                78,
                4.7
            ),
            (
                "Westside Transit & Shopping Arena",
                "772 West Avenue, Westside Gateway",
                "Westside",
                40.7190, -74.0200,
                30,
                30.0, 12.0, 40.0, 45.0,
                "Mall Connected, Express Elevators, EV Superchargers, Car Wash Station",
                "Smooth",
                22,
                4.5
            )
        ]

        cursor.executemany("""
            INSERT INTO parking_locations (name, address, zone, lat, lng, total_slots, hourly_car, hourly_bike, hourly_ev, hourly_suv, amenities, traffic_status, congestion_index, rating)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, locations)

        # 3. Create Slots for each location (mixture of Car, Bike, EV, SUV, Ground/Floor 1/Basement)
        cursor.execute("SELECT id, total_slots FROM parking_locations")
        loc_rows = cursor.fetchall()

        slot_entries = []
        for loc in loc_rows:
            loc_id = loc[0]
            total = loc[1]
            
            # Allocation pattern: 50% Car, 20% Bike, 15% EV, 15% SUV
            for i in range(1, total + 1):
                floor = "Ground" if i <= 10 else ("Floor 1" if i <= 20 else "Basement")
                
                if i % 10 in [1, 2]:
                    v_type = "Bike"
                    prefix = "BK"
                    is_ev = 0
                elif i % 10 in [3, 4]:
                    v_type = "EV"
                    prefix = "EV"
                    is_ev = 1
                elif i % 10 == 5:
                    v_type = "SUV"
                    prefix = "SV"
                    is_ev = 0
                else:
                    v_type = "Car"
                    prefix = "CR"
                    is_ev = 0

                slot_num = f"{prefix}-{floor[0]}{i:02d}"
                # Initial random occupancy for realism
                initial_status = "Occupied" if (i % 5 == 0 and i > 4) else "Available"
                is_accessible = 1 if i == 1 else 0

                slot_entries.append((loc_id, slot_num, floor, v_type, initial_status, is_ev, is_accessible))

        cursor.executemany("""
            INSERT INTO parking_slots (location_id, slot_number, floor, vehicle_type, status, is_ev_charger, is_accessible)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, slot_entries)

        # 4. Create Traffic Corridors with coordinates for map display
        corridors = [
            (
                "Broadway Express Corridor",
                "Civic Center",
                "Downtown Metro",
                "Heavy",
                78,
                18.5,
                14,
                json.dumps([
                    [40.7350, -74.0010],
                    [40.7280, -74.0025],
                    [40.7200, -74.0040],
                    [40.7128, -74.0060]
                ]),
                "Road construction on 5th Ave crossing causing slow crawl. Divert to Harbor route."
            ),
            (
                "Riverfront Bypass Expressway",
                "Westside Gateway",
                "Harborfront Plaza",
                "Smooth",
                20,
                55.0,
                0,
                json.dumps([
                    [40.7190, -74.0200],
                    [40.7100, -74.0185],
                    [40.7028, -74.0150]
                ]),
                "Clear traffic flow. Green corridor recommended for swift parking access."
            ),
            (
                "Silicon Highway & Tech Avenue",
                "Downtown Metro",
                "Cyber Tech Park",
                "Moderate",
                48,
                38.0,
                5,
                json.dumps([
                    [40.7128, -74.0060],
                    [40.7200, -74.0010],
                    [40.7282, -73.9942]
                ]),
                "Moderate evening tech park commuting flow. 5 mins minor delay."
            ),
            (
                "North-South Urban Transit Arterial",
                "Civic Quarter",
                "Tech Quarter",
                "Moderate",
                55,
                32.0,
                8,
                json.dumps([
                    [40.7350, -74.0010],
                    [40.7310, -73.9970],
                    [40.7282, -73.9942]
                ]),
                "Traffic signals synchronized for bus rapid transit."
            ),
            (
                "Coastal Boulevard Link",
                "Harbor Zone",
                "Westside Arena",
                "Smooth",
                15,
                58.0,
                0,
                json.dumps([
                    [40.7028, -74.0150],
                    [40.7080, -74.0190],
                    [40.7190, -74.0200]
                ]),
                "Free-flowing multi-lane scenic route. Zero congestion detected."
            )
        ]

        cursor.executemany("""
            INSERT INTO traffic_corridors (corridor_name, from_area, to_area, congestion_level, congestion_pct, avg_speed_kmh, delay_minutes, polyline_coords, incident_report)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, corridors)

        # 5. Insert Sample Initial Bookings for Demo User (Alex Mercer)
        now = datetime.now()
        demo_booking = (
            "PK-884210",
            1, # Alex Mercer
            2, # Slot 2 (Bike or Car)
            1, # Downtown Metro
            "Car",
            "CA-78-MK-9021",
            now.strftime("%Y-%m-%d %H:%M:%S"),
            (now + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            2,
            100.0,
            "Active"
        )
        cursor.execute("""
            INSERT INTO bookings (booking_code, user_id, slot_id, location_id, vehicle_type, vehicle_plate, start_time, end_time, duration_hours, total_amount, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, demo_booking)

        # Mark that slot as Reserved
        cursor.execute("UPDATE parking_slots SET status = 'Reserved', current_booking_id = 1 WHERE id = 2")

        conn.commit()

    conn.close()

if __name__ == "__main__":
    init_db()
    seed_data_if_empty()
    print("Database initialized and seeded successfully.")
