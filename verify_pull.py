import requests
import json

BASE_URL = "http://localhost:8000"

def test_pull():
    print("Testing Pull 'tinyllama'...")
    try:
        r = requests.post(f"{BASE_URL}/api/models/pull", json={"name": "tinyllama"}, stream=True)
        print(f"Pull Status: {r.status_code}")
        
        for line in r.iter_lines():
            if line:
                print(f"Chunk: {line.decode('utf-8')}")
                if b"[DONE]" in line:
                    break
    except Exception as e:
        print(f"Pull Failed: {e}")

if __name__ == "__main__":
    test_pull()
