#image_lsb_advanced.py
from PIL import Image
import numpy as np
import math

class ImageLSBAdvancedPlugin:
    name = "image_lsb_advanced"

    def can_handle(self, mime, path):
        return mime and mime.startswith("image/")

    def _chi_square(self, ones, total):
        exp = total / 2.0
        return ((ones - exp)**2 / exp) + (((total - ones) - exp)**2 / exp)

    def analyze(self, path):
        im = Image.open(path).convert("RGB")
        arr = np.array(im, dtype=np.uint8)
        h, w, c = arr.shape
        total = h * w

        lsb_counts = {}
        chi_sq = {}
        bitplane_hist = {ch: {b: 0 for b in range(8)} for ch in ["R","G","B"]}

        for i, ch in enumerate(["R","G","B"]):
            channel = arr[:,:,i]
            ones = int(np.count_nonzero(channel & 1))
            lsb_counts[ch] = ones
            chi_sq[ch] = round(self._chi_square(ones, total), 4)
            for b in range(8):
                bitplane_hist[ch][b] = int(np.count_nonzero((channel >> b) & 1))

        score = 0.0
        for ch in ["R","G","B"]:
            dev = abs(lsb_counts[ch] - (total/2)) / (total/2)
            score += dev + (chi_sq[ch] / 10.0)

        return {
            "width": w, "height": h,
            "lsb_counts": lsb_counts,
            "chi_square": chi_sq,
            "bitplane_hist": bitplane_hist,
            "suspiciousness_score": round(score, 5),
            "notes": "Lower score ≈ closer to natural (50/50) distribution; higher may indicate LSB stego"
        }
