# audio_lsb_stego.py
# Encrypted / non-encrypted LSB audio steganography (WAV)
# Preserves filename + extension

import hashlib
import struct
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad


class AudioLSBStegoPlugin:
    name = "audio_lsb_stego"

    def can_handle(self, mime, path):
        return mime == "audio/wav" or str(path).lower().endswith(".wav")

    # ---------- CRYPTO ----------

    def _derive_key(self, password: str) -> bytes:
        return hashlib.sha256(password.encode("utf-8")).digest()

    def _encrypt(self, data: bytes, password: str) -> bytes:
        key = self._derive_key(password)
        iv = get_random_bytes(16)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return iv + cipher.encrypt(pad(data, AES.block_size))

    def _decrypt(self, data: bytes, password: str) -> bytes:
        key = self._derive_key(password)
        iv = data[:16]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return unpad(cipher.decrypt(data[16:]), AES.block_size)

    # ---------- EMBED ----------

    def embed(self, infile: Path, payload: bytes, password: str,
              outfile: Path, payload_name: str):

        sr, samples = wavfile.read(infile)

        if samples.dtype != np.int16:
            raise ValueError("Only 16-bit PCM WAV supported")

        flat = samples.flatten()

        # ---- filename ----
        name_bytes = payload_name.encode("utf-8")
        name_len = len(name_bytes)

        # ---- payload ----
        if password:
            payload_bytes = self._encrypt(payload, password)
            encrypted = True
        else:
            payload_bytes = payload
            encrypted = False

        payload_len = len(payload_bytes)

        header = (
            struct.pack(">I", name_len) +
            name_bytes +
            struct.pack(">I", payload_len)
        )

        full_data = header + payload_bytes
        bitstream = np.unpackbits(
            np.frombuffer(full_data, dtype=np.uint8)
        )

        if len(bitstream) > len(flat):
            raise ValueError("Payload too large for this audio file")

        stego = flat.copy()
        stego[:len(bitstream)] &= ~1
        stego[:len(bitstream)] |= bitstream

        wavfile.write(outfile, sr, stego.reshape(samples.shape))

        return {
            "embedded_bytes": len(payload),
            "encrypted": encrypted,
            "capacity_bits": len(flat),
            "used_bits": len(bitstream)
        }

    # ---------- EXTRACT ----------

    def extract(self, infile: Path, password: str):
        sr, samples = wavfile.read(infile)
        flat = samples.flatten()

        # ---- filename length ----
        name_len_bits = flat[:32] & 1
        name_len = struct.unpack(">I", np.packbits(name_len_bits))[0]

        # ---- filename ----
        name_bits = flat[32:32 + name_len * 8] & 1
        name = np.packbits(name_bits).tobytes().decode("utf-8")

        # ---- payload length ----
        offset = 32 + name_len * 8
        payload_len_bits = flat[offset:offset + 32] & 1
        payload_len = struct.unpack(">I", np.packbits(payload_len_bits))[0]

        # ---- payload ----
        payload_start = offset + 32
        payload_bits = flat[payload_start:payload_start + payload_len * 8] & 1
        payload_data = np.packbits(payload_bits).tobytes()

        if password:
            payload_data = self._decrypt(payload_data, password)

        return {
            "payload": payload_data,
            "name": name
        }
