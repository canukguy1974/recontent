from fastapi import FastAPI, Request
from packages.common.pubsub import parse_push
from packages.common.logging import get_logger
from services.worker.processors import compositor, captioner, analyzer, social_media

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
    elif typ == "analyze_set":
        result = await analyzer.run(msg)
        return {"status": "ok", "result": result}
    elif typ == "generate_social":
        result = await social_media.run(msg)
        return {"status": "ok", "result": result}
    return {"status": "ignored", "type": typ}
