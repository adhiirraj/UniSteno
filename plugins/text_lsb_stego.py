# text_lsb_stego.py
# Zero-width Unicode text steganography with optional AES encryption

import base64
from pathlib import Path

try:
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes
    from Crypto.Protocol.KDF import PBKDF2
except Exception:
    AES = None


ZW0 = "\u200B"  # bit 0
ZW1 = "\u200C"  # bit 1
ZWS = "\u200D"  # separator


class TextLSBStegoPlugin:
    name = "text_lsb_stego"

    def can_handle(self, mime, path):
        return mime.startswith("text/")

    # ---------------- CRYPTO ----------------

    def _encrypt(self, data: bytes, password: str) -> bytes:
        salt = get_random_bytes(16)
        key = PBKDF2(password, salt, dkLen=32, count=100_000)
        cipher = AES.new(key, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(data)
        return salt + cipher.nonce + tag + ciphertext

    def _decrypt(self, data: bytes, password: str) -> bytes:
        salt = data[:16]
        nonce = data[16:32]
        tag = data[32:48]
        ciphertext = data[48:]
        key = PBKDF2(password, salt, dkLen=32, count=100_000)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag)

    # ---------------- BIT UTILS ----------------

    def _to_bits(self, data: bytes) -> str:
        return "".join(f"{b:08b}" for b in data)

    def _from_bits(self, bits: str) -> bytes:
        return bytes(int(bits[i:i+8], 2) for i in range(0, len(bits), 8))

    # ---------------- EMBED ----------------

    def embed(self, infile: Path, payload: bytes, password: str,
              outfile: Path, payload_name: str):

        text = infile.read_text(encoding="utf-8", errors="replace")

        header = f"{payload_name}\0".encode()
        data = header + payload

        if password:
            if AES is None:
                raise Exception("PyCryptodome not installed")
            data = self._encrypt(data, password)

        b64 = base64.b64encode(data)
        bits = self._to_bits(b64)

        zw_stream = []
        for bit in bits:
            zw_stream.append(ZW1 if bit == "1" else ZW0)
        zw_stream.append(ZWS)

        stego_text = text + "".join(zw_stream)
        outfile.write_text(stego_text, encoding="utf-8")

        return {
            "method": "zero-width-unicode",
            "encrypted": bool(password),
            "payload_bytes": len(payload),
            "output": outfile.name
        }

    # ---------------- EXTRACT ----------------

    def extract(self, infile: Path, password: str):
        text = infile.read_text(encoding="utf-8", errors="replace")

        zw_chars = [c for c in text if c in (ZW0, ZW1, ZWS)]
        if ZWS not in zw_chars:
            return {"error": "no hidden payload found"}

        bits = ""
        for c in zw_chars:
            if c == ZWS:
                break
            bits += "1" if c == ZW1 else "0"

        data = base64.b64decode(self._from_bits(bits))

        if password:
            if AES is None:
                raise Exception("PyCryptodome not installed")
            data = self._decrypt(data, password)

        name, payload = data.split(b"\0", 1)

        return {
            "name": name.decode(errors="replace"),
            "payload": payload
        }
