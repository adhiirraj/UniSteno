# image_bitplane_superimposed.py
# Plugin to visualize superimposed RGB bitplanes
# Similar to Aperisolve-style analysis, useful for spotting LSB steganography

from PIL import Image      # Image loading and manipulation
import numpy as np         # Numerical array operations
import io                  # In-memory byte buffer
import base64              # Base64 encoding for frontend display

class ImageBitplaneSuperimposedPlugin:
    # Plugin identifier
    name = "image_bitplane_superimposed"

    def can_handle(self, mime, path):
        """
        Determine whether this plugin can analyze the given file.
        Supports all image MIME types.
        """
        return mime and mime.startswith("image/")

    def analyze(self, path):
        """
        Generate superimposed RGB bitplane images.
        For each bit position (0–7), combines R, G, B bits into a single image.
        """

        # Load image and force RGB mode
        im = Image.open(path).convert("RGB")

        # Convert image to NumPy array
        arr = np.array(im, dtype=np.uint8)

        # Dictionary to store base64-encoded bitplane images
        planes = {}

        # Iterate through all 8 bit positions
        for bit in range(8):
            # Bit mask for current bitplane
            mask = 1 << bit

            # Extract the selected bit from each RGB channel
            # Shift to LSB position and scale to visible range (0 or 255)
            rgb = np.stack(
                [
                    ((arr[:, :, c] & mask) >> bit) * 255
                    for c in range(3)
                ],
                axis=-1
            ).astype(np.uint8)

            # Convert array to RGB image
            img = Image.fromarray(rgb, mode="RGB")

            # Save image to memory buffer
            buf = io.BytesIO()
            img.save(buf, format="PNG")

            # Encode PNG bytes to base64 string
            planes[f"bit_{bit}"] = base64.b64encode(
                buf.getvalue()
            ).decode("ascii")

        # Return visualization results
        return {
            "description": "Superimposed RGB bitplanes (Aperisolve-style)",
            "planes": planes
        }
