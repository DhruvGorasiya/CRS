# test_api.py
import requests
import json

base_url = "http://127.0.0.1:5000"

def test_burnout_scores():
    response = requests.post(
        f"{base_url}/api/burnout-scores",
        json={"nuid": "12345"}
    )
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=4))

def test_recommendations():
    response = requests.post(
        f"{base_url}/api/recommendations",
        json={"nuid": "0", "semester": 3}
    )
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=4))

if __name__ == "__main__":
    print("Testing burnout scores API...")
    test_burnout_scores()
    
    print("\nTesting recommendations API...")
    test_recommendations()