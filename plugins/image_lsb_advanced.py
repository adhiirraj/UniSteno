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

        for ch in ["R", "G", "B"]:
            lsb_ratio = lsb_counts[ch] / total
            bit1_ratio = bitplane_hist[ch][1] / total
            randomness_jump = abs(lsb_ratio - bit1_ratio)
            NATURAL_R_JUMP = 0.015
            NATURAL_CHI_LOG = 5.5
            r_norm = min(abs(randomness_jump - NATURAL_R_JUMP) / NATURAL_R_JUMP, 1.0)

            chi_val = chi_sq[ch]
            chi_log = np.log10(chi_val + 1)
            chi_norm = min(abs(chi_log - NATURAL_CHI_LOG) / NATURAL_CHI_LOG, 1.0)

            score += 0.6 * r_norm + 0.4 * chi_norm

        score /= 3.0
        score = round(score, 4)

        return {
            "width": w, "height": h,
            "lsb_counts": lsb_counts,
            "chi_square": chi_sq,
            "bitplane_hist": bitplane_hist,
            "suspiciousness_score": round(score, 5),
            "notes": "Lower score ≈ closer to natural (50/50) distribution; higher may indicate LSB stego"
        }