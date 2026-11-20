"""
Automated Integration and Functional Tests for Smart Parking & Traffic Management Portal
"""
import unittest
import json
from app import app
from models import get_db_connection

class TestSmartParkingSystem(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_01_index_page(self):
        """Test home index page renders properly"""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"ParkSmart", response.data)
        self.assertIn(b"City Traffic & Map", response.data)

    def test_02_user_registration_and_login(self):
        """Test custom new user registration and authentication flow"""
        test_username = f"rider_neo"
        test_payload = {
            "username": test_username,
            "password": "Password!99",
            "full_name": "Neo Anderson",
            "email": "neo@matrix.io",
            "phone": "+1-555-8822",
            "vehicle_plate": "NY-77-ZZ-9999",
            "preferred_vehicle": "Bike"
        }

        # 1. Register
        reg_res = self.app.post('/api/auth/register', data=json.dumps(test_payload), content_type='application/json')
        self.assertIn(reg_res.status_code, [200, 409])
        
        # 2. Login
        login_payload = {
            "username": test_username,
            "password": "Password!99"
        }
        login_res = self.app.post('/api/auth/login', data=json.dumps(login_payload), content_type='application/json')
        self.assertEqual(login_res.status_code, 200)
        login_data = json.loads(login_res.data)
        self.assertTrue(login_data['success'])
        self.assertEqual(login_data['user']['username'], test_username)

        # 3. Check Current Session /api/auth/me
        me_res = self.app.get('/api/auth/me')
        self.assertEqual(me_res.status_code, 200)
        me_data = json.loads(me_res.data)
        self.assertTrue(me_data['authenticated'])
        self.assertEqual(me_data['user']['vehicle_plate'], "NY-77-ZZ-9999")

    def test_03_parking_locations_and_slots(self):
        """Test fetching locations and slots per location with vehicle filtering"""
        res = self.app.get('/api/parking/locations')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertGreater(len(data['locations']), 0)

        first_loc_id = data['locations'][0]['id']

        # Fetch slots for this location
        slots_res = self.app.get(f'/api/parking/slots/{first_loc_id}?vehicle_type=Car')
        self.assertEqual(slots_res.status_code, 200)
        slots_data = json.loads(slots_res.data)
        self.assertTrue(slots_data['success'])
        self.assertIn('floors', slots_data)
        self.assertGreater(len(slots_data['slots']), 0)

    def test_04_booking_lifecycle(self):
        """Test full booking lifecycle: auto-pick slot, reserve, view passes, extend, and cancel"""
        # 1. Login with demo user
        login_res = self.app.post('/api/auth/demo-login', data=json.dumps({"role": "driver1"}), content_type='application/json')
        self.assertEqual(login_res.status_code, 200)

        # 2. Create Booking for a Car
        booking_payload = {
            "location_id": 1,
            "vehicle_type": "Car",
            "vehicle_plate": "TEST-PLATE-101",
            "duration_hours": 3
        }
        book_res = self.app.post('/api/bookings/create', data=json.dumps(booking_payload), content_type='application/json')
        self.assertEqual(book_res.status_code, 200)
        book_data = json.loads(book_res.data)
        self.assertTrue(book_data['success'])
        booking_id = book_data['booking']['id']
        slot_number = book_data['booking']['slot_number']
        self.assertIsNotNone(booking_id)

        # 3. View in My Bookings
        my_res = self.app.get('/api/bookings/my')
        self.assertEqual(my_res.status_code, 200)
        my_data = json.loads(my_res.data)
        self.assertTrue(my_data['success'])
        user_booking_ids = [b['id'] for b in my_data['bookings']]
        self.assertIn(booking_id, user_booking_ids)

        # 4. Extend Booking by 1 hour
        ext_res = self.app.post(f'/api/bookings/{booking_id}/extend', data=json.dumps({"extra_hours": 1}), content_type='application/json')
        self.assertEqual(ext_res.status_code, 200)
        ext_data = json.loads(ext_res.data)
        self.assertTrue(ext_data['success'])

        # 5. Cancel Booking
        cancel_res = self.app.post(f'/api/bookings/{booking_id}/cancel')
        self.assertEqual(cancel_res.status_code, 200)
        cancel_data = json.loads(cancel_res.data)
        self.assertTrue(cancel_data['success'])

    def test_05_traffic_summary_and_recommendations(self):
        """Test city traffic summary and AI recommendations algorithm"""
        # Traffic summary
        res = self.app.get('/api/traffic/summary')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertIn('avg_congestion_pct', data['traffic'])
        self.assertIn('corridors', data['traffic'])

        # AI Recommendations
        rec_res = self.app.get('/api/recommendations?vehicle_type=Bike')
        self.assertEqual(rec_res.status_code, 200)
        rec_data = json.loads(rec_res.data)
        self.assertTrue(rec_data['success'])
        self.assertGreater(len(rec_data['recommendations']), 0)
        # Verify recommendation has score & traffic details
        first_rec = rec_data['recommendations'][0]
        self.assertIn('composite_score', first_rec)
        self.assertIn('badge', first_rec)

    def test_06_simulation_pulse(self):
        """Test IoT traffic and slot pulse step"""
        res = self.app.post('/api/simulate/pulse')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])

if __name__ == '__main__':
    unittest.main()
