# image_lsb_stego.py
# Image-based LSB steganography plugin for UniSteno
# Supports password-based pseudo-random embedding and extraction
# Includes filename preservation and CRC integrity verification

import hashlib
import zlib
from pathlib import Path
from PIL import Image
import numpy as np

# Magic header used to identify UniSteno-embedded payloads
MAGIC = b"UNISTENO"


class ImageLSBStegoPlugin:
    # Plugin identifier
    name = "image_lsb_stego"

    def can_handle(self, mime, path):
        """
        Determine whether this plugin can process the file.
        Supports all image MIME types.
        """
        return mime and mime.startswith("image/")

    def _seed_from_password(self, password: str):
        """
        Convert password into a deterministic RNG seed.
        SHA-256 ensures consistent permutation across embed/extract.
        """
        if not password:
            return 0
        h = hashlib.sha256(password.encode("utf-8")).digest()
        return int.from_bytes(h[:8], byteorder="big", signed=False)

    # ============================ EMBED ============================

    def embed(self, infile, payload_bytes: bytes, password: str,
              outfile, payload_name: str = ""):
        """
        Embed payload into image using LSB substitution.
        - RGB channels only
        - Skips fully transparent pixels
        - Uses password-seeded random bit positions
        """

        # Load image
        im = Image.open(infile)

        # Preserve alpha channel if present
        has_alpha = 'A' in im.mode
        work_mode = 'RGBA' if has_alpha else 'RGB'
        im = im.convert(work_mode)

        # Convert image to NumPy array
        arr = np.array(im, dtype=np.uint8)

        # Work only on RGB channels
        target = arr[..., :3]
        flat = target.ravel()

        # Determine usable pixel positions
        if has_alpha:
            # Skip fully transparent pixels
            alpha = arr[..., 3].ravel()
            pixel_mask = (alpha != 0)
            byte_mask = np.repeat(pixel_mask, 3)
            available_positions = np.nonzero(byte_mask)[0].astype(np.int64)
        else:
            available_positions = np.arange(flat.size, dtype=np.int64)

        capacity_bits = available_positions.size

        # ================= PAYLOAD FORMAT =================
        # MAGIC | name_len | name | payload_len | payload | CRC32

        name_bytes = (payload_name or "").encode("utf-8")
        name_len_b = len(name_bytes).to_bytes(4, "big")
        payload_len_b = len(payload_bytes).to_bytes(4, "big")
        crc_b = (zlib.crc32(payload_bytes) & 0xffffffff).to_bytes(4, "big")

        blob = (
            MAGIC +
            name_len_b +
            name_bytes +
            payload_len_b +
            payload_bytes +
            crc_b
        )

        # Convert payload blob into individual bits
        bits = np.unpackbits(
            np.frombuffer(blob, dtype=np.uint8)
        ).astype(np.uint8)

        # Capacity check
        if bits.size > capacity_bits:
            raise Exception("Payload too large for image capacity")

        # Pseudo-random placement using password-derived seed
        rng = np.random.default_rng(self._seed_from_password(password))
        chosen = available_positions[
            rng.permutation(capacity_bits)[:bits.size]
        ]

        # Embed bits into LSBs
        flat[chosen] = (flat[chosen] & np.uint8(0xFE)) | bits

        # Restore modified RGB data
        arr[..., :3] = flat.reshape(target.shape)

        # Save output image
        out_path = Path(outfile)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(arr, work_mode).save(out_path)

        return {
            "outfile": str(outfile),
            "payload_bytes": len(payload_bytes),
            "embedded_name": payload_name
        }

    # ============================ EXTRACT ============================

    def extract(self, infile, password: str):
        """
        Extract embedded payload from image.
        Uses same password-seeded RNG to recover bit positions.
        """

        # Load image
        im = Image.open(infile)
        has_alpha = 'A' in im.mode
        work_mode = 'RGBA' if has_alpha else 'RGB'
        im = im.convert(work_mode)

        arr = np.array(im, dtype=np.uint8)
        flat = arr[..., :3].ravel()

        # Identify usable byte positions
        if has_alpha:
            alpha = arr[..., 3].ravel()
            byte_mask = np.repeat(alpha != 0, 3)
            available_positions = np.nonzero(byte_mask)[0].astype(np.int64)
        else:
            available_positions = np.arange(flat.size, dtype=np.int64)

        # Recreate permutation using same password
        rng = np.random.default_rng(self._seed_from_password(password))
        perm = rng.permutation(available_positions.size)

        def read_bytes(nbytes, offset_bits):
            """
            Read nbytes from LSB stream starting at bit offset.
            """
            bit_indices = perm[offset_bits: offset_bits + nbytes * 8]
            byte_positions = available_positions[bit_indices]
            bits = (flat[byte_positions] & 1).astype(np.uint8)
            return np.packbits(bits).tobytes()

        offset = 0

        # ---------------- MAGIC CHECK ----------------
        magic = read_bytes(len(MAGIC), offset)
        if magic != MAGIC:
            raise Exception(
                "No UniSteno payload detected (wrong password or clean image)"
            )
        offset += len(MAGIC) * 8

        # ---------------- FILENAME LENGTH ----------------
        name_len = int.from_bytes(read_bytes(4, offset), "big")
        if name_len < 0 or name_len > 10 * 1024:
            raise Exception("Invalid filename length")
        offset += 32

        # ---------------- FILENAME ----------------
        name = read_bytes(name_len, offset).decode(
            "utf-8", errors="replace"
        )
        offset += name_len * 8

        # ---------------- PAYLOAD LENGTH ----------------
        payload_len = int.from_bytes(read_bytes(4, offset), "big")
        if payload_len < 0 or payload_len > 200 * 1024 * 1024:
            raise Exception("Invalid payload length")
        offset += 32

        # ---------------- PAYLOAD ----------------
        payload = read_bytes(payload_len, offset)
        offset += payload_len * 8

        # ---------------- CRC CHECK ----------------
        crc_extracted = int.from_bytes(read_bytes(4, offset), "big")
        if zlib.crc32(payload) & 0xffffffff != crc_extracted:
            raise Exception(
                "CRC mismatch (wrong password or corrupted image)"
            )

        return {
            "name": name or "extracted.bin",
            "payload": payload
        }
