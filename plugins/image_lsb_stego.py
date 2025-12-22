# image_lsb_stego.py
import hashlib
import zlib
from pathlib import Path
from PIL import Image
import numpy as np

MAGIC = b"UNISTENO"  # magic header to identify UniSteno payloads


class ImageLSBStegoPlugin:
    name = "image_lsb_stego"

    def can_handle(self, mime, path):
        return mime and mime.startswith("image/")

    def _seed_from_password(self, password: str):
        if not password:
            return 0
        h = hashlib.sha256(password.encode("utf-8")).digest()
        return int.from_bytes(h[:8], byteorder="big", signed=False)

    # ---------------- EMBED ----------------
    def embed(self, infile, payload_bytes: bytes, password: str, outfile, payload_name: str = ""):
        im = Image.open(infile)
        has_alpha = 'A' in im.mode
        work_mode = 'RGBA' if has_alpha else 'RGB'
        im = im.convert(work_mode)

        arr = np.array(im, dtype=np.uint8)

        # Only modify RGB channels
        target = arr[..., :3]
        flat = target.ravel()

        # Skip fully transparent pixels if alpha exists
        if has_alpha:
            alpha = arr[..., 3].ravel()
            pixel_mask = (alpha != 0)
            byte_mask = np.repeat(pixel_mask, 3)
            available_positions = np.nonzero(byte_mask)[0].astype(np.int64)
        else:
            available_positions = np.arange(flat.size, dtype=np.int64)

        capacity_bits = available_positions.size

        name_bytes = (payload_name or "").encode("utf-8")
        name_len_b = len(name_bytes).to_bytes(4, "big")
        payload_len_b = len(payload_bytes).to_bytes(4, "big")
        crc_b = (zlib.crc32(payload_bytes) & 0xffffffff).to_bytes(4, "big")

        blob = MAGIC + name_len_b + name_bytes + payload_len_b + payload_bytes + crc_b
        bits = np.unpackbits(np.frombuffer(blob, dtype=np.uint8)).astype(np.uint8)

        if bits.size > capacity_bits:
            raise Exception("Payload too large for image capacity")

        rng = np.random.default_rng(self._seed_from_password(password))
        chosen = available_positions[rng.permutation(capacity_bits)[:bits.size]]

        flat[chosen] = (flat[chosen] & np.uint8(0xFE)) | bits

        arr[..., :3] = flat.reshape(target.shape)
        out_path = Path(outfile)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(arr, work_mode).save(out_path)

        return {
            "outfile": str(outfile),
            "payload_bytes": len(payload_bytes),
            "embedded_name": payload_name
        }

    # ---------------- EXTRACT ----------------
    def extract(self, infile, password: str):
        im = Image.open(infile)
        has_alpha = 'A' in im.mode
        work_mode = 'RGBA' if has_alpha else 'RGB'
        im = im.convert(work_mode)
        arr = np.array(im, dtype=np.uint8)

        flat = arr[..., :3].ravel()

        if has_alpha:
            alpha = arr[..., 3].ravel()
            byte_mask = np.repeat(alpha != 0, 3)
            available_positions = np.nonzero(byte_mask)[0].astype(np.int64)
        else:
            available_positions = np.arange(flat.size, dtype=np.int64)

        rng = np.random.default_rng(self._seed_from_password(password))
        perm = rng.permutation(available_positions.size)

        def read_bytes(nbytes, offset_bits):
            bit_indices = perm[offset_bits : offset_bits + nbytes * 8]
            byte_positions = available_positions[bit_indices]
            bits = (flat[byte_positions] & 1).astype(np.uint8)
            return np.packbits(bits).tobytes()

        offset = 0

        # --- MAGIC CHECK ---
        magic = read_bytes(len(MAGIC), offset)
        if magic != MAGIC:
            raise Exception("No UniSteno payload detected (wrong password or clean image)")
        offset += len(MAGIC) * 8

        # --- filename length ---
        name_len = int.from_bytes(read_bytes(4, offset), "big")
        if name_len < 0 or name_len > 10 * 1024:
            raise Exception("Invalid filename length")
        offset += 32

        # --- filename ---
        name = read_bytes(name_len, offset).decode("utf-8", errors="replace")
        offset += name_len * 8

        # --- payload length ---
        payload_len = int.from_bytes(read_bytes(4, offset), "big")
        if payload_len < 0 or payload_len > 200 * 1024 * 1024:
            raise Exception("Invalid payload length")
        offset += 32

        # --- payload ---
        payload = read_bytes(payload_len, offset)
        offset += payload_len * 8

        # --- crc ---
        crc_extracted = int.from_bytes(read_bytes(4, offset), "big")
        if zlib.crc32(payload) & 0xffffffff != crc_extracted:
            raise Exception("CRC mismatch (wrong password or corrupted image)")

        return {
            "name": name or "extracted.bin",
            "payload": payload
        }
