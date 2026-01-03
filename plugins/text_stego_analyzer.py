# text_stego_analyzer.py
from PyPDF2 import PdfReader
import re
import math
import unicodedata
from collections import Counter

class TextStegoAnalyzerPlugin:
    name = "text_stego_analyzer"

    ZERO_WIDTH = [
        "\u200b", "\u200c", "\u200d",
        "\u2060", "\ufeff"
    ]

    HOMOGLYPHS = {
        "а": "a", "е": "e", "о": "o", "р": "p",
        "с": "c", "х": "x", "і": "i", "ј": "j"
    }

    def can_handle(self, mime, path):
        return (
            mime and (
                mime.startswith("text/")
                or mime == "application/pdf"
                or mime == "application/octet-stream"
            )
        )

    def _entropy(self, s):
        if not s:
            return 0.0
        counts = Counter(s)
        total = len(s)
        return -sum((c / total) * math.log2(c / total) for c in counts.values())

    def _extract_text(self, path, mime):
        if mime == "application/pdf":
            try:
                reader = PdfReader(path)
                text = ""
                for page in reader.pages:
                    t = page.extract_text()
                    if t:
                        text += t + "\n"
                return text
            except Exception:
                return ""
        else:
            try:
                with open(path, "r", errors="ignore") as f:
                    return f.read()
            except Exception:
                return ""

    def analyze(self, path, mime=None):
        text = self._extract_text(path, mime)
        length = len(text) if text else 1

        zw_count = sum(text.count(z) for z in self.ZERO_WIDTH)
        whitespace_runs = len(re.findall(r"[ \t]{3,}", text))
        homoglyphs = sum(1 for c in text if c in self.HOMOGLYPHS)

        binary_runs = len(re.findall(r"[01]{16,}", text))
        base64_runs = len(re.findall(r"[A-Za-z0-9+/]{20,}={0,2}", text))

        entropy = self._entropy(text)
        entropy_norm = min((entropy - 3.5) / 2.5, 1.0) if entropy > 3.5 else 0.0

        categories = Counter(unicodedata.category(c) for c in text)
        control_ratio = categories.get("Cf", 0) / length

        lines = text.splitlines()
        line_lengths = [len(l) for l in lines if l.strip()]
        line_var = (
            (max(line_lengths) - min(line_lengths)) / max(line_lengths)
            if line_lengths else 0.0
        )

        zw_norm = min(zw_count / (length * 0.002), 1.0)
        ws_norm = min(whitespace_runs / (length * 0.001), 1.0)
        hg_norm = min(homoglyphs / (length * 0.001), 1.0)
        bin_norm = min(binary_runs / 2.0, 1.0)
        b64_norm = min(base64_runs / 2.0, 1.0)
        ctrl_norm = min(control_ratio / 0.001, 1.0)
        line_norm = min(line_var / 0.6, 1.0)

        score = (
            0.30 * zw_norm +
            0.15 * ws_norm +
            0.10 * hg_norm +
            0.15 * bin_norm +
            0.10 * b64_norm +
            0.10 * entropy_norm +
            0.05 * ctrl_norm +
            0.05 * line_norm
        )

        score = round(min(score, 1.0), 4)

        return {
            "length": length,
            "zero_width_count": zw_count,
            "whitespace_runs": whitespace_runs,
            "homoglyph_count": homoglyphs,
            "binary_runs": binary_runs,
            "base64_runs": base64_runs,
            "entropy": round(entropy, 3),
            "line_variance": round(line_var, 3),
            "control_char_ratio": round(control_ratio, 6),
            "suspiciousness_score": score,
            "suspiciousness_percent": round(score * 100, 1),
            "notes": "Detects zero-width chars, encoding patterns, entropy, Unicode abuse, and structure anomalies"
        }
