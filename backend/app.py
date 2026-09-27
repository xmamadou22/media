import os
import tempfile
from pathlib import Path

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)

@app.get("/")
def home():
    return jsonify({"status": "ok"})

@app.post("/download")
def download():
    data = request.get_json(silent=True) or {}
    url = str(data.get("url", "")).strip()
    media_type = data.get("type", "video")

    if not url:
        return jsonify({"error": "URL manquante."}), 400

    if media_type not in ("audio", "video"):
        return jsonify({"error": "Format invalide."}), 400

    temp = Path(tempfile.mkdtemp(prefix="media_dl_"))
    template = str(temp / "%(title).180B.%(ext)s")

    if media_type == "audio":
        opts = {
            "format": "bestaudio/best",
            "outtmpl": template,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }
    else:
        opts = {
            "format": "bestvideo*+bestaudio/best",
            "merge_output_format": "mp4",
            "outtmpl": template,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            prepared = Path(ydl.prepare_filename(info))

        files = list(temp.iterdir())

        # When video/audio streams are merged, the resulting extension can differ.
        if media_type == "video":
            mp4 = [p for p in files if p.suffix.lower() == ".mp4"]
            if mp4:
                prepared = mp4[0]

        if not prepared.exists():
            if not files:
                raise RuntimeError("Aucun fichier n'a été généré.")
            prepared = files[0]

        title = info.get("title") or "download"
        ext = prepared.suffix or ""
        filename = "".join(c for c in title if c not in '<>:"/\\|?*').strip()
        filename = (filename[:120] or "download") + ext

        return send_file(
            prepared,
            as_attachment=True,
            download_name=filename,
            max_age=0
        )

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
