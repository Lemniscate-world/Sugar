import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_tools():
    print("--- Status Check ---")
    r = requests.get(f"{BASE_URL}/api/status")
    status = r.json()
    print("Engine Status:", json.dumps(status.get("engine"), indent=2))
    
    if not status.get("engine", {}).get("connectors", {}).get("obsidian"):
        print("⚠️ Obsidian not configured. Skipping search test.")
        return

    print("\n--- Chat Tool Test (Search) ---")
    cid = requests.post(f"{BASE_URL}/api/conversations").json()['id']
    print(f"Conversation: {cid}")
    
    payload = {
        "messages": [{"role": "user", "content": "Search my notes for 'todo' or 'task'"}],
        "model": "tinyllama",
        "conversation_id": cid
    }
    
    try:
        r = requests.post(f"{BASE_URL}/api/chat/stream", json=payload, stream=True)
        for line in r.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith("data: "):
                    data_str = line_str[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        if "content" in data:
                            print(data["content"], end="", flush=True)
                        elif "error" in data:
                            print(f"\nError: {data['error']}")
                    except:
                        pass
        print("\n\n(Stream Finished)")
    except Exception as e:
        print(f"Chat execution failed: {e}")

if __name__ == "__main__":
    test_tools()
