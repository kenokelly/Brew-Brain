import sys
import os
# Add current directory to path
sys.path.append(os.getcwd())
# Add app directory to path
sys.path.append(os.path.join(os.getcwd(), 'app'))

from flask import Flask
try:
    from app.api.routes import api_bp
    from app.core.config import set_config
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

app = Flask(__name__)
app.register_blueprint(api_bp)

def test_check():
    # Set some mock config
    set_config("batch_name", "Test Batch")
    set_config("og", "1.055")
    set_config("target_fg", "1.010")
    set_config("style", "American IPA")
    
    with app.test_client() as client:
        response = client.get('/api/brew_day_check')
        print(f"Status Code: {response.status_code}")
        data = response.get_json()
        print(f"Data: {data}")
        
        if data['status'] == 'success':
            print("--- CHECKS ---")
            for check in data['data']['checks']:
                print(f"[{check['status'].upper()}] {check['name']}: {check['message']}")
            print(f"READINESS SCORE: {data['data']['score']}%")

if __name__ == "__main__":
    test_check()
