from PIL import Image
import numpy as np
import io
import base64

class ImageBitplaneSuperimposedPlugin:
    name = "image_bitplane_superimposed"

    def can_handle(self, mime, path):
        return mime and mime.startswith("image/")

    def analyze(self, path):
        with Image.open(path) as im:
            im = im.convert("RGB")
            arr = np.array(im, dtype=np.uint8)

        planes = {}

        for bit in range(8):
            mask = 1 << bit
            rgb = np.stack(
                [((arr[..., c] & mask) >> bit) * 255 for c in range(3)],
                axis=-1
            ).astype(np.uint8)

            img = Image.fromarray(rgb, mode="RGB")
            buf = io.BytesIO()
            img.save(buf, format="PNG")

            planes[f"bit_{bit}"] = base64.b64encode(buf.getvalue()).decode("ascii")

        return {
            "description": "Superimposed RGB bitplanes (Aperisolve-style)",
            "planes": planes,
            "width": arr.shape[1],
            "height": arr.shape[0]
        }
