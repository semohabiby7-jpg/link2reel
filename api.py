"""
مرصاد — Link2Reel API Server (FastAPI)
يرفع على Render، يخدم الموقع على GitHub Pages
"""
import os
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Streamlit Cloud: حقن المفتاح من st.secrets لو متاح
try:
    import streamlit as st
    if 'GEMINI_API_KEY' in st.secrets:
        os.environ['GEMINI_API_KEY'] = st.secrets['GEMINI_API_KEY']
except Exception:
    pass

from scraper import scrape_product
from script_generator import generate_script
from tts_engine import generate_voiceover
from video_builder import build_video

app = FastAPI(title="مرصاد API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# مجلد للتخزين المؤقت للملفات
os.makedirs("static", exist_ok=True)
try:
    app.mount("/files", StaticFiles(directory="static"), name="static")
except Exception:
    pass

# ===== Models =====
class ScrapeReq(BaseModel):
    url: str

class ScriptReq(BaseModel):
    product: dict
    tone: str = "egyptian"

class VoiceReq(BaseModel):
    script: dict
    voice: str = "male"
    tone: str = "egyptian"

class VideoReq(BaseModel):
    product: dict
    script: dict
    audio_path: str

# ===== Endpoints =====
@app.get("/")
def root():
    return {"status": "ok", "app": "مرصاد API", "version": "1.0"}

@app.post("/scrape")
def api_scrape(req: ScrapeReq):
    result = scrape_product(req.url)
    return JSONResponse(result)

@app.post("/script")
def api_script(req: ScriptReq):
    result = generate_script(req.product, req.tone)
    return JSONResponse(result)

@app.post("/voice")
def api_voice(req: VoiceReq):
    out = os.path.join("static", f"voice_{int(time.time())}.mp3")
    result = generate_voiceover(req.script, voice_gender=req.voice, tone=req.tone, output_path=out)
    if result.get("success"):
        result["audio_url"] = f"/files/{os.path.basename(out)}"
    return JSONResponse(result)

@app.post("/video")
def api_video(req: VideoReq):
    out = os.path.join("static", f"video_{int(time.time())}.mp4")
    audio = req.audio_path
    # لو audio_path جاي كـ URL من الـ API، حولّه لمسار محلي
    if audio and audio.startswith("/files/"):
        audio = os.path.join("static", os.path.basename(audio))
    result = build_video(req.product, req.script, audio, out)
    if result.get("success"):
        result["video_url"] = f"/files/{os.path.basename(out)}"
    return JSONResponse(result)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
