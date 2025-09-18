from fastapi import FastAPI, Request
from packages.common.pubsub import parse_push
from packages.common.logging import get_logger
from services.worker.processors import compositor, captioner

app = FastAPI(title="recontent Worker")
log = get_logger("worker")

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/pubsub")
async def pubsub_push(request: Request):
    msg = await parse_push(request)
    typ = msg.get("type")
    log.info(f"Received job type={typ}")
    if typ == "composite":
        uris = compositor.run(msg)
        return {"status": "ok", "outputs": uris}
    return {"status": "ignored", "type": typ}
