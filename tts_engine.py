"""
=================================================================
Link2Reel (مرصاد) - Text-to-Speech Engine
Generates natural voiceover using Edge-TTS (free) or ElevenLabs (premium)
Ownership: Smart Analyst | MIA8444
=================================================================
"""

import os
import asyncio
from typing import Dict, Optional

# Try to import edge-tts
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

# Try to import gTTS (fallback)
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False


# ===== Voice Profiles =====
VOICES = {
    'egyptian': {
        'male': 'ar-EG-SalamahNeural',
        'female': 'ar-EG-NairaNeural',
    },
    'english': {
        'male': 'en-US-GuyNeural',
        'female': 'en-US-JennyNeural',
    }
}

# Default voice settings
DEFAULT_RATE = '+0%'
DEFAULT_VOLUME = '+0%'


def generate_voiceover(script_data: Dict, voice_gender: str = 'male', 
                       tone: str = 'egyptian', output_path: str = 'output_voice.mp3') -> Dict:
    """
    Generate voiceover audio from script.
    
    Args:
        script_data: Dict from script_generator.py
        voice_gender: 'male' or 'female'
        tone: 'egyptian' or 'english'
        output_path: Path to save audio file
    
    Returns:
        Dict with: success, audio_path, duration, voice_used, error
    """
    full_script = script_data.get('full_script', '')
    
    # Clean script (remove labels like HOOK:, PROBLEM:, etc.)
    clean_text = _clean_script(full_script)
    
    if not clean_text:
        return {
            'success': False,
            'error': 'No text to synthesize',
            'audio_path': None
        }
    
    if EDGE_TTS_AVAILABLE:
        result = asyncio.run(_generate_edge_tts(clean_text, voice_gender, tone, output_path))
        if result['success']:
            return result
    
    # Fallback to gTTS
    if GTTS_AVAILABLE:
        return _generate_gtts(clean_text, tone, output_path)
    
    return _generate_placeholder(clean_text, output_path)


async def _generate_edge_tts(text: str, gender: str, tone: str, output_path: str) -> Dict:
    """Generate audio using Edge-TTS."""
    try:
        voice = VOICES.get(tone, VOICES['egyptian']).get(gender, VOICES['egyptian']['male'])
        
        communicate = edge_tts.Communicate(text, voice, rate=DEFAULT_RATE, volume=DEFAULT_VOLUME)
        await communicate.save(output_path)
        
        # Estimate duration (rough: 150 words per minute)
        word_count = len(text.split())
        duration = (word_count / 150) * 60  # seconds
        
        return {
            'success': True,
            'audio_path': output_path,
            'duration': round(duration, 1),
            'voice_used': voice,
            'word_count': word_count,
            'error': None
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Edge-TTS error: {str(e)}',
            'audio_path': None
        }


def _generate_gtts(text: str, tone: str, output_path: str) -> Dict:
    """Generate audio using gTTS (Google Text-to-Speech)."""
    try:
        lang = 'ar' if tone == 'egyptian' else 'en'
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(output_path)
        
        word_count = len(text.split())
        duration = (word_count / 150) * 60
        
        return {
            'success': True,
            'audio_path': output_path,
            'duration': round(duration, 1),
            'voice_used': 'gTTS (Google)',
            'word_count': word_count,
            'error': None
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'gTTS error: {str(e)}',
            'audio_path': None
        }


def _generate_placeholder(text: str, output_path: str) -> Dict:
    """Placeholder when edge-tts not available."""
    return {
        'success': False,
        'error': 'edge-tts not installed. Run: pip install edge-tts',
        'audio_path': None,
        'text': text
    }


def _clean_script(script: str) -> str:
    """Remove labels (HOOK:, PROBLEM:, etc.) from script."""
    import re
    # Remove section labels
    clean = re.sub(r'\b(HOOK|PROBLEM|SOLUTION|FEATURES|CTA):\s*', '', script)
    # Remove extra whitespace
    clean = re.sub(r'\n+', '. ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def get_available_voices() -> Dict:
    """Return available voice options."""
    return VOICES


# ===== Test =====
if __name__ == '__main__':
    test_script = {
        'full_script': 'HOOK: بتدور على حل؟ PROBLEM: تعبت من البحث. SOLUTION: ده الحل. FEATURES: جودة عالية. CTA: اطلب دلوقتي.'
    }
    
    print('Generating voiceover...')
    result = generate_voiceover(test_script, voice_gender='male', tone='egyptian')
    print(f'Result: {result}')
