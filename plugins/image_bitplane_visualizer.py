# image_bitplane_visualizer.py
# Plugin to visualize individual bitplanes of an image
# Useful for detecting LSB steganography and hidden visual patterns

from PIL import Image      # Image loading and manipulation
import numpy as np         # Numerical operations on pixel data
import io                  # In-memory byte buffers
import base64              # Base64 encoding for frontend transport

class ImageBitplaneVisualizerPlugin:
    # Plugin identifier
    name = "image_bitplane_visualizer"

    def can_handle(self, mime, path):
        """
        Determine whether this plugin can analyze the given file.
        Supports all image MIME types.
        """
        return mime and mime.startswith("image/")

    def analyze(self, path, options=None):
        options = options or {}

        """
        Extract and visualize all 8 bitplanes for each RGB channel.
        Each bitplane is returned as a base64-encoded PNG image.
        """

        # Load image and ensure RGB format
        with Image.open(path) as im:
            im = im.convert("RGB")
            arr = np.array(im, dtype=np.uint8)

        # Image dimensions
        h, w, _ = arr.shape

        # Storage for bitplanes
        planes = {
            "R": {},
            "G": {},
            "B": {}
        }

        # Iterate over RGB channels
        for idx, ch in enumerate(["R", "G", "B"]):
            channel = arr[:, :, idx]

            # Extract each of the 8 bitplanes
            for bit in range(0, 8):
                # Isolate bitplane and scale to visible range (0 or 255)
                plane = ((channel >> bit) & 1) * 255

                # Convert to 1-bit black/white image
                img = (
                    Image.fromarray(plane.astype(np.uint8), mode="L")
                    .convert("1")
                )

                # Encode image as PNG in memory
                buf = io.BytesIO()
                img.save(buf, format="PNG")

                # Convert PNG bytes to base64 string
                b64 = base64.b64encode(buf.getvalue()).decode("ascii")

                # Store encoded image
                planes[ch][f"bit_{bit}"] = b64

        # Return visualization data
        return {
            "description": "Bitplane visualization (bit_0 = LSB, bit_7 = MSB)",
            "width": w,
            "height": h,
            "planes": planes
        }
