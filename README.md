# MemeVault 1000+

MemeVault is a small Flask website that searches Wikimedia Commons for openly available video files and builds a ZIP archive.

## Important limitations

- This does **not** guarantee 1,000 files will be found. Commons is not a viral-meme feed.
- Results are not guaranteed to be vertical, MP4, or 480p. This version does not transcode video.
- The app includes source/license notes where available. Review the original file page and license before redistribution.
- ZIP generation is resource-intensive. A free host may time out or run out of memory/disk space for large archives.
- This is a working starter project, but it must be deployed with a backend before the button can download real files. A static-only hosting service cannot run this Python backend.

## Run locally (Windows 10)

1. Install Python 3.11 or newer.
2. Extract this ZIP to a folder.
3. Open Command Prompt in that folder.
4. Run:

   ```bat
   py -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   python app.py
   ```

5. Open `http://127.0.0.1:5000`.

## Deploy

The included `render.yaml` is a starting point for Render. Connect the project repository and deploy as a Python web service. Free hosting policies and limits can change; long-running downloads may need a paid or self-hosted worker. For a production version, implement background jobs, retries, storage cleanup, source attribution, codec normalization, and strict per-file/total size caps.