# plugins/image_lsb_entropy.py
from PIL import Image
import numpy as np
import math

class ImageLSBEntropyPlugin:
    name = "image_lsb_entropy"

    def can_handle(self, mime, path):
        return mime and mime.startswith("image/")

    def _entropy(self, bits):
        # bits: array of 0/1 values
        if bits.size == 0:
            return 0.0
        p1 = np.mean(bits)
        p0 = 1.0 - p1
        eps = 1e-12
        return -(
            p0 * math.log2(p0 + eps) +
            p1 * math.log2(p1 + eps)
        )

    def analyze(self, path):
        im = Image.open(path).convert("RGB")
        arr = np.array(im, dtype=np.uint8)

        entropies = {}
        for i, ch in enumerate(["R", "G", "B"]):
            lsb = (arr[:, :, i] & 1).astype(np.uint8)
            entropies[ch] = round(self._entropy(lsb), 4)

        avg_entropy = round(sum(entropies.values()) / 3.0, 4)

        return {
            "lsb_entropy": entropies,
            "average_entropy": avg_entropy,
            "notes": (
                "Entropy close to 1.0 indicates randomized LSBs, "
                "often caused by LSB steganography."
            )
        }
