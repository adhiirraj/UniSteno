# image_lsb_stego.py
import hashlib
import zlib
from pathlib import Path
from PIL import Image
import numpy as np

MAGIC = b"UNISTENO"


class ImageLSBStegoPlugin:
    name = "image_lsb_stego"

    def can_handle(self, mime, path):
        return mime and mime.startswith("image/")

    def _seed_from_password(self, password: str):
        if not password:
            return 0
        h = hashlib.sha256(password.encode("utf-8")).digest()
        return int.from_bytes(h[:8], byteorder="big", signed=False)

    # ================= EMBED =================
    def embed(self, infile, payload_bytes: bytes, password: str, outfile, payload_name: str = ""):
        im = Image.open(infile)
        has_alpha = "A" in im.mode
        work_mode = "RGBA" if has_alpha else "RGB"
        im = im.convert(work_mode)

        arr = np.array(im, dtype=np.uint8)
        rgb = arr[..., :3].ravel()

        if has_alpha:
            alpha = arr[..., 3].ravel()
            mask = np.repeat(alpha != 0, 3)
            available = np.nonzero(mask)[0].astype(np.int64)
        else:
            available = np.arange(rgb.size, dtype=np.int64)

        name_bytes = payload_name.encode("utf-8")
        blob = (
            MAGIC +
            len(name_bytes).to_bytes(4, "big") +
            name_bytes +
            len(payload_bytes).to_bytes(4, "big") +
            payload_bytes +
            (zlib.crc32(payload_bytes) & 0xffffffff).to_bytes(4, "big")
        )

        bits = np.unpackbits(np.frombuffer(blob, dtype=np.uint8)).astype(np.uint8)
        if bits.size > available.size:
            raise Exception("Payload too large for image capacity")

        rng = np.random.default_rng(self._seed_from_password(password))
        perm = rng.permutation(available.size)

        cursor = 0
        for bit in bits:
            idx = available[perm[cursor]]
            rgb[idx] = (rgb[idx] & 0xFE) | bit
            cursor += 1

        arr[..., :3] = rgb.reshape(arr[..., :3].shape)
        out_path = Path(outfile)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(arr, work_mode).save(out_path)

        return {
            "outfile": str(outfile),
            "payload_bytes": len(payload_bytes),
            "embedded_name": payload_name
        }

    # ================= EXTRACT =================
    def extract(self, infile, password: str):
        im = Image.open(infile)
        has_alpha = "A" in im.mode
        work_mode = "RGBA" if has_alpha else "RGB"
        im = im.convert(work_mode)

        arr = np.array(im, dtype=np.uint8)
        rgb = arr[..., :3].ravel()

        if has_alpha:
            alpha = arr[..., 3].ravel()
            mask = np.repeat(alpha != 0, 3)
            available = np.nonzero(mask)[0].astype(np.int64)
        else:
            available = np.arange(rgb.size, dtype=np.int64)

        rng = np.random.default_rng(self._seed_from_password(password))
        perm = rng.permutation(available.size)

        cursor = 0

        def read_bits(n):
            nonlocal cursor
            idx = available[perm[cursor:cursor + n]]
            cursor += n
            return (rgb[idx] & 1).astype(np.uint8)

        def read_bytes(n):
            return np.packbits(read_bits(n * 8)).tobytes()

        # --- MAGIC ---
        if read_bytes(len(MAGIC)) != MAGIC:
            raise Exception("No UniSteno payload detected (wrong password or clean image)")

        # --- filename ---
        name_len = int.from_bytes(read_bytes(4), "big")
        if name_len > 10 * 1024:
            raise Exception("Invalid filename length")
        name = read_bytes(name_len).decode("utf-8", errors="replace")

        # --- payload ---
        payload_len = int.from_bytes(read_bytes(4), "big")
        if payload_len > 200 * 1024 * 1024:
            raise Exception("Invalid payload length")
        payload = read_bytes(payload_len)

        # --- CRC ---
        crc_extracted = int.from_bytes(read_bytes(4), "big")
        if zlib.crc32(payload) & 0xffffffff != crc_extracted:
            raise Exception("CRC mismatch (wrong password or corrupted image)")

        return {
            "name": name or "extracted.bin",
            "payload": payload
        }
