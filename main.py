import os
import requests
import textwrap
import json
import time
import io
from PIL import Image, ImageDraw, ImageFont, ImageOps # ImageOps added for smart resizing

# --- CONFIGURATION ---
PIXABAY_KEY = os.getenv('PIXABAY_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN_MOTIVATION')
WEBHOOK_URL = os.getenv('WEBHOOK_MOTIVATION')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
HISTORY_FILE = "history.txt"
FIXED_AUTHOR = "- Lucas Hart"

def get_safe_font():
    """Download Font safely. Fallback to default if fails."""
    font_path = "font.ttf"
    try:
        if os.path.exists(font_path) and os.path.getsize(font_path) > 1000:
            return ImageFont.truetype(font_path, 55), ImageFont.truetype(font_path, 35)
        
        print("📥 Downloading Font...")
        # Using a reliable raw link
        url = "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Bold.ttf"
        r = requests.get(url, timeout=15)
        
        if r.status_code == 200 and len(r.content) > 1000:
            with open(font_path, "wb") as f: f.write(r.content)
            return ImageFont.truetype(font_path, 55), ImageFont.truetype(font_path, 35)
    except Exception as e:
        print(f"⚠️ Font Error: {e}. Using Default.")

    return ImageFont.load_default(), ImageFont.load_default()

def create_motivation_image():
    try:
        # STEP 1: Get Quote
        print("1️⃣ Fetching Quote...")
        used_quotes = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f: used_quotes = f.read().splitlines()

        headers = {'User-Agent': 'Mozilla/5.0'}
        quote_text = "\"Do what you can, with what you have, where you are.\"" 
        raw_q = "Default"

        for _ in range(3):
            try:
                res = requests.get("https://zenquotes.io/api/random", headers=headers, timeout=5).json()[0]
                if res['q'] not in used_quotes:
                    quote_text = f'"{res["q"]}"'
                    raw_q = res['q']
                    break
            except: continue

        # STEP 2: Get Background (Any Size)
        print("2️⃣ Fetching Background...")
        final_img = None
        
        try:
            # Using 'nature' + 'dark' to get good contrast images
            p_url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q=nature+dark+moody&image_type=photo&per_page=10"
            pix_data = requests.get(p_url, headers=headers, timeout=10).json()
            
            for hit in pix_data.get('hits', []):
                try:
                    # Downloading High Quality Image
                    img_res = requests.get(hit['largeImageURL'], headers=headers, timeout=15)
                    byte_data = io.BytesIO(img_res.content)
                    img = Image.open(byte_data)
                    img.verify() 
                    
                    byte_data.seek(0)
                    final_img = Image.open(byte_data).convert("RGB")
                    print(f"✅ Background Loaded: {hit['largeImageURL'][:30]}...")
                    break
                except: continue
        except Exception as e:
            print(f"⚠️ Pixabay Failed: {e}")

        # FALLBACK BACKGROUND
        if not final_img:
            print("⚠️ Using Fallback Background.")
            final_img = Image.new('RGB', (1080, 1350), color=(20, 20, 20))

        # STEP 3: Smart Resizing & Processing
        print("3️⃣ Resizing & Processing...")
        
        # 🔥 SMART RESIZE: Yeh image ko crop karke 1080x1350 mein fit karega bina stretch kiye
        final_img = ImageOps.fit(final_img, (1080, 1350), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        
        # Dark Overlay
        overlay = Image.new('RGBA', final_img.size, (0, 0, 0, 140))
        final_img.paste(overlay, (0, 0), overlay)
        
        draw = ImageDraw.Draw(final_img)
        font_quote, font_author = get_safe_font()
        
        # Text Wrapping
        wrap_width = 20 if "FreeType" in str(type(font_quote)) else 40
        lines = textwrap.wrap(quote_text, width=wrap_width)
        
        line_height = 80 if "FreeType" in str(type(font_quote)) else 20
        total_height = len(lines) * line_height
        y = (1350 - total_height) / 2

        for line in lines:
            try: w = draw.textbbox((0, 0), line, font=font_quote)[2]
            except: w = draw.textlength(line, font=font_quote)
            
            draw.text(((1080 - w) / 2, y), line, font=font_quote, fill="white")
            y += line_height
        
        y += 40
        try: w_auth = draw.textbbox((0, 0), FIXED_AUTHOR, font=font_author)[2]
        except: w_auth = draw.textlength(FIXED_AUTHOR, font=font_author)
        
        draw.text(((1080 - w_auth) / 2, y), FIXED_AUTHOR, font=font_author, fill="white")
        
        print("💾 Saving Optimized File...")
        # Quality 75 for smaller size (faster upload)
        final_img.save("post.jpg", optimize=True, quality=75)
        
        with open(HISTORY_FILE, "a") as f: f.write(raw_q + "\n")
        
        return "post.jpg"

    except Exception as e:
        print(f"❌ Processing Failed: {e}")
        return None

def upload_with_retry(file_path):
    """Retries upload 3 times if it fails"""
    url = "https://catbox.moe/user/api.php"
    
    # Retry Loop (3 Attempts)
    for attempt in range(1, 4):
        try:
            print(f"🚀 Uploading to Catbox (Attempt {attempt}/3)...")
            with open(file_path, 'rb') as f:
                # Increasing timeout with each attempt: 30s -> 60s -> 90s
                r = requests.post(url, data={'reqtype': 'fileupload'}, files={'fileToUpload': f}, timeout=30 * attempt)
                if "http" in r.text:
                    return r.text
        except Exception as e:
            print(f"⚠️ Attempt {attempt} failed: {e}")
            time.sleep(5) # Wait 5 seconds before retrying
            
    return None

def main():
    path = create_motivation_image()
    if not path: return

    # Upload using Retry Logic
    url = upload_with_retry(path)

    if url:
        print(f"✅ SUCCESS: {url}")
        caption = "💡 Daily Motivation. #Inspiration #LucasHart"
        
        if TELEGRAM_TOKEN and CHAT_ID:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", 
                         json={"chat_id": CHAT_ID, "photo": url, "caption": caption})
        
        if WEBHOOK_URL:
            requests.post(WEBHOOK_URL, json={"content": f"{caption}\n{url}"})
    else:
        print("❌ All upload attempts failed.")

if __name__ == "__main__":
    main()
