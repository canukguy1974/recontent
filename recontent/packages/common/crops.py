from PIL import Image, ImageOps
from io import BytesIO

SIZES = [(1080, 1080), (1080, 1350), (1080, 1920)]

def social_crops(img_bytes: bytes) -> list[bytes]:
    im = Image.open(BytesIO(img_bytes)).convert("RGB")
    outs = []
    for w, h in SIZES:
        c = ImageOps.fit(im, (w, h), method=Image.Resampling.LANCZOS)
        b = BytesIO()
        c.save(b, format="JPEG", quality=92)
        outs.append(b.getvalue())
    return outs
