import base64
import json
from fastapi import Request, HTTPException

async def parse_push(request: Request) -> dict:
    payload = await request.json()
    try:
        data = payload["message"]["data"]
        return json.loads(base64.b64decode(data).decode("utf-8"))
    except Exception as e:
        raise HTTPException(400, f"Bad Pub/Sub payload: {e}")
