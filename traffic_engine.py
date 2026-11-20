"""
Traffic Analytics & Smart Routing Engine for Urban Parking
Simulates live sensor feeds, calculates congestion delays, and suggests traffic-free parking hubs.
"""
import random
import json
from datetime import datetime
from models import get_db_connection

def get_city_traffic_summary():
    """Returns aggregated traffic status for the city"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM traffic_corridors")
    corridors = [dict(row) for row in cursor.fetchall()]

    for c in corridors:
        c['polyline_coords'] = json.loads(c['polyline_coords'])

    total_pct = sum(c['congestion_pct'] for c in corridors)
    avg_congestion = round(total_pct / len(corridors), 1) if corridors else 30

    if avg_congestion < 35:
        overall_status = "Smooth / Free Flow"
        status_color = "emerald"
    elif avg_congestion < 65:
        overall_status = "Moderate Traffic"
        status_color = "amber"
    else:
        overall_status = "High Congestion / Delays"
        status_color = "rose"

    conn.close()
    return {
        "corridors": corridors,
        "avg_congestion_pct": avg_congestion,
        "overall_status": overall_status,
        "status_color": status_color,
        "active_corridors": len(corridors),
        "total_delays_min": sum(c['delay_minutes'] for c in corridors)
    }

def get_smart_recommendations(vehicle_type='Car', preferred_zone=None):
    """
    Evaluates all parking locations and recommends the optimal hub:
    - High slot availability for requested vehicle
    - Low traffic congestion on connecting corridors
    - Lowest estimated arrival delay
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT l.*, 
               COUNT(s.id) as total_hub_slots,
               SUM(CASE WHEN s.status = 'Available' AND s.vehicle_type = ? THEN 1 ELSE 0 END) as available_for_type,
               SUM(CASE WHEN s.status = 'Available' THEN 1 ELSE 0 END) as total_available
        FROM parking_locations l
        LEFT JOIN parking_slots s ON l.id = s.location_id
        GROUP BY l.id
    """, (vehicle_type,))
    hubs = [dict(row) for row in cursor.fetchall()]

    # Fetch corridors to map traffic impact
    cursor.execute("SELECT * FROM traffic_corridors")
    corridors = [dict(r) for r in cursor.fetchall()]

    recommendations = []
    for hub in hubs:
        # Score calculation:
        # Higher available slots = better
        # Lower congestion index = better
        avail = hub['available_for_type'] or 0
        total_avail = hub['total_available'] or 0
        cong = hub['congestion_index'] or 30

        # Heuristic score (100 = best)
        # availability weight: 50%, congestion avoidance: 50%
        avail_ratio = (avail / (hub['total_slots'] / 4)) if hub['total_slots'] else 0
        avail_score = min(50, avail_ratio * 40)
        traffic_score = max(0, 50 - (cong * 0.5))
        composite_score = round(avail_score + traffic_score, 1)

        # Recommendation badge
        if cong < 30 and avail > 2:
            badge = "Traffic-Free & Fast Parking"
            badge_class = "badge-success"
            eta_delay = 0
        elif cong < 60:
            badge = "Moderate Flow"
            badge_class = "badge-warning"
            eta_delay = 4
        else:
            badge = "Bottleneck Alert"
            badge_class = "badge-danger"
            eta_delay = 12

        rate_key = f"hourly_{vehicle_type.lower()}"
        rate = hub.get(rate_key, hub.get('hourly_car', 40.0))

        recommendations.append({
            "hub_id": hub['id'],
            "name": hub['name'],
            "address": hub['address'],
            "zone": hub['zone'],
            "lat": hub['lat'],
            "lng": hub['lng'],
            "available_for_vehicle": avail,
            "total_available": total_avail,
            "total_slots": hub['total_slots'],
            "congestion_index": cong,
            "traffic_status": hub['traffic_status'],
            "hourly_rate": rate,
            "rating": hub['rating'],
            "badge": badge,
            "badge_class": badge_class,
            "eta_delay_mins": eta_delay,
            "composite_score": composite_score,
            "amenities": hub['amenities'].split(",") if hub['amenities'] else []
        })

    # Sort best composite score first
    recommendations.sort(key=lambda x: x['composite_score'], reverse=True)
    conn.close()
    return recommendations

def simulate_traffic_pulse():
    """
    Randomly shifts traffic density and simulates vehicles entering / departing slots
    to give a live smart-city feel.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Update corridors with slight realistic drift
    cursor.execute("SELECT id, congestion_pct FROM traffic_corridors")
    corridors = cursor.fetchall()
    for cid, pct in corridors:
        delta = random.randint(-8, 8)
        new_pct = max(10, min(95, pct + delta))
        if new_pct < 35:
            level = "Smooth"
            speed = round(random.uniform(50, 65), 1)
            delay = 0
        elif new_pct < 70:
            level = "Moderate"
            speed = round(random.uniform(30, 48), 1)
            delay = random.randint(3, 7)
        else:
            level = "Heavy"
            speed = round(random.uniform(12, 25), 1)
            delay = random.randint(10, 22)

        cursor.execute("""
            UPDATE traffic_corridors 
            SET congestion_pct = ?, congestion_level = ?, avg_speed_kmh = ?, delay_minutes = ?, last_updated = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_pct, level, speed, delay, cid))

    # 2. Update parking locations congestion index
    cursor.execute("SELECT id, congestion_index FROM parking_locations")
    locs = cursor.fetchall()
    for lid, cindex in locs:
        delta = random.randint(-6, 6)
        new_cindex = max(10, min(90, cindex + delta))
        status = "Smooth" if new_cindex < 35 else ("Moderate" if new_cindex < 65 else "Heavy")
        cursor.execute("UPDATE parking_locations SET congestion_index = ?, traffic_status = ? WHERE id = ?", (new_cindex, status, lid))

    # 3. Randomly toggle 1 or 2 unreserved slots to mimic physical sensor arrivals/departures
    cursor.execute("SELECT id, status FROM parking_slots WHERE status != 'Reserved' ORDER BY RANDOM() LIMIT 2")
    sample_slots = cursor.fetchall()
    for sid, st in sample_slots:
        new_status = 'Occupied' if st == 'Available' else 'Available'
        cursor.execute("UPDATE parking_slots SET status = ? WHERE id = ?", (new_status, sid))

    conn.commit()
    conn.close()
    return {"status": "success", "message": "City traffic & parking sensor state updated"}
