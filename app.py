"""
=================================================================
Link2Reel (مرصاد) - Main Application
Streamlit Dashboard for Product-to-Video Generation
Ownership: Smart Analyst | MIA8444
=================================================================
"""

import os
import time
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Import modules
from scraper import scrape_product
from script_generator import generate_script
from tts_engine import generate_voiceover, get_available_voices
from video_builder import build_video

# ===== Page Config =====
st.set_page_config(
    page_title="Link2Reel — مرصاد",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== Custom CSS =====
st.markdown("""
<style>
.main { background: #0f1e3d; }
.stApp { background: linear-gradient(135deg, #0f1e3d, #1a2f5c); color: white; }
h1, h2, h3 { color: #d4a937 !important; }
.stButton > button { background: linear-gradient(135deg, #d4a937, #b8901f); color: #0f1e3d; border: none; border-radius: 10px; font-weight: bold; }
.stButton > button:hover { background: linear-gradient(135deg, #e0b547, #c89a2f); }
.stTextInput > div > div > input { background: rgba(255,255,255,0.1); color: white; border: 1px solid #d4a937; }
.footer { text-align: center; margin-top: 50px; padding: 20px; color: #d4a937; font-size: 14px; }
.step-box { background: rgba(212,169,55,0.1); padding: 15px; border-radius: 10px; margin: 10px 0; border-right: 3px solid #d4a937; }
</style>
""", unsafe_allow_html=True)

# ===== Header =====
st.markdown("""
<div style="text-align:center; padding:20px 0;">
    <h1 style="font-size:48px;">🎬 مرصاد — Link2Reel</h1>
    <p style="font-size:18px; color:#ccc;">حوّل أي لينك منتج لفيديو تسويقي احترافي في ثواني</p>
</div>
""", unsafe_allow_html=True)

# ===== Sidebar =====
st.sidebar.markdown("### ⚙️ الإعدادات")
tone = st.sidebar.selectbox("🗣️ اللهجة", ["مصرية", "إنجليزية"], index=0)
voice_gender = st.sidebar.selectbox("🎙️ صوت", ["ذكر", "أنثى"], index=0)

# ===== Main Input =====
st.markdown("### 📎 حط لينك المنتج")
url = st.text_input(
    "رابط المنتج (Amazon / Noon / Shopify / أي متجر)",
    placeholder="https://www.amazon.eg/dp/..."
)

st.markdown("")

# ===== Process Button =====
if st.button("🚀 ابدأ — حوّل لفيديو", use_container_width=True):
    if not url:
        st.error("اكتب لينك المنتج الأول!")
    else:
        # Map tone
        tone_code = 'egyptian' if tone == 'مصرية' else 'english'
        gender_code = 'male' if voice_gender == 'ذكر' else 'female'
        
        progress = st.progress(0)
        status = st.empty()
        
        # ===== Step 1: Scraping =====
        status.markdown('<div class="step-box">🔍 <b>الخطوة 1:</b> جاري قراءة بيانات المنتج...</div>', unsafe_allow_html=True)
        progress.progress(20)
        
        t0 = time.time()
        product = scrape_product(url)
        t_scrape = time.time() - t0
        
        if product.get('error'):
            st.error(f"❌ {product['error']}")
            st.stop()
        
        if not product.get('title'):
            st.error("❌ ما قدرتش أقرا المنتج. تأكد من اللينك.")
            st.stop()
        
        # Show product info
        st.markdown('<div class="step-box">')
        st.markdown(f"### ✅ تم قراءة المنتج ({t_scrape:.1f}s)")
        st.markdown(f"**الاسم:** {product['title']}")
        if product.get('price'):
            st.markdown(f"**السعر:** {product['price']} {product.get('currency','')}")
        if product.get('rating'):
            st.markdown(f"**التقييم:** ⭐ {product['rating']}")
        if product.get('images'):
            st.markdown(f"**الصور:** {len(product['images'])} صورة")
        st.markdown('</div>')
        
        # ===== Step 2: Script Generation =====
        status.markdown('<div class="step-box">📝 <b>الخطوة 2:</b> جاري كتابة السكريبت التسويقي...</div>', unsafe_allow_html=True)
        progress.progress(40)
        
        t0 = time.time()
        script = generate_script(product, tone_code)
        t_script = time.time() - t0
        
        st.markdown('<div class="step-box">')
        st.markdown(f"### ✅ السكريبت جاهز ({t_script:.1f}s)")
        st.markdown(f"**HOOK:** {script.get('hook','')}")
        st.markdown(f"**PROBLEM:** {script.get('problem','')}")
        st.markdown(f"**SOLUTION:** {script.get('solution','')}")
        st.markdown(f"**FEATURES:** {script.get('features','')}")
        st.markdown(f"**CTA:** {script.get('cta','')}")
        st.markdown('</div>')
        
        # Download script button
        st.download_button(
            "📄 حمّل السكريبت (.txt)",
            data=script.get('full_script', ''),
            file_name="script.txt",
            mime="text/plain"
        )
        
        # ===== Step 3: Voiceover =====
        status.markdown('<div class="step-box">🎙️ <b>الخطوة 3:</b> جاري توليد الصوت...</div>', unsafe_allow_html=True)
        progress.progress(60)
        
        audio_path = "output_voice.mp3"
        audio_result = generate_voiceover(script, voice_gender=gender_code, tone=tone_code, output_path=audio_path)
        
        st.markdown('<div class="step-box">')
        if audio_result['success']:
            st.markdown(f"### ✅ الصوت جاهز ({audio_result['duration']}s)")
            st.markdown(f"**الصوت:** {audio_result['voice_used']}")
            st.audio(audio_path)
            st.download_button("🎵 حمّل الصوت (.mp3)", data=open(audio_path,'rb').read(), file_name="voiceover.mp3", mime="audio/mpeg")
        else:
            st.warning(f"⚠️ {audio_result.get('error','فشل توليد الصوت')}")
        st.markdown('</div>')
        
        # ===== Step 4: Video =====
        if audio_result['success']:
            status.markdown('<div class="step-box">🎬 <b>الخطوة 4:</b> جاري بناء الفيديو...</div>', unsafe_allow_html=True)
            progress.progress(80)
            
            video_path = "output_video.mp4"
            video_result = build_video(product, script, audio_path, video_path)
            
            st.markdown('<div class="step-box">')
            if video_result['success']:
                st.markdown(f"### ✅ الفيديو جاهز! ({video_result['duration']}s)")
                st.video(video_path)
                st.download_button("🎬 حمّل الفيديو (.mp4)", data=open(video_path,'rb').read(), file_name="reel.mp4", mime="video/mp4")
            else:
                st.error(f"❌ {video_result.get('error','فشل بناء الفيديو')}")
            st.markdown('</div>')
        
        progress.progress(100)
        status.markdown("### 🎉 تم! الفيديو جاهز للنشر")

# ===== Footer =====
st.markdown("""
<div class="footer">
    <p>🎬 <b>مرصاد — Link2Reel</b> | <i>Smart Analyst | MIA8444</i></p>
    <p style="font-size:12px; color:#888;">حوّل أي لينك لفيديو احترافي في ثواني</p>
</div>
""", unsafe_allow_html=True)
