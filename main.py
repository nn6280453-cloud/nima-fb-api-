from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import yt_dlp
import os
import uuid
import glob

app = FastAPI(title="FB Video Downloader API", version="1.0.0")

# Downloads folder එක හදන්න
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


class VideoRequest(BaseModel):
    url: str


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "FB Video Downloader API is running",
        "usage": "POST /download with JSON body: {\"url\": \"<facebook_url>\"}"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/download")
async def download_fb_video(req: VideoRequest):
    """
    Facebook video URL එකක් ලබාදුන්නම video file එක return කරනවා.
    """
    url = req.url.strip()

    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    if "facebook.com" not in url and "fb.watch" not in url and "fb.com" not in url:
        raise HTTPException(status_code=400, detail="Not a valid Facebook URL")

    # Unique file name එකක් හදන්න
    file_id = str(uuid.uuid4())
    outtmpl = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")

    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "merge_output_format": "mp4",
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        # FFmpeg merge නිසා extension එක වෙනස් වෙන්න පුළුවන්
        if not os.path.exists(filename):
            matches = glob.glob(os.path.join(DOWNLOAD_DIR, f"{file_id}.*"))
            if not matches:
                raise HTTPException(status_code=500, detail="Download failed")
            filename = matches[0]

        # වීඩියෝ නම ලබාගැනීම
        title = info.get("title", "facebook_video")
        
        # වීඩියෝ නමේ ඉංග්‍රීසි නොවන අකුරු (සිංහල, ඉමෝජි) ඉවත් කරන්න
        safe_title = "".join(c for c in title if c.isascii() and (c.isalnum() or c in " -_"))[:60].strip()
        
        # නම කිසිම දෙයක් ඉතුරු නොවුණොත් default නම දාන්න
        if not safe_title:
            safe_title = "facebook_video"

        return FileResponse(
            filename,
            media_type="video/mp4",
            filename=f"{safe_title}.mp4",
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.mp4"'},
        )

    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=400, detail=f"Download error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
