"""
Smart Parking Management & City Traffic Control System
Flask Web Application & REST APIs
"""
import os
import secrets
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

from models import init_db, seed_data_if_empty, get_db_connection
from traffic_engine import get_city_traffic_summary, get_smart_recommendations, simulate_traffic_pulse

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "smart_parking_secret_key_2026_x8931")

# Ensure database is initialized on startup
init_db()
seed_data_if_empty()

# ----------------- PAGE ROUTES -----------------
@app.route("/")
def index():
    return render_template("index.html")

# ----------------- AUTHENTICATION APIS -----------------
@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip()
    phone = data.get("phone", "").strip()
    vehicle_plate = data.get("vehicle_plate", "").strip()
    preferred_vehicle = data.get("preferred_vehicle", "Car")

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required."}), 400

    if not full_name:
        full_name = username.capitalize()
    if not email:
        email = f"{username}@example.com"
    if not vehicle_plate:
        vehicle_plate = f"REG-{secrets.token_hex(2).upper()}"

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if username or email already exists
    cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return jsonify({"success": False, "message": "Username or email is already registered."}), 409

    pwd_hash = generate_password_hash(password)
    try:
        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, email, phone, vehicle_plate, preferred_vehicle)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (username, pwd_hash, full_name, email, phone, vehicle_plate, preferred_vehicle))
        user_id = cursor.lastrowid
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "message": f"Database error: {str(e)}"}), 500

    # Auto login on successful registration
    session["user_id"] = user_id
    session["username"] = username

    user_info = {
        "id": user_id,
        "username": username,
        "full_name": full_name,
        "email": email,
        "vehicle_plate": vehicle_plate,
        "preferred_vehicle": preferred_vehicle
    }
    conn.close()
    return jsonify({"success": True, "message": "Registration successful!", "user": user_info})

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? OR email = ?", (username, username))
    user = cursor.fetchone()
    conn.close()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"success": False, "message": "Invalid username or password."}), 401

    session["user_id"] = user["id"]
    session["username"] = user["username"]

    return jsonify({
        "success": True,
        "message": f"Welcome back, {user['full_name']}!",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "email": user["email"],
            "vehicle_plate": user["vehicle_plate"],
            "preferred_vehicle": user["preferred_vehicle"]
        }
    })

@app.route("/api/auth/demo-login", methods=["POST"])
def demo_login():
    data = request.get_json() or {}
    role = data.get("role", "driver1") # driver1, biker_sarah, ev_james, admin

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (role,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return jsonify({"success": False, "message": "Demo user not found."}), 404

    session["user_id"] = user["id"]
    session["username"] = user["username"]

    return jsonify({
        "success": True,
        "message": f"Logged in as Demo Profile: {user['full_name']} ({user['preferred_vehicle']} User)",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "email": user["email"],
            "vehicle_plate": user["vehicle_plate"],
            "preferred_vehicle": user["preferred_vehicle"]
        }
    })

@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully."})

@app.route("/api/auth/me", methods=["GET"])
def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"authenticated": False, "user": None})

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, full_name, email, phone, vehicle_plate, preferred_vehicle FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        session.clear()
        return jsonify({"authenticated": False, "user": None})

    return jsonify({"authenticated": True, "user": dict(user)})

# ----------------- PARKING LOCATIONS & SLOTS APIS -----------------
@app.route("/api/parking/locations", methods=["GET"])
def list_locations():
    vehicle_filter = request.args.get("vehicle_type", "All")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT l.*,
               COUNT(s.id) as total_hub_slots,
               SUM(CASE WHEN s.status = 'Available' THEN 1 ELSE 0 END) as available_slots,
               SUM(CASE WHEN s.status = 'Occupied' THEN 1 ELSE 0 END) as occupied_slots,
               SUM(CASE WHEN s.status = 'Reserved' THEN 1 ELSE 0 END) as reserved_slots,
               SUM(CASE WHEN s.status = 'Available' AND s.vehicle_type = 'Car' THEN 1 ELSE 0 END) as car_available,
               SUM(CASE WHEN s.status = 'Available' AND s.vehicle_type = 'Bike' THEN 1 ELSE 0 END) as bike_available,
               SUM(CASE WHEN s.status = 'Available' AND s.vehicle_type = 'EV' THEN 1 ELSE 0 END) as ev_available,
               SUM(CASE WHEN s.status = 'Available' AND s.vehicle_type = 'SUV' THEN 1 ELSE 0 END) as suv_available
        FROM parking_locations l
        LEFT JOIN parking_slots s ON l.id = s.location_id
        GROUP BY l.id
    """)
    locations = [dict(row) for row in cursor.fetchall()]

    for loc in locations:
        loc["amenities_list"] = [a.strip() for a in loc["amenities"].split(",")] if loc["amenities"] else []
        # Calculate dynamic occupancy percentage
        total = loc["total_slots"] or 1
        occupied = loc["occupied_slots"] + loc["reserved_slots"]
        loc["occupancy_pct"] = round((occupied / total) * 100)

    conn.close()
    return jsonify({"success": True, "locations": locations})

@app.route("/api/parking/slots/<int:location_id>", methods=["GET"])
def get_location_slots(location_id):
    vehicle_type = request.args.get("vehicle_type")
    floor_filter = request.args.get("floor")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM parking_locations WHERE id = ?", (location_id,))
    loc = cursor.fetchone()
    if not loc:
        conn.close()
        return jsonify({"success": False, "message": "Location not found"}), 404

    query = "SELECT * FROM parking_slots WHERE location_id = ?"
    params = [location_id]

    if vehicle_type and vehicle_type != "All":
        query += " AND vehicle_type = ?"
        params.append(vehicle_type)

    if floor_filter and floor_filter != "All":
        query += " AND floor = ?"
        params.append(floor_filter)

    query += " ORDER BY floor ASC, id ASC"
    cursor.execute(query, params)
    slots = [dict(s) for s in cursor.fetchall()]

    # Group slots by floor for structured 2D lot layout
    floors = {}
    for slot in slots:
        fl = slot["floor"]
        if fl not in floors:
            floors[fl] = []
        floors[fl].append(slot)

    conn.close()
    return jsonify({
        "success": True,
        "location": dict(loc),
        "total_returned_slots": len(slots),
        "floors": floors,
        "slots": slots
    })

# ----------------- BOOKING APIS -----------------
@app.route("/api/bookings/create", methods=["POST"])
def create_booking():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Please log in to book a parking slot."}), 401

    data = request.get_json() or {}
    location_id = data.get("location_id")
    slot_id = data.get("slot_id")
    vehicle_type = data.get("vehicle_type", "Car")
    vehicle_plate = data.get("vehicle_plate", "").strip().upper()
    duration_hours = int(data.get("duration_hours", 2))
    start_time_str = data.get("start_time")

    if not location_id:
        return jsonify({"success": False, "message": "Location is required."}), 400
    if not vehicle_plate:
        return jsonify({"success": False, "message": "Vehicle plate number is required."}), 400
    if duration_hours < 1:
        duration_hours = 1

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get location pricing
    cursor.execute("SELECT * FROM parking_locations WHERE id = ?", (location_id,))
    location = cursor.fetchone()
    if not location:
        conn.close()
        return jsonify({"success": False, "message": "Parking location not found."}), 404

    # Determine hourly rate by vehicle type
    rate_map = {
        "Car": location["hourly_car"],
        "Bike": location["hourly_bike"],
        "EV": location["hourly_ev"],
        "SUV": location["hourly_suv"]
    }
    hourly_rate = rate_map.get(vehicle_type, location["hourly_car"])
    total_amount = round(hourly_rate * duration_hours, 2)

    # If slot_id is not specified, auto-select the best available slot matching vehicle type
    selected_slot = None
    if slot_id:
        cursor.execute("SELECT * FROM parking_slots WHERE id = ? AND location_id = ?", (slot_id, location_id))
        selected_slot = cursor.fetchone()
        if not selected_slot:
            conn.close()
            return jsonify({"success": False, "message": "Selected slot does not exist."}), 404
        if selected_slot["status"] != "Available":
            conn.close()
            return jsonify({"success": False, "message": f"Slot {selected_slot['slot_number']} is currently {selected_slot['status']}. Please select another slot."}), 409
    else:
        cursor.execute("""
            SELECT * FROM parking_slots 
            WHERE location_id = ? AND vehicle_type = ? AND status = 'Available'
            ORDER BY id ASC LIMIT 1
        """, (location_id, vehicle_type))
        selected_slot = cursor.fetchone()

        # Fallback to Car slot if bike/SUV specific slot not found
        if not selected_slot and vehicle_type in ["Car", "SUV"]:
            cursor.execute("""
                SELECT * FROM parking_slots 
                WHERE location_id = ? AND status = 'Available'
                ORDER BY id ASC LIMIT 1
            """, (location_id,))
            selected_slot = cursor.fetchone()

        if not selected_slot:
            conn.close()
            return jsonify({"success": False, "message": f"No available parking slots for {vehicle_type} at this location."}), 409

    # Generate unique booking code
    booking_code = f"PK-{secrets.token_hex(3).upper()}"
    
    # Calculate start and end time
    now = datetime.now()
    if start_time_str:
        try:
            start_dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M")
        except Exception:
            start_dt = now
    else:
        start_dt = now

    end_dt = start_dt + timedelta(hours=duration_hours)

    # Insert booking
    cursor.execute("""
        INSERT INTO bookings (booking_code, user_id, slot_id, location_id, vehicle_type, vehicle_plate, start_time, end_time, duration_hours, total_amount, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active')
    """, (
        booking_code,
        user_id,
        selected_slot["id"],
        location_id,
        vehicle_type,
        vehicle_plate,
        start_dt.strftime("%Y-%m-%d %H:%M:%S"),
        end_dt.strftime("%Y-%m-%d %H:%M:%S"),
        duration_hours,
        total_amount
    ))
    booking_id = cursor.lastrowid

    # Mark slot as reserved
    cursor.execute("""
        UPDATE parking_slots 
        SET status = 'Reserved', current_booking_id = ?
        WHERE id = ?
    """, (booking_id, selected_slot["id"]))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": f"Slot {selected_slot['slot_number']} reserved successfully!",
        "booking": {
            "id": booking_id,
            "booking_code": booking_code,
            "location_name": location["name"],
            "location_address": location["address"],
            "slot_number": selected_slot["slot_number"],
            "floor": selected_slot["floor"],
            "vehicle_type": vehicle_type,
            "vehicle_plate": vehicle_plate,
            "start_time": start_dt.strftime("%b %d, %Y - %I:%M %p"),
            "end_time": end_dt.strftime("%b %d, %Y - %I:%M %p"),
            "duration_hours": duration_hours,
            "hourly_rate": hourly_rate,
            "total_amount": total_amount,
            "status": "Active"
        }
    })

@app.route("/api/bookings/my", methods=["GET"])
def get_my_bookings():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Not authenticated"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT b.*,
               l.name as location_name,
               l.address as location_address,
               l.lat as location_lat,
               l.lng as location_lng,
               l.traffic_status,
               s.slot_number,
               s.floor,
               s.is_ev_charger
        FROM bookings b
        JOIN parking_locations l ON b.location_id = l.id
        JOIN parking_slots s ON b.slot_id = s.id
        WHERE b.user_id = ?
        ORDER BY b.id DESC
    """, (user_id,))
    rows = cursor.fetchall()

    bookings = []
    now = datetime.now()

    for r in rows:
        b = dict(r)
        # Parse times for timer & status
        try:
            end_time = datetime.strptime(b["end_time"], "%Y-%m-%d %H:%M:%S")
            remaining_seconds = max(0, int((end_time - now).total_seconds()))
            is_expired = remaining_seconds == 0
        except Exception:
            remaining_seconds = 0
            is_expired = False

        b["remaining_seconds"] = remaining_seconds
        b["is_expired"] = is_expired
        bookings.append(b)

    conn.close()
    return jsonify({"success": True, "bookings": bookings})

@app.route("/api/bookings/<int:booking_id>/cancel", methods=["POST"])
def cancel_booking(booking_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Not authenticated"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM bookings WHERE id = ? AND user_id = ?", (booking_id, user_id))
    booking = cursor.fetchone()
    if not booking:
        conn.close()
        return jsonify({"success": False, "message": "Booking not found."}), 404

    if booking["status"] != "Active":
        conn.close()
        return jsonify({"success": False, "message": f"Booking is already {booking['status']}."}), 400

    # Free the slot
    cursor.execute("UPDATE parking_slots SET status = 'Available', current_booking_id = NULL WHERE id = ?", (booking["slot_id"],))
    # Update booking status
    cursor.execute("UPDATE bookings SET status = 'Cancelled' WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Booking cancelled and slot released successfully."})

@app.route("/api/bookings/<int:booking_id>/extend", methods=["POST"])
def extend_booking(booking_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Not authenticated"}), 401

    data = request.get_json() or {}
    extra_hours = int(data.get("extra_hours", 1))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT b.*, l.hourly_car, l.hourly_bike, l.hourly_ev, l.hourly_suv 
        FROM bookings b 
        JOIN parking_locations l ON b.location_id = l.id
        WHERE b.id = ? AND b.user_id = ?
    """, (booking_id, user_id))
    b = cursor.fetchone()
    if not b:
        conn.close()
        return jsonify({"success": False, "message": "Booking not found."}), 404

    rate_map = {
        "Car": b["hourly_car"],
        "Bike": b["hourly_bike"],
        "EV": b["hourly_ev"],
        "SUV": b["hourly_suv"]
    }
    rate = rate_map.get(b["vehicle_type"], b["hourly_car"])
    add_amount = rate * extra_hours

    try:
        current_end = datetime.strptime(b["end_time"], "%Y-%m-%d %H:%M:%S")
        new_end = current_end + timedelta(hours=extra_hours)
    except Exception:
        new_end = datetime.now() + timedelta(hours=extra_hours)

    cursor.execute("""
        UPDATE bookings 
        SET end_time = ?, duration_hours = duration_hours + ?, total_amount = total_amount + ?
        WHERE id = ?
    """, (new_end.strftime("%Y-%m-%d %H:%M:%S"), extra_hours, add_amount, booking_id))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": f"Parking extended by {extra_hours} hour(s). New end time: {new_end.strftime('%I:%M %p')}",
        "new_end_time": new_end.strftime("%Y-%m-%d %H:%M:%S")
    })

# ----------------- CITY TRAFFIC & SMART ROUTING APIS -----------------
@app.route("/api/traffic/summary", methods=["GET"])
def traffic_summary():
    data = get_city_traffic_summary()
    return jsonify({"success": True, "traffic": data})

@app.route("/api/recommendations", methods=["GET"])
def recommendations():
    vtype = request.args.get("vehicle_type", "Car")
    zone = request.args.get("zone", None)
    recs = get_smart_recommendations(vehicle_type=vtype, preferred_zone=zone)
    return jsonify({"success": True, "recommendations": recs})

@app.route("/api/simulate/pulse", methods=["POST"])
def simulate_step():
    res = simulate_traffic_pulse()
    return jsonify({"success": True, "details": res})

if __name__ == "__main__":
    print("Starting Smart Parking & Traffic Management Portal on http://127.0.0.1:5000 ...")
    app.run(host="0.0.0.0", port=5000, debug=False)
