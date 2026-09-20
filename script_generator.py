"""
=================================================================
Link2Reel (مرصاد) - Marketing Script Generator
AI-powered marketing script generation using Gemini API
Ownership: Smart Analyst | MIA8444
=================================================================
"""

import os
import json
import re
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

# Try to import Gemini
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# ===== Config =====
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
SIGNATURE = "Smart Analyst | MIA8444"


def generate_script(product_data: Dict, tone: str = 'egyptian') -> Dict:
    """
    Generate a marketing script for a product.
    
    Args:
        product_data: Dict from scraper.py
        tone: 'egyptian' (Egyptian Arabic) or 'english' (Professional English)
    
    Returns:
        Dict with: hook, problem, solution, features, cta, full_script, duration
    """
    if GEMINI_AVAILABLE and GEMINI_API_KEY:
        return _generate_with_gemini(product_data, tone)
    else:
        return _generate_fallback(product_data, tone)


def _generate_with_gemini(product_data: Dict, tone: str) -> Dict:
    """Generate script using Gemini API."""
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-flash-latest')
    
    prompt = _build_prompt(product_data, tone)
    
    try:
        response = model.generate_content(prompt)
        script_text = response.text
        return _parse_script(script_text, product_data, tone)
    except Exception as e:
        print(f'Gemini error: {e}')
        return _generate_fallback(product_data, tone)


def _build_prompt(product_data: Dict, tone: str) -> str:
    """Build the prompt for Gemini."""
    title = product_data.get('title', 'المنتج')
    price = product_data.get('price', 'غير محدد')
    features = product_data.get('features', [])
    description = product_data.get('description', '')
    rating = product_data.get('rating', '')
    reviews = product_data.get('reviews', [])
    
    features_text = '\n'.join([f'- {f}' for f in features[:5]]) if features else '- مميزات المنتج'
    reviews_text = '\n'.join([f'- {r.get("body","")[:100]}' for r in reviews[:3]]) if reviews else ''
    
    if tone == 'egyptian':
        return f"""انت خبير تسويق مصري محترف. اكتب سكريبت فيديو تسويقي قصير (30-60 ثانية) باللهجة المصرية لهذا المنتج.

المنتج: {title}
السعر: {price}
المميزات:
{features_text}
الوصف: {description[:300] if description else 'غير متاح'}
التقييم: {rating}

{f'آراء العملاء:' if reviews_text else ''}
{reviews_text}

اكتب السكريبت بالشكل ده بالظبط (كل قسم في سطر منفصل):

HOOK: [جملة قوية أول 3 ثواني توقف السكROLL - سؤال صادم أو جملة غريبة]
PROBLEM: [المشكلة اللي بتعاني منها الجمهور المستهدف]
SOLUTION: [المنتج هو الحل - اذكر اسم المنتج]
FEATURES: [مميزات المنتج بشكل جذاب في 2-3 جمل]
CTA: [دعوة قوية للإجراء - اطلب منهم يحملوا المنتج أو يشتروه]

خلي الكلام طبيعي، جذاب، ومصري أصيل. استخدم إيموجي بشكل طبيعي. مدة الفيديو 30-60 ثانية.
"""
    else:
        return f"""You are an expert marketing copywriter. Write a short marketing video script (30-60 seconds) for this product.

Product: {title}
Price: {price}
Features:
{features_text}
Description: {description[:300] if description else 'N/A'}
Rating: {rating}

{f'Customer reviews:' if reviews_text else ''}
{reviews_text}

Write the script in this exact format (each section on a new line):

HOOK: [Powerful first 3 seconds to stop the scroll - shocking question or bold statement]
PROBLEM: [The problem your target audience faces]
SOLUTION: [This product is the solution - mention the product name]
FEATURES: [Product features in 2-3 engaging sentences]
CTA: [Strong call to action - tell them to buy or download]

Keep it natural, engaging, and professional. Duration: 30-60 seconds.
"""


def _parse_script(script_text: str, product_data: Dict, tone: str) -> Dict:
    """Parse the generated script into sections."""
    sections = {
        'hook': '',
        'problem': '',
        'solution': '',
        'features': '',
        'cta': '',
        'full_script': script_text,
        'tone': tone,
        'duration': '45s'
    }
    
    # Extract sections
    for key, label in [('hook', 'HOOK'), ('problem', 'PROBLEM'), ('solution', 'SOLUTION'),
                      ('features', 'FEATURES'), ('cta', 'CTA')]:
        pattern = rf'{label}:\s*(.*?)(?=\n[A-Z]+:|$)'
        match = re.search(pattern, script_text, re.DOTALL)
        if match:
            sections[key] = match.group(1).strip()
    
    return sections


def _generate_fallback(product_data: Dict, tone: str) -> Dict:
    """Fallback script generator (no AI)."""
    title = product_data.get('title', 'المنتج')
    price = product_data.get('price', '')
    features = product_data.get('features', [])
    
    if tone == 'egyptian':
        hook = f"بتدّور على حل لمشكلتك؟ 🤔 دي خلصت دلوقتي!"
        problem = f"تعبت من البحث واللف والدوران؟ ضيّعت وقت ومجهود كتير؟"
        solution = f"لقينا الحل! {title} — أحسن اختيارلك 🎯"
        f_list = features[:3] if features else ['جودة عالية', 'سعر مناسب', 'ضمان']
        features_text = '. '.join(f_list)
        features_str = f"ليه تختاره؟ {features_text} 💪"
        cta = f"اطلبه دلوقتي بسعر {price or 'مميز'}! اضغط اللينك واطلب قبل ما يخلص 🚀"
    else:
        hook = "Looking for a solution? 🤔 Your search ends here!"
        problem = "Tired of searching and wasting time? We've been there."
        solution = f"Here's the answer: {title} — the best choice for you 🎯"
        f_list = features[:3] if features else ['High quality', 'Great price', 'Guaranteed']
        features_text = '. '.join(f_list)
        features_str = f"Why choose it? {features_text} 💪"
        cta = f"Get it now for {price or 'a great price'}! Click the link before it's gone 🚀"
    
    full_script = f"HOOK: {hook}\nPROBLEM: {problem}\nSOLUTION: {solution}\nFEATURES: {features_str}\nCTA: {cta}"
    
    return {
        'hook': hook,
        'problem': problem,
        'solution': solution,
        'features': features_str,
        'cta': cta,
        'full_script': full_script,
        'tone': tone,
        'duration': '45s'
    }


# ===== Test =====
if __name__ == '__main__':
    test_product = {
        'title': 'سماعات بلوتوث لاسلكية',
        'price': '299 جنيه',
        'features': ['صوت نقاء عالي', 'بطارية 24 ساعة', 'مقاومة للماء IPX7'],
        'description': 'سماعات بلوتوث احترافية بجودة عالية',
        'rating': 4.5,
        'reviews': []
    }
    
    print('=== Egyptian Arabic ===')
    result = generate_script(test_product, 'egyptian')
    print(json.dumps(result, indent=2, ensure_ascii=False))
