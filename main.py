import os
import requests
import textwrap
import json
import time
import io
from PIL import Image, ImageDraw, ImageFont

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
        # Check if already exists and valid size
        if os.path.exists(font_path) and os.path.getsize(font_path) > 1000:
            return ImageFont.truetype(font_path, 55), ImageFont.truetype(font_path, 35)
        
        print("📥 Downloading Font...")
        # Using a reliable raw link
        url = "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Bold.ttf"
        r = requests.get(url, timeout=10)
        
        if r.status_code == 200 and len(r.content) > 1000:
            with open(font_path, "wb") as f: f.write(r.content)
            return ImageFont.truetype(font_path, 55), ImageFont.truetype(font_path, 35)
        else:
            print("⚠️ Font download failed (Size/Status mismatch). Using Default.")
    except Exception as e:
        print(f"⚠️ Font Error: {e}. Using Default.")

    # FALLBACK: Use Default Font if anything fails
    return ImageFont.load_default(), ImageFont.load_default()

def create_motivation_image():
    try:
        # STEP 1: Get Quote
        print("1️⃣ Fetching Quote...")
        used_quotes = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f: used_quotes = f.read().splitlines()

        headers = {'User-Agent': 'Mozilla/5.0'}
        quote_text = "\"Do what you can, with what you have, where you are.\"" # Default
        raw_q = "Default"

        for _ in range(3):
            try:
                res = requests.get("https://zenquotes.io/api/random", headers=headers, timeout=5).json()[0]
                if res['q'] not in used_quotes:
                    quote_text = f'"{res["q"]}"'
                    raw_q = res['q']
                    break
            except: continue

        # STEP 2: Get Background
        print("2️⃣ Fetching Background...")
        final_img = None
        
        try:
            p_url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q=nature+dark+mountain&orientation=vertical&image_type=photo&per_page=10"
            pix_data = requests.get(p_url, headers=headers, timeout=10).json()
            
            for hit in pix_data.get('hits', []):
                try:
                    img_res = requests.get(hit['webformatURL'], headers=headers, timeout=10)
                    # Load from memory
                    byte_data = io.BytesIO(img_res.content)
                    img = Image.open(byte_data)
                    img.verify() # Check integrity
                    
                    # Re-open for processing
                    byte_data.seek(0)
                    final_img = Image.open(byte_data).convert("RGB")
                    print(f"✅ Background Loaded: {hit['webformatURL'][:30]}...")
                    break
                except: continue
        except Exception as e:
            print(f"⚠️ Pixabay Failed: {e}")

        # FALLBACK BACKGROUND (Solid Color)
        if not final_img:
            print("⚠️ Using Fallback Black Background.")
            final_img = Image.new('RGB', (1080, 1350), color=(20, 20, 20))

        # STEP 3: Processing
        print("3️⃣ Processing Image...")
        # Resize safely
        final_img = final_img.resize((1080, 1350), Image.Resampling.LANCZOS)
        
        # Overlay
        overlay = Image.new('RGBA', final_img.size, (0, 0, 0, 140))
        final_img.paste(overlay, (0, 0), overlay)
        
        draw = ImageDraw.Draw(final_img)
        
        # Load Safe Fonts
        font_quote, font_author = get_safe_font()
        
        # Text Wrapping Logic
        # Adjust char width based on font type (Default font is smaller)
        wrap_width = 22 if "FreeType" in str(type(font_quote)) else 40
        
        lines = textwrap.wrap(quote_text, width=wrap_width)
        # Calculate text block height
        line_height = 75 if "FreeType" in str(type(font_quote)) else 20
        total_height = len(lines) * line_height
        y = (1350 - total_height) / 2

        for line in lines:
            # textbbox/textsize check
            try:
                w = draw.textbbox((0, 0), line, font=font_quote)[2]
            except: w = draw.textlength(line, font=font_quote)
            
            draw.text(((1080 - w) / 2, y), line, font=font_quote, fill="white")
            y += line_height
        
        # Author
        y += 30
        try:
            w_auth = draw.textbbox((0, 0), FIXED_AUTHOR, font=font_author)[2]
        except: w_auth = draw.textlength(FIXED_AUTHOR, font=font_author)
        
        draw.text(((1080 - w_auth) / 2, y), FIXED_AUTHOR, font=font_author, fill="white")
        
        # Save
        print("💾 Saving File...")
        final_img.save("post.jpg", optimize=True, quality=85)
        
        # Update History
        with open(HISTORY_FILE, "a") as f: f.write(raw_q + "\n")
        
        return "post.jpg"

    except Exception as e:
        print(f"❌ FATAL ERROR IN SCRIPT: {e}")
        import traceback
        traceback.print_exc() # Print details for debugging
        return None

def main():
    path = create_motivation_image()
    if not path: return

    # Catbox Upload
    url = None
    try:
        print("🚀 Uploading to Catbox...")
        with open(path, 'rb') as f:
            r = requests.post("https://catbox.moe/user/api.php", 
                            data={'reqtype': 'fileupload'}, 
                            files={'fileToUpload': f}, timeout=30)
            if "http" in r.text: url = r.text
    except Exception as e: print(f"⚠️ Upload Error: {e}")

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
