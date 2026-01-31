import os
import requests
import textwrap
import json
import time
import io
from PIL import Image, ImageDraw, ImageFont, ImageOps

# --- CONFIGURATION ---
PIXABAY_KEY = os.getenv('PIXABAY_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN_MOTIVATION')
WEBHOOK_URL = os.getenv('WEBHOOK_MOTIVATION')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
HISTORY_FILE = "history.txt"
FIXED_AUTHOR = "- Lucas Hart"

def get_safe_font():
    """Gets a Professional Font (Uses System Font to avoid download errors)"""
    
    # Option 1: Linux System Font (Best for GitHub Actions)
    # DejaVuSans-Bold looks 99% like Arial/Roboto
    linux_font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if os.path.exists(linux_font):
        return ImageFont.truetype(linux_font, 60), ImageFont.truetype(linux_font, 40)
    
    # Option 2: Download Roboto (Backup for local run)
    font_path = "font.ttf"
    if not os.path.exists(font_path):
        try:
            url = "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Bold.ttf"
            r = requests.get(url, timeout=10)
            with open(font_path, "wb") as f: f.write(r.content)
        except: pass
    
    if os.path.exists(font_path):
        return ImageFont.truetype(font_path, 60), ImageFont.truetype(font_path, 40)

    # Option 3: Default (Only if everything fails)
    print("⚠️ Warning: Using ugly default font.")
    return ImageFont.load_default(), ImageFont.load_default()

def create_motivation_image():
    try:
        # 1. Get Quote
        print("1️⃣ Fetching Quote...")
        used_quotes = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f: used_quotes = f.read().splitlines()

        headers = {'User-Agent': 'Mozilla/5.0'}
        quote_text = "\"The only way to do great work is to love what you do.\""
        raw_q = "Default"

        for _ in range(3):
            try:
                res = requests.get("https://zenquotes.io/api/random", headers=headers, timeout=5).json()[0]
                if res['q'] not in used_quotes:
                    quote_text = f'"{res["q"]}"'
                    raw_q = res['q']
                    break
            except: continue

        # 2. Get Background
        print("2️⃣ Fetching Background...")
        final_img = None
        try:
            p_url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q=nature+dark+moody&image_type=photo&per_page=10"
            pix_data = requests.get(p_url, headers=headers, timeout=10).json()
            
            for hit in pix_data.get('hits', []):
                try:
                    # High Res Image Download
                    img_res = requests.get(hit['largeImageURL'], headers=headers, timeout=15)
                    img = Image.open(io.BytesIO(img_res.content))
                    img.verify()
                    
                    final_img = Image.open(io.BytesIO(img_res.content)).convert("RGB")
                    print(f"✅ Background Loaded: {hit['largeImageURL'][:30]}...")
                    break
                except: continue
        except: pass

        if not final_img:
            final_img = Image.new('RGB', (1080, 1350), color=(20, 20, 20))

        # 3. Processing (Smart Resize + Overlay)
        print("3️⃣ Resizing & Texting...")
        
        # Smart Crop to 1080x1350
        final_img = ImageOps.fit(final_img, (1080, 1350), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        
        # Dark Overlay
        overlay = Image.new('RGBA', final_img.size, (0, 0, 0, 120))
        final_img.paste(overlay, (0, 0), overlay)
        
        draw = ImageDraw.Draw(final_img)
        font_quote, font_author = get_safe_font()
        
        # Text Wrapping
        # 'FreeType' check ensures we use correct width calculation for TTF fonts
        wrap_width = 20 if "FreeType" in str(type(font_quote)) else 40
        lines = textwrap.wrap(quote_text, width=wrap_width)
        
        line_height = 85 if "FreeType" in str(type(font_quote)) else 20
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
        
        print("💾 Saving File...")
        final_img.save("post.jpg", optimize=True, quality=75)
        
        with open(HISTORY_FILE, "a") as f: f.write(raw_q + "\n")
        return "post.jpg"

    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def upload_with_retry(file_path):
    url = "https://catbox.moe/user/api.php"
    for attempt in range(1, 4):
        try:
            print(f"🚀 Uploading (Attempt {attempt})...")
            with open(file_path, 'rb') as f:
                r = requests.post(url, data={'reqtype': 'fileupload'}, files={'fileToUpload': f}, timeout=30 * attempt)
                if "http" in r.text: return r.text
        except Exception as e:
            print(f"⚠️ Fail: {e}")
            time.sleep(5)
    return None

def main():
    path = create_motivation_image()
    if not path: return

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
        print("❌ Upload failed.")

if __name__ == "__main__":
    main()
