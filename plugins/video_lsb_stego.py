# video_lsb_stego.py
# First-frame video steganography with filename preservation (BLUE CHANNEL ONLY)

import cv2
import numpy as np
import struct
import zlib
from pathlib import Path
from hashlib import sha256


class VideoLSBStegoPlugin:
    name = "video_lsb_stego"

    FNAME_LEN_FMT = ">H"   # uint16
    PAYLOAD_LEN_FMT = ">I"
    CRC_FMT = ">I"

    def can_handle(self, mime, path):
        return mime and mime.startswith("video/")

    def _rng(self, password):
        seed = int.from_bytes(
            sha256(password.encode()).digest()[:8], "big"
        )
        return np.random.default_rng(seed)

    # ================= EMBED =================
    def embed(self, infile, payload, password, outfile, payload_name=None):
        infile = Path(infile)
        outfile = outfile.with_suffix(".avi")

        if not payload_name:
            payload_name = "payload.bin"

        fname_bytes = payload_name.encode("utf-8")
        if len(fname_bytes) > 65535:
            raise ValueError("Filename too long")

        cap = cv2.VideoCapture(str(infile))
        if not cap.isOpened():
            raise ValueError("Cannot open video")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        ret, frame0 = cap.read()
        if not ret:
            raise ValueError("Cannot read first frame")

        blue = frame0[:, :, 0].reshape(-1)

        payload_len = len(payload)
        crc = zlib.crc32(payload) & 0xFFFFFFFF

        data = (
            struct.pack(self.FNAME_LEN_FMT, len(fname_bytes)) +
            fname_bytes +
            struct.pack(self.PAYLOAD_LEN_FMT, payload_len) +
            payload +
            struct.pack(self.CRC_FMT, crc)
        )

        bits = np.unpackbits(np.frombuffer(data, dtype=np.uint8))

        if bits.size > blue.size:
            raise ValueError("Payload too large for first frame")

        perm = self._rng(password).permutation(blue.size)

        for i, bit in enumerate(bits):
            blue[perm[i]] = (blue[perm[i]] & 0xFE) | bit

        frame0[:, :, 0] = blue.reshape(height, width)

        fourcc = cv2.VideoWriter_fourcc(*"FFV1")
        out = cv2.VideoWriter(str(outfile), fourcc, fps, (width, height))

        out.write(frame0)
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)

        cap.release()
        out.release()

        return {
            "outfile": outfile.name,
            "method": "First-frame BLUE-channel LSB (lossless)",
            "payload_name": payload_name,
            "payload_bytes": payload_len
        }

    # ================= EXTRACT =================
    def extract(self, infile, password):
        cap = cv2.VideoCapture(str(infile))
        if not cap.isOpened():
            raise ValueError("Cannot open video")

        ret, frame0 = cap.read()
        cap.release()
        if not ret:
            raise ValueError("Cannot read first frame")

        blue = frame0[:, :, 0].reshape(-1)
        perm = self._rng(password).permutation(blue.size)

        idx = 0

        # ---- filename length ----
        fname_len_bits = [blue[perm[idx + i]] & 1 for i in range(16)]
        fname_len = struct.unpack(
            self.FNAME_LEN_FMT,
            np.packbits(fname_len_bits).tobytes()
        )[0]
        idx += 16

        # ---- filename ----
        fname_bits = [blue[perm[idx + i]] & 1 for i in range(fname_len * 8)]
        filename = np.packbits(fname_bits).tobytes().decode("utf-8")
        idx += fname_len * 8

        # ---- payload length ----
        plen_bits = [blue[perm[idx + i]] & 1 for i in range(32)]
        payload_len = struct.unpack(
            self.PAYLOAD_LEN_FMT,
            np.packbits(plen_bits).tobytes()
        )[0]
        idx += 32

        if payload_len <= 0 or payload_len > 10_000_000:
            raise ValueError("Invalid or corrupted payload length")

        # ---- payload ----
        payload_bits = [blue[perm[idx + i]] & 1 for i in range(payload_len * 8)]
        payload = np.packbits(payload_bits).tobytes()
        idx += payload_len * 8

        # ---- CRC ----
        crc_bits = [blue[perm[idx + i]] & 1 for i in range(32)]
        crc_expected = struct.unpack(
            self.CRC_FMT,
            np.packbits(crc_bits).tobytes()
        )[0]

        if zlib.crc32(payload) & 0xFFFFFFFF != crc_expected:
            raise ValueError("CRC mismatch – wrong password or corrupted data")

        return {
            "payload": payload,
            "name": filename,
            "method": "First-frame BLUE-channel extraction"
        }
