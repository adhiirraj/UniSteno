# audio_spectrogram_visualizer.py
# Full-duration spectrogram visualizer with UI-controlled parameters
# Saves spectrogram to disk and returns URL (no base64)

import matplotlib
matplotlib.use("Agg")  # headless / server-safe

import io
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import stft
from scipy.io import wavfile
from pathlib import Path

try:
    from pydub import AudioSegment
except Exception:
    AudioSegment = None


class AudioSpectrogramVisualizerPlugin:
    name = "audio_spectrogram_visualizer"

    # Where spectrogram images are stored
    OUTPUT_DIR = Path("uploads/spectrograms")

    def __init__(self):
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def can_handle(self, mime, path):
        return mime and mime.startswith("audio/")

    def _load_audio(self, path: Path):
        # WAV fast path
        if path.suffix.lower() == ".wav":
            sr, data = wavfile.read(path)
        else:
            if AudioSegment is None:
                raise Exception("pydub + ffmpeg required for non-WAV audio")

            audio = AudioSegment.from_file(path)
            audio = audio.set_channels(1)

            buf = io.BytesIO()
            audio.export(buf, format="wav")
            buf.seek(0)

            sr, data = wavfile.read(buf)

        if data.ndim > 1:
            data = data.mean(axis=1)

        return sr, data.astype(np.float32)

    def analyze(self, path, options=None):
        options = options or {}

        # --- UI OPTIONS ---
        log_scale = bool(options.get("log_scale", True))
        scroll_speed = int(options.get("scroll_speed", 3))

        # --- LOAD AUDIO ---
        sr, samples = self._load_audio(path)
        duration = len(samples) / sr

        # --- SCROLL SPEED → TIME RESOLUTION ---
        window_map = {
            1: 512,
            2: 1024,
            3: 2048,
            4: 4096,
            5: 8192
        }

        nperseg = window_map.get(scroll_speed, 2048)
        noverlap = nperseg // 2

        # --- STFT ---
        f, t, Zxx = stft(
            samples,
            fs=sr,
            nperseg=nperseg,
            noverlap=noverlap,
            padded=False,
            boundary=None
        )

        mag = np.abs(Zxx)
        spec_db = 20 * np.log10(mag + 1e-8)

        # --- FREQUENCY AXIS ---
        if log_scale:
            f_min = max(20.0, f[1])
            f_max = sr / 2.0

            log_bins = np.logspace(
                np.log10(f_min),
                np.log10(f_max),
                256
            )

            spec_plot = np.zeros((len(log_bins) - 1, spec_db.shape[1]))

            for i in range(len(log_bins) - 1):
                idx = np.where((f >= log_bins[i]) & (f < log_bins[i + 1]))[0]
                if idx.size:
                    spec_plot[i] = spec_db[idx].mean(axis=0)

            y_vals = log_bins
        else:
            spec_plot = spec_db
            y_vals = f

        # --- DYNAMIC RANGE (dCode-like) ---
        vmax = np.percentile(spec_plot, 99)
        vmin = vmax - 60
        spec_plot = np.clip(spec_plot, vmin, vmax)

        # --- PLOT (dark, dCode-style) ---
        plt.style.use("dark_background")
        fig, ax = plt.subplots(figsize=(12, 4), facecolor="black")
        ax.set_facecolor("black")

        ax.imshow(
            spec_plot,
            origin="lower",
            aspect="auto",
            cmap="inferno",
            extent=[t.min(), t.max(), y_vals[0], y_vals[-1]],
            vmin=vmin,
            vmax=vmax
        )

        if log_scale:
            ax.set_yscale("log")

        ax.set_xlabel("Time (s)", color="white")
        ax.set_ylabel("Frequency (Hz)", color="white")
        ax.set_title(
            "Audio Spectrogram "
            + ("(Log Frequency)" if log_scale else "(Linear Frequency)"),
            color="white"
        )

        ax.tick_params(colors="white")
        plt.tight_layout()

        # --- SAVE TO DISK ---
        out_name = f"spectrogram_{path.stem}_log{int(log_scale)}_s{scroll_speed}.png"
        out_path = self.OUTPUT_DIR / out_name

        plt.savefig(out_path, format="png", dpi=120)
        plt.close(fig)

        # --- RETURN METADATA ONLY ---
        return {
            "description": "Full-duration spectrogram",
            "sample_rate": int(sr),
            "duration_seconds": round(duration, 2),
            "log_scale": log_scale,
            "scroll_speed": scroll_speed,
            "spectrogram_url": f"/uploads/spectrograms/{out_name}"
        }
