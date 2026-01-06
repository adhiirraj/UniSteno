# video_bitplane_visualizer.py
# Frame-wise RGB + SUPER bitplane visualization for videos
# Produces 32 videos (R/G/B/SUPER × 8 bits)
# Correctly encoded for browser playback (BGR, isColor=True)

import cv2
import numpy as np
from pathlib import Path


class VideoBitplaneVisualizerPlugin:
    name = "video_bitplane_visualizer"

    def can_handle(self, mime, path):
        return mime and mime.startswith("video/")

    def analyze(self, path, options=None):
        path = Path(path)
        video_name = path.stem

        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            raise ValueError("Unable to open video")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        out_dir = Path("uploads/video_bitplanes") / video_name
        out_dir.mkdir(parents=True, exist_ok=True)

        fourcc = cv2.VideoWriter_fourcc(*"VP80")

        # ---------------- Writers ----------------
        writers = {}
        for ch in ["R", "G", "B", "SUPER"]:
            writers[ch] = {}
            for bit in range(8):
                writers[ch][bit] = cv2.VideoWriter(
                    str(out_dir / f"{ch}_bit_{bit}.webm"),
                    fourcc,
                    fps,
                    (width, height),
                    isColor=True
                )

        frames = 0

        while True:
            ret, frame_bgr = cap.read()
            if not ret:
                break

            # Convert to RGB for logical bit extraction
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

            R = frame_rgb[:, :, 0]
            G = frame_rgb[:, :, 1]
            B = frame_rgb[:, :, 2]

            for bit in range(8):
                r = ((R >> bit) & 1) * 255
                g = ((G >> bit) & 1) * 255
                b = ((B >> bit) & 1) * 255

                # -------- Individual channels (colorized) --------
                writers["R"][bit].write(
                    cv2.merge([np.zeros_like(r), np.zeros_like(r), r])  # BGR
                )
                writers["G"][bit].write(
                    cv2.merge([np.zeros_like(g), g, np.zeros_like(g)])
                )
                writers["B"][bit].write(
                    cv2.merge([b, np.zeros_like(b), np.zeros_like(b)])
                )

                # -------- SUPER (true RGB combined, then BGR) --------
                super_rgb = cv2.merge([r, g, b])
                super_bgr = cv2.cvtColor(super_rgb, cv2.COLOR_RGB2BGR)
                writers["SUPER"][bit].write(super_bgr)

            frames += 1

        cap.release()
        for ch in writers:
            for bit in writers[ch]:
                writers[ch][bit].release()

        # ---------------- UI response ----------------
        planes = {
            ch: {
                f"bit_{bit}": f"/uploads/video_bitplanes/{video_name}/{ch}_bit_{bit}.webm"
                for bit in range(8)
            }
            for ch in ["R", "G", "B", "SUPER"]
        }

        return {
            "description": "Video bitplane visualization (RGB + SUPER × 8 bits)",
            "frames": frames,
            "width": width,
            "height": height,
            "planes": planes
        }
