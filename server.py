#server.py
import mimetypes
import io
import os
import importlib.util
import traceback
import time
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, send_file
from werkzeug.utils import secure_filename

try:
    import magic
except Exception:
    magic = None

try:
    from PIL import Image
except Exception:
    Image = None

BASE_DIR = Path(".").resolve()
UPLOAD_DIR = BASE_DIR / "uploads"
PLUGINS_DIR = BASE_DIR / "plugins"
UPLOAD_DIR.mkdir(exist_ok=True)
PLUGINS_DIR.mkdir(exist_ok=True)

MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200 MB

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


LOADED_PLUGINS = []

def load_plugins():
    global LOADED_PLUGINS
    LOADED_PLUGINS = []
    for py in PLUGINS_DIR.glob("*.py"):
        name = py.stem
        try:
            spec = importlib.util.spec_from_file_location(f"plugins.{name}", py)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            candidates = []
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and attr_name.lower().endswith("plugin"):
                    candidates.append(attr)
            if hasattr(module, "plugin"):
                candidates.append(getattr(module, "plugin"))

            for cand in candidates:
                try:
                    inst = cand() if isinstance(cand, type) else cand

                    has_can = callable(getattr(inst, "can_handle", None))
                    has_analyze = callable(getattr(inst, "analyze", None))
                    has_embed = callable(getattr(inst, "embed", None))
                    has_extract = callable(getattr(inst, "extract", None))
                    if has_can and (has_analyze or has_embed or has_extract):
                        LOADED_PLUGINS.append(inst)
                    else:
                        print(f"[plugin] skipping {cand}: has_can={has_can}, analyze={has_analyze}, embed={has_embed}, extract={has_extract}")

                except Exception as e:
                    print(f"[plugin] failed to instantiate {cand}: {e}")
                    traceback.print_exc()

        except Exception as e:
            print(f"[plugin] failed to load {py}: {e}")
            traceback.print_exc()

load_plugins()

def detect_mime(filepath: Path):
    if magic:
        try:
            m = magic.Magic(mime=True)
            return m.from_file(str(filepath))
        except Exception as e:
            print("python-magic detection failed:", e)
    ext = filepath.suffix.lower()
    mapping = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
        ".txt": "text/plain",
        ".csv": "text/csv",
        ".json": "application/json",
        ".pdf": "application/pdf",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".mp4": "video/mp4",
        ".mkv": "video/x-matroska",
    }
    return mapping.get(ext, "application/octet-stream")

def is_text_file(path: Path, blocksize: int = 4096):
    """
    Heuristic: read chunk, check for NUL bytes, try UTF-8 decode.
    """
    try:
        with open(path, "rb") as f:
            chunk = f.read(blocksize)
            if not chunk:
                return True
            if b"\x00" in chunk:
                return False
            chunk.decode("utf-8")
            return True
    except Exception:
        return False

def cleanup_old_uploads(max_age_seconds: int = 60*60):
    now = time.time()
    for p in UPLOAD_DIR.iterdir():
        try:
            if now - p.stat().st_mtime > max_age_seconds:
                p.unlink()
        except Exception:
            pass

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/uploads/<path:fname>")
def serve_upload(fname):
    return send_from_directory(UPLOAD_DIR, fname, as_attachment=False)

@app.route("/upload", methods=["POST"])
def upload():
    cleanup_old_uploads()  # keep uploads tidy
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "no file provided"}), 400

    filename = secure_filename(f.filename)
    if not filename:
        return jsonify({"error": "invalid filename"}), 400

    save_path = UPLOAD_DIR / filename
    base, ext = os.path.splitext(filename)
    i = 1
    while save_path.exists():
        filename = f"{base}_{i}{ext}"
        save_path = UPLOAD_DIR / filename
        i += 1

    try:
        f.save(save_path)
    except Exception as e:
        return jsonify({"error": f"failed to save file: {e}"}), 500

    return jsonify({"filename": filename, "size": save_path.stat().st_size})

@app.route("/analyze", methods=["POST"])
def analyze():
    fname = request.form.get("filename")
    if not fname:
        return jsonify({"error": "filename required"}), 400

    path = UPLOAD_DIR / fname
    if not path.exists():
        return jsonify({"error": "file not found"}), 404

    mime = detect_mime(path)
    response = {"filename": fname, "mime": mime, "size": path.stat().st_size}

    if mime and mime.startswith("image/") and Image is not None:
        try:
            with Image.open(path) as im:
                response.update({
                    "type": "image",
                    "format": im.format,
                    "mode": im.mode,
                    "width": im.width,
                    "height": im.height
                })
        except Exception as e:
            response["image_error"] = f"failed to read image: {e}"

    elif is_text_file(path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                txt = fh.read(4096)
                preview = txt if len(txt) <= 2000 else txt[:2000] + "\n...[truncated]"
                response.update({"type": "text", "preview": preview})
        except Exception as e:
            response["text_error"] = str(e)
    else:
        response["note"] = "No specialized analyzer available for this MIME yet."

    plugin_results = {}
    for plugin in LOADED_PLUGINS:
        try:
            if plugin.can_handle(mime, path):
                plugin_res = plugin.analyze(path)
                plugin_results[plugin.name] = plugin_res
        except Exception as e:
            plugin_results[f"{plugin.name}_error"] = str(e)

    if plugin_results:
        response["plugins"] = plugin_results

    return jsonify(response)

@app.route("/embed", methods=["POST"])
def embed():
    fname = request.form.get("filename")
    password = request.form.get("password", "")
    payload_file = request.files.get("payload")
    if not fname or not payload_file:
        return jsonify({"error": "filename and payload required"}), 400

    infile = UPLOAD_DIR / fname
    if not infile.exists():
        return jsonify({"error": "file not found"}), 404

    payload_bytes = payload_file.read()
    payload_name = secure_filename(payload_file.filename or "payload.bin")

    for p in LOADED_PLUGINS:
        try:
            if p.can_handle(detect_mime(infile), infile) and hasattr(p, "embed"):
                outname = f"embedded_{fname}"
                outfile = UPLOAD_DIR / outname
                info = p.embed(infile, payload_bytes, password, outfile, payload_name)
                return jsonify({"outfile": outname, "info": info})
        except Exception as e:
            return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

    return jsonify({"error": "no plugin available to embed this file type"}), 400

@app.route("/extract", methods=["POST"])
def extract():
    fname = request.form.get("filename")
    password = request.form.get("password", "")
    if not fname:
        return jsonify({"error": "filename required"}), 400

    infile = UPLOAD_DIR / fname
    if not infile.exists():
        return jsonify({"error": "file not found"}), 404

    for p in LOADED_PLUGINS:
        try:
            if p.can_handle(detect_mime(infile), infile) and hasattr(p, "extract"):
                res = p.extract(infile, password)

                if isinstance(res, dict) and isinstance(res.get("payload"), (bytes, bytearray)):
                    payload = res.get("payload")
                    suggested_name = res.get("name", "extracted.bin")

                    guessed_type, _ = mimetypes.guess_type(suggested_name)
                    if not guessed_type:
                        guessed_type = "application/octet-stream"

                    inline = guessed_type.startswith("text/")

                    return send_file(
                        io.BytesIO(payload),
                        download_name=suggested_name,
                        as_attachment=not inline,
                        mimetype=f"{guessed_type}; charset=utf-8" if guessed_type.startswith("text/") else guessed_type
                    )

                else:
                    return jsonify(res)
        except Exception as e:
            return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

    return jsonify({"error": "no plugin available to extract this file type"}), 400

if __name__ == "__main__":
    print("Starting UniSteno server...")
    print(f"Loaded plugins: {[p.name for p in LOADED_PLUGINS]}")
    if magic is None:
        print("WARNING: python-magic not installed. Install python-magic-bin on Windows for better MIME detection.")
    if Image is None:
        print("WARNING: Pillow not installed. Image analysis will not be available.")
    app.run(debug=True)