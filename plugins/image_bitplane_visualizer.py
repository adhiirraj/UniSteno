# image_bitplane_visualizer.py
from PIL import Image
import numpy as np
import io
import base64

class ImageBitplaneVisualizerPlugin:
    name = "image_bitplane_visualizer"

    def can_handle(self, mime, path):
        return mime and mime.startswith("image/")

    def analyze(self, path):
        with Image.open(path) as im:
            im = im.convert("RGB")
            arr = np.array(im, dtype=np.uint8)

        h, w, _ = arr.shape
        planes = {"R": {}, "G": {}, "B": {}}

        for idx, ch in enumerate(["R", "G", "B"]):
            channel = arr[:, :, idx]
            for bit in range(0, 8):
                plane = ((channel >> bit) & 1) * 255
                img = Image.fromarray(plane.astype(np.uint8), mode="L").convert("1")

                buf = io.BytesIO()
                img.save(buf, format="PNG")
                b64 = base64.b64encode(buf.getvalue()).decode("ascii")

                planes[ch][f"bit_{bit}"] = b64

        return {
            "description": "Bitplane visualization (bit_0 = LSB, bit_7 = MSB)",
            "width": w,
            "height": h,
            "planes": planes
        }
