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
from urllib.parse import quote

load_dotenv()

# Streamlit Cloud: .env مش موجود، فنسحب المفتاح من st.secrets ونحقنه كـ env var
try:
    if 'GEMINI_API_KEY' in st.secrets:
        os.environ['GEMINI_API_KEY'] = st.secrets['GEMINI_API_KEY']
except Exception:
    pass

from scraper import scrape_product
from script_generator import generate_script
from tts_engine import generate_voiceover, get_available_voices
from video_builder import build_video

st.set_page_config(
    page_title="Link2Reel — مرصاد",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.main { background: #0f1e3d; }
.stApp { background: linear-gradient(135deg, #0f1e3d, #1a2f5c); color: white; }
h1, h2, h3 { color: #d4a937 !important; }
.stButton > button { background: linear-gradient(135deg, #d4a937, #b8901f); color: #0f1e3d; border: none; border-radius: 10px; font-weight: bold; }
.stButton > button:hover { background: linear-gradient(135deg, #e0b547, #c89a2f); }
.stTextInput > div > div > input { background: rgba(255,255,255,0.1); color: white; border: 1px solid #d4a937; }
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(212,169,55,0.35) !important;
    border-radius: 14px !important;
    padding: 18px !important;
    margin-bottom: 18px !important;
}
.footer { text-align: center; margin-top: 30px; padding: 20px; color: #d4a937; font-size: 14px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center; padding:10px 0 5px;">
    <h1 style="font-size:42px;">🎬 مرصاد — Link2Reel</h1>
    <p style="font-size:16px; color:#ccc;">حوّل أي لينك منتج لفيديو تسويقي احترافي في ثواني</p>
</div>
""", unsafe_allow_html=True)

# ===== Sidebar =====
st.sidebar.markdown("### ⚙️ الإعدادات")
tone = st.sidebar.selectbox("🗣️ اللهجة", ["مصرية", "إنجليزية"], index=0)
voice_gender = st.sidebar.selectbox("🎙️ صوت", ["ذكر", "أنثى"], index=0)
if st.sidebar.button("♻️ إعادة البدء"):
    for k in ['product', 'script', 'audio_path', 'video_path']:
        if k in st.session_state:
            st.session_state[k] = None
    st.rerun()

for k in ['product', 'script', 'audio_path', 'video_path']:
    if k not in st.session_state:
        st.session_state[k] = None

tone_code = 'egyptian' if tone == 'مصرية' else 'english'
gender_code = 'male' if voice_gender == 'ذكر' else 'female'

# ===== Box 1: خانة اللينك =====
with st.container(border=True):
    st.markdown("### 1️⃣ خانة اللينك")
    st.caption("حط رابط المنتج واضغط اقرا المنتج")
    url = st.text_input(
        "رابط المنتج (Amazon / Noon / Shopify / أي متجر)",
        placeholder="https://www.amazon.eg/dp/...",
        label_visibility="collapsed"
    )
    if st.button("🔎 اقرا المنتج", use_container_width=True, type="primary"):
        if not url:
            st.error("اكتب لينك المنتج الأول!")
        else:
            with st.spinner("جاري قراءة بيانات المنتج..."):
                t0 = time.time()
                product = scrape_product(url)
                t_scrape = time.time() - t0
            if product.get('error'):
                st.error(f"❌ {product['error']}")
            elif not product.get('title'):
                st.error("❌ ما قدرتش أقرا المنتج. تأكد من اللينك أو جرّب لينك تاني.")
            else:
                st.session_state.product = product
                st.session_state.script = None
                st.session_state.audio_path = None
                st.session_state.video_path = None
                st.success(f"✅ تم قراءة المنتج في {t_scrape:.1f}s — روح للخانة التانية")
                st.rerun()

# ===== Box 2: خانة الصور =====
if st.session_state.product:
    p = st.session_state.product
    with st.container(border=True):
        st.markdown("### 2️⃣ خانة الصور")
        st.markdown(f"**المنتج:** {p['title']}")
        if p.get('price'):
            st.markdown(f"**السعر:** {p['price']} {p.get('currency','')}")
        if p.get('rating'):
            st.markdown(f"**التقييم:** ⭐ {p['rating']}")
        imgs = p.get('images') or []
        st.markdown(f"**عدد الصور:** {len(imgs)}")
        if imgs:
            n = min(4, len(imgs))
            cols = st.columns(n)
            for i in range(n):
                with cols[i]:
                    try:
                        st.image(imgs[i], use_container_width=True)
                    except Exception:
                        st.warning("صورة مش متاحة")
        else:
            st.info("مفيش صور متاحة لهذا المنتج — هتستخدم صورة افتراضية في الفيديو")

# ===== Box 3: خانة الاسكريبت =====
if st.session_state.product:
    with st.container(border=True):
        st.markdown("### 3️⃣ خانة الاسكريبت")
        st.caption("السكريبت التسويقي اللي هيتقال في الفيديو")
        if st.button("📝 ولّد الاسكريبت التسويقي", use_container_width=True, type="primary"):
            with st.spinner("جاري كتابة السكريبت بالـ AI..."):
                t0 = time.time()
                script = generate_script(st.session_state.product, tone_code)
                t_script = time.time() - t0
            if script and script.get('hook'):
                st.session_state.script = script
                st.session_state.audio_path = None
                st.session_state.video_path = None
                st.success(f"✅ السكريبت جاهز في {t_script:.1f}s")
                st.rerun()
            else:
                st.error("❌ فشل توليد الاسكريبت. جرّب تاني.")
        if st.session_state.script:
            s = st.session_state.script
            st.markdown(f"**HOOK (الجذب):** {s.get('hook','')}")
            st.markdown(f"**PROBLEM (المشكلة):** {s.get('problem','')}")
            st.markdown(f"**SOLUTION (الحل):** {s.get('solution','')}")
            st.markdown(f"**FEATURES (المميزات):** {s.get('features','')}")
            st.markdown(f"**CTA (الدعوة):** {s.get('cta','')}")
            full = s.get('full_script', '')
            if full:
                st.download_button(
                    "📄 حمّل الاسكريبت (.txt)",
                    data=full.encode('utf-8'),
                    file_name="script.txt",
                    mime="text/plain",
                    use_container_width=True
                )

# ===== Box 4: خانة توليد الاسكريبت بالصوت =====
if st.session_state.script:
    with st.container(border=True):
        st.markdown("### 4️⃣ خانة توليد الاسكريبت بالصوت")
        st.caption("حوّل الاسكريبت لصوت تعليق صوتي")
        if st.button("🎙️ ولّد الصوت", use_container_width=True, type="primary"):
            with st.spinner("جاري توليد الصوت..."):
                audio_path = "output_voice.mp3"
                audio_result = generate_voiceover(
                    st.session_state.script,
                    voice_gender=gender_code,
                    tone=tone_code,
                    output_path=audio_path
                )
            if audio_result.get('success'):
                st.session_state.audio_path = audio_path
                st.session_state.audio_info = audio_result
                st.session_state.video_path = None
                st.success(f"✅ الصوت جاهز ({audio_result.get('duration','?')}s) — روح للخانة الخامسة")
                st.rerun()
            else:
                st.warning(f"⚠️ {audio_result.get('error','فشل توليد الصوت')}")
        if st.session_state.audio_path:
            info = st.session_state.get('audio_info', {})
            st.markdown(f"**الصوت المستخدم:** {info.get('voice_used','—')}")
            st.audio(st.session_state.audio_path)
            try:
                with open(st.session_state.audio_path, 'rb') as f:
                    audio_bytes = f.read()
                st.download_button(
                    "🎵 حمّل الصوت (.mp3)",
                    data=audio_bytes,
                    file_name="voiceover.mp3",
                    mime="audio/mpeg",
                    use_container_width=True
                )
            except Exception:
                pass

# ===== Box 5: خانة الفيديو =====
if st.session_state.audio_path:
    with st.container(border=True):
        st.markdown("### 5️⃣ خانة الفيديو")
        st.caption("اجمع الصور + الصوت في فيديو نهائي جاهز للنشر")
        if st.button("🎬 ابني الفيديو", use_container_width=True, type="primary"):
            with st.spinner("جاري بناء الفيديو... (دقيقة بالظبط)"):
                video_path = "output_video.mp4"
                video_result = build_video(
                    st.session_state.product,
                    st.session_state.script,
                    st.session_state.audio_path,
                    video_path
                )
            if video_result.get('success'):
                st.session_state.video_path = video_path
                st.success(f"✅ الفيديو جاهز! ({video_result.get('duration','?')}s)")
                st.rerun()
            else:
                st.error(f"❌ {video_result.get('error','فشل بناء الفيديو')}")
        if st.session_state.video_path:
            st.video(st.session_state.video_path)
            try:
                with open(st.session_state.video_path, 'rb') as f:
                    video_bytes = f.read()
                st.download_button(
                    "⬇️ تحميل الفيديو (.mp4)",
                    data=video_bytes,
                    file_name="reel.mp4",
                    mime="video/mp4",
                    use_container_width=True
                )
            except Exception:
                pass
            share_url = "https://link2reel.streamlit.app"
            share_text = "🎬 فيديو تسويقي اتعمل بمرصاد — Link2Reel"
            wa_link = f"https://wa.me/?text={quote(share_text + ' ' + share_url)}"
            st.markdown(f"[📲 مشاركة على واتساب]({wa_link})")

# ===== Footer =====
st.markdown("""
<div class="footer">
    <p>🎬 <b>مرصاد — Link2Reel</b> | <i>Smart Analyst | MIA8444</i></p>
    <p style="font-size:12px; color:#888;">حوّل أي لينك لفيديو احترافي في ثواني</p>
</div>
""", unsafe_allow_html=True)
