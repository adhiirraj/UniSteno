# audio_lsb_analyzer.py
# Audio steganalysis plugin for UniSteno
# Performs LSB statistical analysis + spectral analysis
# Automatically converts non-WAV audio to WAV for analysis

import tempfile
import os
import math
import numpy as np
from collections import Counter

from scipy.io import wavfile
from scipy.signal import stft

# Optional dependency for format conversion (mp3, ogg, etc.)
try:
    from pydub import AudioSegment
except Exception:
    AudioSegment = None


class AudioLSBAnalyzerPlugin:
    name = "audio_lsb_analyzer"

    def can_handle(self, mime, path):
        """
        Accept all audio files.
        Non-WAV formats will be converted internally.
        """
        return mime and mime.startswith("audio/")

    # ================= AUDIO LOADING =================

    def _load_as_wav(self, path):
        """
        Load audio file as WAV.
        If input is not WAV, convert it using pydub.
        Returns: (sample_rate, mono_samples)
        """

        ext = os.path.splitext(path)[1].lower()

        # Case 1: Already WAV
        if ext == ".wav":
            sr, data = wavfile.read(path)

        # Case 2: Convert other formats → WAV
        else:
            if AudioSegment is None:
                raise Exception(
                    "Non-WAV audio requires pydub + ffmpeg installed"
                )

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_name = tmp.name

            audio = AudioSegment.from_file(path)
            audio = audio.set_channels(1)  # force mono
            audio.export(tmp_name, format="wav")

            sr, data = wavfile.read(tmp_name)
            os.unlink(tmp_name)

        # Convert stereo → mono if needed
        if data.ndim > 1:
            data = data.mean(axis=1)

        return sr, data.astype(np.int16)

    # ================= LSB ANALYSIS =================

    def _lsb_entropy(self, samples):
        """
        Compute entropy of LSB distribution.
        Natural audio ≠ perfectly random LSBs.
        """
        lsb = samples & 1
        counts = Counter(lsb.tolist())
        total = len(lsb)

        entropy = 0.0
        for c in counts.values():
            p = c / total
            entropy -= p * math.log2(p)

        return entropy

    def _chi_square(self, samples):
        """
        Chi-square test for LSB randomness.
        """
        lsb = samples & 1
        ones = int(np.count_nonzero(lsb))
        total = len(lsb)
        exp = total / 2.0

        return (
            ((ones - exp) ** 2) / exp +
            (((total - ones) - exp) ** 2) / exp
        )

    # ================= SPECTRAL ANALYSIS =================

    def _spectral_features(self, samples, sr):
        """
        Compute spectral flatness, HF energy ratio,
        and frame-to-frame spectral variance.
        """

        # Short-time Fourier transform
        _, _, Zxx = stft(
            samples,
            fs=sr,
            nperseg=1024,
            noverlap=512,
            padded=False
        )

        power = np.abs(Zxx) ** 2 + 1e-12

        # ----- Spectral Flatness -----
        geo_mean = np.exp(np.mean(np.log(power), axis=0))
        arith_mean = np.mean(power, axis=0)
        flatness = np.mean(geo_mean / arith_mean)

        # ----- High-Frequency Energy Ratio -----
        freqs = np.linspace(0, sr / 2, power.shape[0])
        hf_mask = freqs > (0.6 * (sr / 2))  # top 40% frequencies

        hf_energy = np.sum(power[hf_mask, :])
        total_energy = np.sum(power)
        hf_ratio = hf_energy / total_energy

        # ----- Spectral Variance -----
        frame_energy = np.sum(power, axis=0)
        variance = np.var(frame_energy / np.mean(frame_energy))

        return flatness, hf_ratio, variance

    # ================= ANALYZE =================

    def analyze(self, path, options=None):
        options = options or {}

        """
        Main analysis entry point.
        Returns forensic audio steganalysis metrics.
        """

        sr, samples = self._load_as_wav(path)

        # Use a subset for speed (first ~5 seconds)
        max_samples = min(len(samples), sr * 5)
        samples = samples[:max_samples]

        # ----- LSB Metrics -----
        lsb_entropy = self._lsb_entropy(samples)
        chi_sq = self._chi_square(samples)

        # ----- Spectral Metrics -----
        flatness, hf_ratio, spec_var = self._spectral_features(samples, sr)

        # ================= SCORING =================

        # Natural reference values (empirical)
        NATURAL_LSB_ENTROPY = 0.6
        NATURAL_FLATNESS = 0.3
        NATURAL_HF_RATIO = 0.15
        NATURAL_VAR = 0.1

        def norm(val, nat):
            return min(abs(val - nat) / nat, 1.0)

        score = (
            0.30 * norm(lsb_entropy, NATURAL_LSB_ENTROPY) +
            0.30 * norm(flatness, NATURAL_FLATNESS) +
            0.30 * norm(hf_ratio, NATURAL_HF_RATIO) +
            0.10 * norm(spec_var, NATURAL_VAR)
        )

        score = round(min(score, 1.0), 4)

        # ================= RESULT =================

        return {
            "sample_rate": int(sr),
            "analyzed_samples": int(max_samples),

            "lsb_entropy": float(round(lsb_entropy, 4)),
            "chi_square": float(round(chi_sq, 3)),

            "spectral_flatness": float(round(flatness, 4)),
            "hf_energy_ratio": float(round(hf_ratio, 4)),
            "spectral_variance": float(round(spec_var, 4)),

            "suspiciousness_score": float(score),
            "suspiciousness_percent": float(round(score * 100, 1)),

            "notes": (
                "Detects LSB randomness and spectral noise consistent "
                "with audio steganography. Non-WAV formats are converted "
                "to WAV before analysis."
            )
        }
