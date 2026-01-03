# text_stego_analyzer.py
# Text and document steganalysis plugin for UniSteno
# Detects hidden data using Unicode abuse, whitespace patterns,
# entropy analysis, encoding traces, and structural anomalies

from PyPDF2 import PdfReader        # PDF text extraction
import re                          # Regular expressions
import math                        # Mathematical functions
import unicodedata                 # Unicode category inspection
from collections import Counter    # Frequency counting

class TextStegoAnalyzerPlugin:
    # Plugin identifier
    name = "text_stego_analyzer"

    # Unicode zero-width characters commonly used in text steganography
    ZERO_WIDTH = [
        "\u200b",  # zero width space
        "\u200c",  # zero width non-joiner
        "\u200d",  # zero width joiner
        "\u2060",  # word joiner
        "\ufeff"   # zero width no-break space / BOM
    ]

    # Unicode homoglyphs that visually mimic ASCII characters
    # Often used to hide binary data in text
    HOMOGLYPHS = {
        "а": "a", "е": "e", "о": "o", "р": "p",
        "с": "c", "х": "x", "і": "i", "ј": "j"
    }

    def can_handle(self, mime, path):
        """
        Determine whether this plugin can analyze the file.
        Supports:
        - Plain text
        - PDF documents
        - Unknown binary (best-effort extraction)
        """
        return (
            mime and (
                mime.startswith("text/")
                or mime == "application/pdf"
                or mime == "application/octet-stream"
            )
        )

    def _entropy(self, s):
        """
        Compute Shannon entropy of a string.
        Higher entropy often indicates encoded or compressed data.
        """
        if not s:
            return 0.0
        counts = Counter(s)
        total = len(s)
        return -sum(
            (c / total) * math.log2(c / total)
            for c in counts.values()
        )

    def _extract_text(self, path, mime):
        """
        Extract textual content from file.
        Uses PDF parsing for PDFs, raw decoding for others.
        """
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
        """
        Perform multi-feature text steganalysis:
        - Zero-width character detection
        - Whitespace manipulation
        - Unicode homoglyph abuse
        - Binary/Base64 traces
        - Entropy anomalies
        - Structural irregularities
        """

        # Extract text from file
        text = self._extract_text(path, mime)
        length = len(text) if text else 1  # prevent divide-by-zero

        # ================= CHARACTER-LEVEL ANALYSIS =================

        # Count zero-width characters
        zw_count = sum(text.count(z) for z in self.ZERO_WIDTH)

        # Count long whitespace runs (space / tab)
        whitespace_runs = len(re.findall(r"[ \t]{3,}", text))

        # Count homoglyph substitutions
        homoglyphs = sum(1 for c in text if c in self.HOMOGLYPHS)

        # ================= ENCODING SIGNATURES =================

        # Long binary sequences
        binary_runs = len(re.findall(r"[01]{16,}", text))

        # Base64-like patterns
        base64_runs = len(re.findall(r"[A-Za-z0-9+/]{20,}={0,2}", text))

        # ================= ENTROPY =================

        entropy = self._entropy(text)

        # Normalize entropy: natural text ≈ 3.5–4.5 bits
        entropy_norm = (
            min((entropy - 3.5) / 2.5, 1.0)
            if entropy > 3.5 else 0.0
        )

        # ================= UNICODE CONTROL CHARACTERS =================

        categories = Counter(unicodedata.category(c) for c in text)

        # Cf = invisible formatting/control characters
        control_ratio = categories.get("Cf", 0) / length

        # ================= STRUCTURAL ANALYSIS =================

        lines = text.splitlines()
        line_lengths = [len(l) for l in lines if l.strip()]

        # Variance in line length can indicate fixed-width encoding
        line_var = (
            (max(line_lengths) - min(line_lengths)) / max(line_lengths)
            if line_lengths else 0.0
        )

        # ================= NORMALIZATION =================

        zw_norm = min(zw_count / (length * 0.002), 1.0)
        ws_norm = min(whitespace_runs / (length * 0.001), 1.0)
        hg_norm = min(homoglyphs / (length * 0.001), 1.0)
        bin_norm = min(binary_runs / 2.0, 1.0)
        b64_norm = min(base64_runs / 2.0, 1.0)
        ctrl_norm = min(control_ratio / 0.001, 1.0)
        line_norm = min(line_var / 0.6, 1.0)

        # ================= FINAL SUSPICIOUSNESS SCORE =================

        score = (
            0.30 * zw_norm +     # zero-width characters (strong indicator)
            0.15 * ws_norm +     # whitespace encoding
            0.10 * hg_norm +     # homoglyph abuse
            0.15 * bin_norm +    # binary traces
            0.10 * b64_norm +    # base64 traces
            0.10 * entropy_norm +
            0.05 * ctrl_norm +   # invisible Unicode controls
            0.05 * line_norm     # structural irregularities
        )

        score = round(min(score, 1.0), 4)

        # ================= RESULT =================

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
            "notes": (
                "Detects zero-width chars, encoding patterns, entropy, "
                "Unicode abuse, and structural anomalies"
            )
        }
