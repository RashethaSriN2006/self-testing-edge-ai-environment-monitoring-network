"""
Convenient launcher for Smart Parking & Traffic Management Portal
"""
import os
import sys

# Support utf-8 terminal outputs on Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure correct working directory
current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)
sys.path.insert(0, current_dir)

from app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 60)
    print("PARKSMART AI - Urban Traffic & Smart Parking System")
    print(f"Web Portal Live at: http://127.0.0.1:{port}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=False)
