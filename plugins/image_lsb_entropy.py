# image_lsb_entropy.py
# Plugin to analyze Least Significant Bit (LSB) entropy in image files
# Used to detect possible LSB-based steganography

from PIL import Image          # Image loading and processing
import numpy as np             # Numerical operations on pixel arrays
import math                    # Mathematical functions (logarithms)

class ImageLSBEntropyPlugin:
    # Plugin identifier (used by the UniSteno framework)
    name = "image_lsb_entropy"

    def can_handle(self, mime, path):
        """
        Check whether this plugin can process the given file.
        This plugin supports all image MIME types.
        """
        return mime and mime.startswith("image/")

    def _entropy(self, bits):
        """
        Compute Shannon entropy for a binary array (0s and 1s).

        bits: NumPy array containing only 0 or 1 values
        Returns entropy value in range [0, 1]
        """

        # Handle empty input safely
        if bits.size == 0:
            return 0.0

        # Probability of bit = 1
        p1 = np.mean(bits)

        # Probability of bit = 0
        p0 = 1.0 - p1

        # Small epsilon to avoid log(0)
        eps = 1e-12

        # Shannon entropy formula for binary distribution
        return -(
            p0 * math.log2(p0 + eps) +
            p1 * math.log2(p1 + eps)
        )

    def analyze(self, path):
        """
        Perform LSB entropy analysis on the given image file.

        path: filesystem path to the image
        Returns a dictionary with per-channel entropy results
        """

        # Open image and convert to RGB to ensure 3 color channels
        im = Image.open(path).convert("RGB")

        # Convert image to NumPy array of unsigned 8-bit integers
        arr = np.array(im, dtype=np.uint8)

        entropies = {}

        # Iterate over RGB channels
        for i, ch in enumerate(["R", "G", "B"]):
            # Extract Least Significant Bit of each pixel in the channel
            lsb = (arr[:, :, i] & 1).astype(np.uint8)

            # Compute entropy for this channel
            entropies[ch] = round(self._entropy(lsb), 4)

        # Compute average entropy across all three channels
        avg_entropy = round(sum(entropies.values()) / 3.0, 4)

        # Return structured analysis result
        return {
            "lsb_entropy": entropies,
            "average_entropy": avg_entropy,
            "notes": (
                "Entropy close to 1.0 indicates randomized LSBs, "
                "often caused by LSB steganography."
            )
        }
