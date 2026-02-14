import requests
import json
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("verify_tools")

BASE_URL = "http://localhost:8000"

def test_tools():
    logger.info("--- Status Check ---")
    r = requests.get(f"{BASE_URL}/api/status")
    status = r.json()
    logger.info("Engine Status: %s", json.dumps(status.get("engine"), indent=2))
    
    if not status.get("engine", {}).get("connectors", {}).get("obsidian"):
        logger.warning("Obsidian not configured. Skipping search test.")
        return

    logger.info("--- Chat Tool Test (Search) ---")
    cid = requests.post(f"{BASE_URL}/api/conversations").json()['id']
    logger.info("Conversation: %s", cid)
    
    payload = {
        "messages": [{"role": "user", "content": "Search my notes for 'todo' or 'task'"}],
        "model": "glm-5:cloud",
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
                            print(data["content"], end="", flush=True) # Keep print for stream content as it's raw output
                        elif "error" in data:
                            logger.error("Error: %s", data['error'])
                    except:
                        pass
        print("\n") # Newline
        logger.info("(Stream Finished)")
    except Exception as e:
        logger.error("Chat execution failed: %s", e)

if __name__ == "__main__":
    test_tools()
