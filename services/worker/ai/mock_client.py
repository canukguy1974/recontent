from PIL import Image, ImageDraw
from io import BytesIO

class MockAIClient:
    def composite(self, agent_bytes: bytes, room_bytes: bytes, brief: str) -> list[bytes]:
        img = Image.open(BytesIO(room_bytes)).convert("RGB")
        out = []
        for i in range(3):
            im = img.copy()
            draw = ImageDraw.Draw(im)
            draw.rectangle([(10, 10), (360, 80)], fill=(0, 0, 0, 160))
            draw.text((20, 25), f"MOCK COMPOSITE #{i+1}", fill=(255, 255, 255))
            b = BytesIO()
            im.save(b, format="JPEG", quality=92)
            out.append(b.getvalue())
        return out

    def caption(self, brief: str, staged: bool) -> str:
        disclosure = " One or more photos are virtually staged." if staged else ""
        return (brief[:120] + " — #ForSale #RealEstate #Home" + disclosure).strip()
