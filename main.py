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

def get_font():
    """Download Arial-style font"""
    font_path = "font.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Bold.ttf"
        try:
            r = requests.get(url, timeout=10)
            with open(font_path, "wb") as f: f.write(r.content)
        except: return None
    return font_path

def create_motivation_image():
    try:
        # 1. History Check
        used_quotes = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f: used_quotes = f.read().splitlines()

        # 2. Get Unique Quote (ZenQuotes)
        quote_text = ""
        raw_q = ""
        # Browser jaisa header taaki block na ho
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

        for _ in range(5):
            try:
                res = requests.get("https://zenquotes.io/api/random", headers=headers, timeout=10).json()[0]
                if res['q'] not in used_quotes:
                    quote_text = f'"{res["q"]}"'
                    raw_q = res['q']
                    break
            except: continue
            
        if not quote_text: 
            print("⚠️ Quote fetch failed, using default.")
            quote_text = "\"The only way to do great work is to love what you do.\""
            raw_q = "Default Quote"

        # 3. Get Valid Background from Pixabay (Fix for Blocked Requests)
        print("🔍 Searching Pixabay...")
        p_url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q=nature+dark+forest&orientation=vertical&image_type=photo&per_page=15"
        pix_resp = requests.get(p_url, headers=headers, timeout=10)
        
        if pix_resp.status_code != 200:
            print(f"❌ Pixabay Error: {pix_resp.status_code}")
            return None

        pix_data = pix_resp.json()
        final_img = None
        
        for hit in pix_data.get('hits', []):
            try:
                img_url = hit['webformatURL']
                # Request with Headers to prevent 403 Forbidden
                img_res = requests.get(img_url, headers=headers, stream=True, timeout=15)
                
                # Check if we actually got an image
                if img_res.status_code == 200 and 'image' in img_res.headers.get('Content-Type', ''):
                    byte_data = io.BytesIO(img_res.content)
                    test_img = Image.open(byte_data)
                    test_img.verify() # Check corruption
                    
                    # Re-open for processing
                    byte_data.seek(0)
                    final_img = Image.open(byte_data).convert("RGB")
                    print(f"✅ Image downloaded: {img_url}")
                    break
                else:
                    print(f"⚠️ Skipped non-image response: {img_url}")
            except Exception as e:
                print(f"⚠️ Image skip error: {e}")
                continue

        if not final_img: 
            print("❌ No valid image found after checking multiple.")
            return None
        
        # 4. Processing (Resize & Merge)
        final_img = final_img.resize((1080, 1350), Image.Resampling.LANCZOS)
        
        # Overlay
        overlay = Image.new('RGBA', final_img.size, (0, 0, 0, 150))
        final_img.paste(overlay, (0, 0), overlay)
        
        draw, font_p = ImageDraw.Draw(final_img), get_font()
        f_quote = ImageFont.truetype(font_p, 55) if font_p else ImageFont.load_default()
        f_author = ImageFont.truetype(font_p, 35) if font_p else ImageFont.load_default()
        
        # Draw Quote
        lines = textwrap.wrap(quote_text, width=22)
        y = (1350 - (len(lines) * 75)) / 2
        for line in lines:
            w = draw.textbbox((0, 0), line, font=f_quote)[2]
            draw.text(((1080 - w) / 2, y), line, font=f_quote, fill="white")
            y += 75
        
        # Draw Author
        y += 30
        w_auth = draw.textbbox((0, 0), FIXED_AUTHOR, font=f_author)[2]
        draw.text(((1080 - w_auth) / 2, y), FIXED_AUTHOR, font=f_author, fill="white")
        
        final_img.save("post.jpg", optimize=True, quality=85)
        
        # Update History
        with open(HISTORY_FILE, "a") as f: f.write(raw_q + "\n")
        
        return "post.jpg"

    except Exception as e:
        print(f"❌ Fatal Error: {e}")
        return None

def main():
    path = create_motivation_image()
    if not path:
        print("❌ Script aborted due to image generation failure.")
        return

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
        print(f"✅ Success! URL: {url}")
        caption = "💡 Daily Motivation. #Inspiration #LucasHart"
        
        if TELEGRAM_TOKEN and CHAT_ID:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", 
                         json={"chat_id": CHAT_ID, "photo": url, "caption": caption})
        
        if WEBHOOK_URL:
            requests.post(WEBHOOK_URL, json={"content": f"{caption}\n{url}"})
    else:
        print("❌ Upload failed, no URL returned.")

if __name__ == "__main__":
    main()
