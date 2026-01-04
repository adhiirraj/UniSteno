# image_lsb_advanced.py
# Advanced LSB steganalysis plugin for images
# Uses Chi-square testing and inter-bitplane statistical comparison
# Produces a normalized "suspiciousness score"

from PIL import Image          # Image loading and conversion
import numpy as np             # Fast numerical array operations
import math                    # Mathematical functions

class ImageLSBAdvancedPlugin:
    # Plugin identifier used by UniSteno backend
    name = "image_lsb_advanced"

    def can_handle(self, mime, path):
        """
        Determine whether this plugin can process the file.
        Supports all image MIME types.
        """
        return mime and mime.startswith("image/")

    def _chi_square(self, ones, total):
        """
        Perform chi-square test for binary distribution.
        Tests deviation from expected 50/50 distribution.

        ones  : number of 1s in LSB plane
        total : total number of pixels

        Returns chi-square statistic
        """
        exp = total / 2.0
        return (
            ((ones - exp) ** 2) / exp +
            (((total - ones) - exp) ** 2) / exp
        )

    def analyze(self, path, options=None):
        options = options or {}

        """
        Perform advanced LSB steganalysis:
        - LSB bit count
        - Chi-square randomness test
        - Inter-bitplane statistical comparison
        - Suspiciousness score estimation
        """

        # Load image and force RGB format
        im = Image.open(path).convert("RGB")

        # Convert image to NumPy array
        arr = np.array(im, dtype=np.uint8)
        h, w, c = arr.shape

        # Total number of pixels per channel
        total = h * w

        # Storage structures
        lsb_counts = {}       # Count of LSB = 1
        chi_sq = {}           # Chi-square values per channel
        bitplane_hist = {ch: {b: 0 for b in range(8)} for ch in ["R","G","B"]}

        # Analyze each color channel independently
        for i, ch in enumerate(["R","G","B"]):
            channel = arr[:, :, i]

            # Count LSB = 1
            ones = int(np.count_nonzero(channel & 1))
            lsb_counts[ch] = ones

            # Chi-square test for LSB randomness
            chi_sq[ch] = round(self._chi_square(ones, total), 4)

            # Histogram of all 8 bitplanes
            for b in range(8):
                bitplane_hist[ch][b] = int(
                    np.count_nonzero((channel >> b) & 1)
                )

        # ================= SUSPICIOUSNESS SCORING =================

        score = 0.0

        for ch in ["R", "G", "B"]:
            # Ratio of 1s in LSB and next bitplane
            lsb_ratio = lsb_counts[ch] / total
            bit1_ratio = bitplane_hist[ch][1] / total

            # Natural images show correlation between adjacent bitplanes
            randomness_jump = abs(lsb_ratio - bit1_ratio)

            # Empirical constants derived from natural images
            NATURAL_R_JUMP = 0.015
            NATURAL_CHI_LOG = 5.5

            # Normalize deviation of bitplane jump
            r_norm = min(
                abs(randomness_jump - NATURAL_R_JUMP) / NATURAL_R_JUMP,
                1.0
            )

            # Normalize chi-square deviation using logarithmic scale
            chi_val = chi_sq[ch]
            chi_log = np.log10(chi_val + 1)
            chi_norm = min(
                abs(chi_log - NATURAL_CHI_LOG) / NATURAL_CHI_LOG,
                1.0
            )

            # Weighted contribution per channel
            score += 0.6 * r_norm + 0.4 * chi_norm

        # Average across RGB channels
        score /= 3.0
        score = round(score, 4)

        # ================= RESULT =================

        return {
            "width": w,
            "height": h,
            "lsb_counts": lsb_counts,
            "chi_square": chi_sq,
            "bitplane_hist": bitplane_hist,
            "suspiciousness_score": round(score, 5),
            "notes": (
                "Lower score ≈ closer to natural (50/50) distribution; "
                "higher may indicate LSB steganography"
            )
        }
