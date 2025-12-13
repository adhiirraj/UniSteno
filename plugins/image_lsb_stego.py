# plugins/image_lsb_stego.py
import hashlib
import zlib
from pathlib import Path
from PIL import Image
import numpy as np

class ImageLSBStegoPlugin:
    name = "image_lsb_stego"

    def can_handle(self, mime, path):
        return mime and mime.startswith("image/")

    def _seed_from_password(self, password: str):
        if not password:
            return 0
        h = hashlib.sha256(password.encode("utf-8")).digest()
        return int.from_bytes(h[:8], byteorder="big", signed=False)

    def embed(self, infile, payload_bytes: bytes, password: str, outfile, payload_name: str = ""):
        """
        Embed layout stored in this order:
         - 4 bytes: filename length (N)
         - N bytes: filename (utf-8)
         - 4 bytes: payload length (L)
         - L bytes: payload
         - 4 bytes: crc32(payload) (for integrity)
        """
        im = Image.open(infile)
        has_alpha = 'A' in im.mode
        work_mode = 'RGBA' if has_alpha else 'RGB'
        im = im.convert(work_mode)

        arr = np.array(im, dtype=np.uint8)
        channels_to_modify = 3
        target = arr[..., :channels_to_modify]

        flat = target.ravel()

        # available positions (skip fully transparent pixels if present)
        if has_alpha:
            alpha = arr[..., 3].ravel()
            pixel_mask = (alpha != 0)
            byte_mask = np.repeat(pixel_mask, 3)
            available_positions = np.nonzero(byte_mask)[0].astype(np.int64)
        else:
            available_positions = np.arange(flat.size, dtype=np.int64)

        capacity_bits = available_positions.size

        # prepare header + payload
        name_bytes = (payload_name or "").encode("utf-8")
        name_len = len(name_bytes)
        name_len_b = name_len.to_bytes(4, byteorder='big')

        payload_len = len(payload_bytes)
        payload_len_b = payload_len.to_bytes(4, byteorder='big')

        crc = zlib.crc32(payload_bytes) & 0xffffffff
        crc_b = crc.to_bytes(4, byteorder='big')

        full = name_len_b + name_bytes + payload_len_b + payload_bytes + crc_b

        bits = np.unpackbits(np.frombuffer(full, dtype=np.uint8)).astype(np.uint8)
        nbits = bits.size

        if nbits > capacity_bits:
            raise Exception(f"Payload too large: requires {nbits} bits but available capacity is {capacity_bits} bits (transparent pixels skipped)")

        seed = self._seed_from_password(password)
        rng = np.random.default_rng(seed)
        perm = rng.permutation(capacity_bits).astype(np.int64)
        chosen_idx = perm[:nbits]
        chosen = available_positions[chosen_idx]

        # safe uint8 ops
        src_vals = flat[chosen].astype(np.uint8)
        mask = np.uint8(0xFE)
        cleared = np.bitwise_and(src_vals, mask)
        bits_uint8 = bits.astype(np.uint8)
        new_vals = np.bitwise_or(cleared, bits_uint8)

        flat[chosen] = new_vals

        arr_mod = arr.copy()
        arr_mod[..., :channels_to_modify] = flat.reshape(target.shape)

        out_im = Image.fromarray(arr_mod, mode=work_mode)
        out_path = Path(outfile)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_im.save(out_path)

        return {"outfile": str(outfile), "payload_bytes": payload_len, "bits_written": int(nbits), "embedded_name": payload_name}

    def extract(self, infile, password: str):
        """
        Reverse of embed: read name_len, name, payload_len, payload, crc
        """
        im = Image.open(infile)
        has_alpha = 'A' in im.mode
        work_mode = 'RGBA' if has_alpha else 'RGB'
        im = im.convert(work_mode)
        arr = np.array(im, dtype=np.uint8)

        target = arr[..., :3]
        flat = target.ravel()

        if has_alpha:
            alpha = arr[..., 3].ravel()
            pixel_mask = (alpha != 0)
            byte_mask = np.repeat(pixel_mask, 3)
            available_positions = np.nonzero(byte_mask)[0].astype(np.int64)
        else:
            available_positions = np.arange(flat.size, dtype=np.int64)

        capacity_bits = available_positions.size

        seed = self._seed_from_password(password)
        rng = np.random.default_rng(seed)
        perm = rng.permutation(capacity_bits).astype(np.int64)

        # read name length (32 bits)
        name_len_idx = perm[:32]
        name_len_pos = available_positions[name_len_idx]
        name_len_bits = (flat[name_len_pos] & np.uint8(1)).astype(np.uint8)
        name_len_bytes = np.packbits(name_len_bits).tobytes()
        name_len = int.from_bytes(name_len_bytes, byteorder='big')

        if name_len < 0 or name_len > (10 * 1024):  # sanity cap: filename <= 10KB
            raise Exception(f"Unreasonable filename length extracted: {name_len}")

        # read filename bits
        name_bits_start = 32
        name_bits_len = name_len * 8
        name_idx = perm[name_bits_start:name_bits_start + name_bits_len]
        name_pos = available_positions[name_idx]
        name_bits = (flat[name_pos] & np.uint8(1)).astype(np.uint8)
        name_bytes = np.packbits(name_bits).tobytes()
        extracted_name = name_bytes.decode('utf-8', errors='replace')

        # read payload length (next 32 bits)
        payload_len_idx_start = name_bits_start + name_bits_len
        payload_len_idx = perm[payload_len_idx_start:payload_len_idx_start + 32]
        payload_len_pos = available_positions[payload_len_idx]
        payload_len_bits = (flat[payload_len_pos] & np.uint8(1)).astype(np.uint8)
        payload_len_bytes = np.packbits(payload_len_bits).tobytes()
        payload_len = int.from_bytes(payload_len_bytes, byteorder='big')

        if payload_len < 0 or payload_len > (200 * 1024 * 1024):
            raise Exception(f"Unreasonable payload length extracted: {payload_len}")

        # read payload and crc
        payload_bits_start = payload_len_idx_start + 32
        payload_bits_len = payload_len * 8
        crc_bits_start = payload_bits_start + payload_bits_len
        crc_bits_len = 32
        total_bits_needed = crc_bits_start + crc_bits_len

        if total_bits_needed > capacity_bits:
            raise Exception(f"Embedded length claims {total_bits_needed} bits but available capacity {capacity_bits} bits")

        payload_idx = perm[payload_bits_start:payload_bits_start + payload_bits_len]
        payload_pos = available_positions[payload_idx]
        payload_bits = (flat[payload_pos] & np.uint8(1)).astype(np.uint8)
        payload_bytes = np.packbits(payload_bits).tobytes()

        crc_idx = perm[crc_bits_start:crc_bits_start + crc_bits_len]
        crc_pos = available_positions[crc_idx]
        crc_bits = (flat[crc_pos] & np.uint8(1)).astype(np.uint8)
        crc_bytes = np.packbits(crc_bits).tobytes()
        crc_extracted = int.from_bytes(crc_bytes, byteorder='big')

        crc_actual = zlib.crc32(payload_bytes) & 0xffffffff
        if crc_extracted != crc_actual:
            raise Exception("CRC mismatch: data integrity check failed (wrong password or corrupted image)")

        return {"name": extracted_name or "extracted.bin", "payload": payload_bytes}
