"""
=================================================================
Link2Reel (مرصاد) - Video Builder Engine
Assembles product images + voiceover + captions into vertical video (9:16)
Ownership: Smart Analyst | MIA8444
=================================================================
"""

import os
from typing import Dict, List, Optional
from urllib.parse import urlparse

# Fix PIL compatibility (Image.ANTIALIAS removed in Pillow 10+)
try:
    from PIL import Image
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = Image.LANCZOS
except ImportError:
    pass

# Try imports
try:
    from moviepy.editor import (ImageClip, AudioFileClip, concatenate_videoclips, 
                                 CompositeVideoClip, TextClip, ColorClip)
    from moviepy.editor import vfx
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False

try:
    from PIL import Image
    import requests
    from io import BytesIO
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ===== Config =====
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 24
BG_COLOR = (15, 30, 61)  # Navy blue
ACCENT_COLOR = (212, 169, 55)  # Gold
WHITE = (255, 255, 255)


def build_video(product_data: Dict, script_data: Dict, audio_path: str, 
                output_path: str = 'output_video.mp4') -> Dict:
    """
    Build the final vertical video.
    
    Args:
        product_data: Dict from scraper.py
        script_data: Dict from script_generator.py
        audio_path: Path to voiceover audio
        output_path: Path to save video
    
    Returns:
        Dict with: success, video_path, duration, error
    """
    if not MOVIEPY_AVAILABLE:
        return {
            'success': False,
            'error': 'moviepy not installed. Run: pip install moviepy',
            'video_path': None
        }
    
    if not os.path.exists(audio_path):
        return {
            'success': False,
            'error': f'Audio file not found: {audio_path}',
            'video_path': None
        }
    
    try:
        # Load audio to get duration
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        # Download and prepare product images
        image_paths = _download_images(product_data.get('images', []))
        
        # Build video clips
        if image_paths:
            video_clip = _build_image_sequence(image_paths, duration)
        else:
            video_clip = _build_text_background(product_data, duration)
        
        # Add audio
        final = video_clip.set_audio(audio_clip)
        
        # Export
        final.write_videofile(
            output_path,
            fps=FPS,
            codec='libx264',
            audio_codec='aac',
            verbose=False,
            logger=None,
            temp_audiofile='temp_audio.mp4'
        )
        
        # Cleanup
        audio_clip.close()
        final.close()
        _cleanup_images(image_paths)
        
        return {
            'success': True,
            'video_path': output_path,
            'duration': round(duration, 1),
            'size': os.path.getsize(output_path),
            'error': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Video build error: {str(e)}',
            'video_path': None
        }


def _download_images(urls: List[str]) -> List[str]:
    """Download product images to temp files."""
    if not PIL_AVAILABLE:
        return []
    
    paths = []
    for i, url in enumerate(urls[:5]):
        try:
            response = requests.get(url, timeout=10)
            img = Image.open(BytesIO(response.content))
            
            # Resize to fit 9:16 (crop center)
            img = _resize_to_vertical(img)
            
            path = f'temp_img_{i}.jpg'
            img.save(path, 'JPEG', quality=90)
            paths.append(path)
        except Exception as e:
            print(f'Failed to download image {i}: {e}')
    
    return paths


def _resize_to_vertical(img: Image) -> Image:
    """Resize image to fit 9:16 vertical (1080x1920)."""
    # Target dimensions
    target_w, target_h = VIDEO_WIDTH, VIDEO_HEIGHT
    target_ratio = target_w / target_h
    
    # Current dimensions
    w, h = img.size
    current_ratio = w / h
    
    # Crop to target ratio (center crop)
    if current_ratio > target_ratio:
        # Too wide, crop width
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    else:
        # Too tall, crop height
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))
    
    # Resize to exact dimensions
    img = img.resize((target_w, target_h), Image.LANCZOS)
    return img


def _build_image_sequence(image_paths: List[str], duration: float) -> CompositeVideoClip:
    """Build video from sequence of images with transitions."""
    if not image_paths:
        return _build_text_background({'title': ''}, duration)
    
    # Each image shows for equal time
    seg_duration = duration / len(image_paths)
    
    clips = []
    for i, path in enumerate(image_paths):
        clip = ImageClip(path).set_duration(seg_duration)
        
        # Add subtle zoom effect (Ken Burns)
        clip = clip.resize(lambda t: 1 + 0.05 * (t / seg_duration))
        clip = clip.set_position('center')
        
        # Transition fade
        if i > 0:
            clip = clip.crossfadein(0.5)
        
        clips.append(clip)
    
    return concatenate_videoclips(clips, method='compose')


def _build_text_background(product_data: Dict, duration: float) -> CompositeVideoClip:
    """Build video with text on solid background (no images)."""
    # Solid background
    bg = ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=BG_COLOR, duration=duration)
    
    # Title text
    title = product_data.get('title', 'Product')
    try:
        txt_clip = TextClip(
            title,
            fontsize=48,
            color=WHITE,
            font='Arial',
            method='caption',
            size=(VIDEO_WIDTH - 100, None)
        ).set_duration(duration).set_position('center')
        
        return CompositeVideoClip([bg, txt_clip])
    except Exception:
        return bg


def _cleanup_images(paths: List[str]):
    """Remove temporary image files."""
    for path in paths:
        try:
            os.remove(path)
        except:
            pass


def get_video_info(video_path: str) -> Dict:
    """Get video file info."""
    if not os.path.exists(video_path):
        return {'exists': False}
    
    return {
        'exists': True,
        'size': os.path.getsize(video_path),
        'path': video_path
    }


# ===== Test =====
if __name__ == '__main__':
    test_product = {
        'title': 'Test Product',
        'images': []
    }
    test_script = {'full_script': 'Test'}
    
    print('Video builder ready.')
    print(f'Output: {VIDEO_WIDTH}x{VIDEO_HEIGHT} @ {FPS}fps')
