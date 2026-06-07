from typing import Any
import httpx
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Constants
KANKA_API_BASE = "https://api.kanka.io/1.0"

# Load from environment variables
KANKA_API_TOKEN = os.getenv("KANKA_API_TOKEN", "")
KANKA_CAMPAIGN_ID = os.getenv("KANKA_CAMPAIGN_ID", "")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

async def make_kanka_request(endpoint: str) -> dict[str, Any] | None:
    """Make a request to the Kanka API with proper authentication and error handling."""
    headers = {
        "Authorization": f"Bearer {KANKA_API_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    url = f"{KANKA_API_BASE}/campaigns/{KANKA_CAMPAIGN_ID}/{endpoint}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"error": str(e)}
        
async def create_kanka_entity(endpoint: str, data: dict[str, Any]) -> dict[str, Any] | None:
    """Create a new entity in Kanka via POST request."""
    headers = {
        "Authorization": f"Bearer {KANKA_API_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    url = f"{KANKA_API_BASE}/campaigns/{KANKA_CAMPAIGN_ID}/{endpoint}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=data, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"error": str(e)}

async def update_kanka_entity(endpoint: str, data: dict[str, Any]) -> dict[str, Any] | None:
    """Update an entity in Kanka via PUT request."""
    headers = {
        "Authorization": f"Bearer {KANKA_API_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    url = f"{KANKA_API_BASE}/campaigns/{KANKA_CAMPAIGN_ID}/{endpoint}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(url, headers=headers, json=data, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"error": str(e)}