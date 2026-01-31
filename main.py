import os
import requests
import textwrap
import json
import time
from PIL import Image, ImageDraw, ImageFont
import io

# --- CONFIGURATION ---
PIXABAY_KEY = os.getenv('PIXABAY_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN_MOTIVATION')
WEBHOOK_URL = os.getenv('WEBHOOK_MOTIVATION')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
HISTORY_FILE = "history.txt"

def get_font():
    font_path = "font.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Bold.ttf"
        try:
            r = requests.get(url, timeout=5)
            with open(font_path, "wb") as f: f.write(r.content)
        except: return None
    return font_path

def create_motivation_image():
    try:
        # 1. History Check
        used_quotes = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f: used_quotes = f.read().splitlines()

        # 2. Get Unique Quote
        quote_data = None
        for _ in range(5):
            res = requests.get("https://zenquotes.io/api/random", timeout=5).json()[0]
            if res['q'] not in used_quotes:
                quote_data = res
                break
        if not quote_data: return None

        # 3. Get Valid Background (Fix for "Unknown File Format")
        p_url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q=nature+dark&orientation=vertical&image_type=photo&per_page=15"
        pix_data = requests.get(p_url, timeout=5).json()
        
        final_img = None
        for hit in pix_data['hits']:
            try:
                img_url = hit['webformatURL']
                img_res = requests.get(img_url, timeout=10)
                # Pillow se check karein ki image sahi hai ya nahi
                test_img = Image.open(io.BytesIO(img_res.content))
                test_img.verify() # Format check
                final_img = Image.open(io.BytesIO(img_res.content)).convert("RGB")
                break # Agar sahi image mil gayi toh loop se bahar
            except:
                continue # Agar error aaye toh agli image try karein

        if not final_img: return None
        
        # 4. Image Processing (1080x1350)
        final_img = final_img.resize((1080, 1350), Image.Resampling.LANCZOS)
        overlay = Image.new('RGBA', final_img.size, (0, 0, 0, 150))
        final_img.paste(overlay, (0, 0), overlay)
        
        draw, font_p = ImageDraw.Draw(final_img), get_font()
        f_quote = ImageFont.truetype(font_p, 55) if font_p else ImageFont.load_default()
        
        lines = textwrap.wrap(f'"{quote_data["q"]}"', width=22)
        y = (1350 - (len(lines) * 75)) / 2
        for line in lines:
            w = draw.textbbox((0, 0), line, font=f_quote)[2]
            draw.text(((1080 - w) / 2, y), line, font=f_quote, fill="white")
            y += 75
        
        f_author = ImageFont.truetype(font_p, 35) if font_p else ImageFont.load_default()
        w_auth = draw.textbbox((0, 0), "- Lucas Hart", font=f_author)[2]
        draw.text(((1080 - w_auth) / 2, y + 30), "- Lucas Hart", font=f_author, fill="white")
        
        final_img.save("post.jpg", optimize=True, quality=80)

        with open(HISTORY_FILE, "a") as f: f.write(quote_data['q'] + "\n")
        return "post.jpg"
    except Exception as e:
        print(f"❌ Error logic: {e}")
        return None

def main():
    path = create_motivation_image()
    if not path:
        print("❌ Could not create image (Format/Network Error)")
        return

    url = None
    for _ in range(2):
        try:
            with open(path, 'rb') as f:
                r = requests.post("https://catbox.moe/user/api.php", data={'reqtype': 'fileupload'}, files={'fileToUpload': f}, timeout=20)
                if "http" in r.text:
                    url = r.text
                    break
        except: time.sleep(2)

    if url:
        print(f"✅ Posted: {url}")
        cap = "💡 Daily Wisdom. #Motivation #LucasHart"
        if TELEGRAM_TOKEN and CHAT_ID:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", json={"chat_id": CHAT_ID, "photo": url, "caption": cap}, timeout=10)
        if WEBHOOK_URL:
            requests.post(WEBHOOK_URL, json={"content": f"{cap}\n{url}"}, timeout=5)

if __name__ == "__main__":
    main()
