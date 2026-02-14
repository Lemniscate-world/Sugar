import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    try:
        r = requests.get(f"{BASE_URL}/api/health")
        print(f"Health: {r.status_code} - {r.json()}")
    except Exception as e:
        print(f"Health Failed: {e}")

def test_status():
    try:
        r = requests.get(f"{BASE_URL}/api/status")
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            print(json.dumps(r.json(), indent=2))
    except Exception as e:
        print(f"Status Failed: {e}")

def test_conversations():
    try:
        r = requests.get(f"{BASE_URL}/api/conversations")
        print(f"Conversations: {r.status_code}")
        if r.status_code == 200:
            print(json.dumps(r.json(), indent=2))
        
        # Create new
        r = requests.post(f"{BASE_URL}/api/conversations")
        print(f"New Conversation: {r.status_code}")
        if r.status_code == 200:
            new_id = r.json()['id']
            print(f"Created ID: {new_id}")
            return new_id
    except Exception as e:
        print(f"Conversations Failed: {e}")
    return None

def test_chat(cid):
    if not cid:
        print("Skipping chat test (no ID)")
        return
    
    print(f"Testing Chat Stream with ID: {cid}")
    try:
        payload = {
            "messages": [{"role": "user", "content": "Hello"}],
            "model": "mistral",
            "conversation_id": cid
        }
        r = requests.post(f"{BASE_URL}/api/chat/stream", json=payload, stream=True)
        print(f"Chat Status: {r.status_code}")
        
        for line in r.iter_lines():
            if line:
                print(f"Chunk: {line.decode('utf-8')}")
                if b"[DONE]" in line:
                    break
    except Exception as e:
        print(f"Chat Failed: {e}")

if __name__ == "__main__":
    print("-" * 20)
    test_health()
    print("-" * 20)
    test_status()
    print("-" * 20)
    cid = test_conversations()
    print("-" * 20)
    test_chat(cid)
