import os
import requests
import textwrap
import json
from PIL import Image, ImageDraw, ImageFont

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
    """History check aur unique quote generation logic"""
    try:
        # 1. History Load karo (Unique IDs ki list)
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                used_quotes = f.read().splitlines()
        else:
            used_quotes = []

        # 2. Unique Quote dhoondo
        quote_data = None
        for _ in range(5): # 5 baar koshish karega naya dhoondne ki
            res = requests.get("https://zenquotes.io/api/random", timeout=5).json()[0]
            if res['q'] not in used_quotes: # Content matching
                quote_data = res
                break
        
        if not quote_data: return None

        quote_text = f'"{quote_data["q"]}"'
        author_text = "- Lucas Hart"

        # 3. Pixabay Background
        p_url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q=nature+dark+landscape&orientation=vertical&per_page=5"
        pix_data = requests.get(p_url, timeout=5).json()
        bg_url = pix_data['hits'][0]['webformatURL']
        
        with open("bg.jpg", "wb") as f: 
            f.write(requests.get(bg_url, timeout=10).content)
        
        # 4. Image Processing (1080x1350)
        img = Image.open("bg.jpg").convert("RGB").resize((1080, 1350))
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 140))
        img.paste(overlay, (0, 0), overlay)
        
        draw, font_p = ImageDraw.Draw(img), get_font()
        f_quote = ImageFont.truetype(font_p, 55) if font_p else ImageFont.load_default()
        f_author = ImageFont.truetype(font_p, 35) if font_p else ImageFont.load_default()
        
        lines = textwrap.wrap(quote_text, width=22)
        y = (1350 - (len(lines) * 75)) / 2
        for line in lines:
            w = draw.textbbox((0, 0), line, font=f_quote)[2]
            draw.text(((1080 - w) / 2, y), line, font=f_quote, fill="white")
            y += 75
        
        y += 30
        w_author = draw.textbbox((0, 0), author_text, font=f_author)[2]
        draw.text(((1080 - w_author) / 2, y), author_text, font=f_author, fill="white")
        
        img.save("post.jpg", optimize=True, quality=85)

        # 5. History Update (Naya quote text save karo)
        with open(HISTORY_FILE, "a") as f:
            f.write(quote_data['q'] + "\n")
            
        return "post.jpg"
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def upload_and_send():
    path = create_motivation_image()
    if not path: return

    try:
        with open(path, 'rb') as f:
            r = requests.post("https://catbox.moe/user/api.php", 
                            data={'reqtype': 'fileupload'}, 
                            files={'fileToUpload': f}, timeout=25)
        url = r.text if "http" in r.text else None
    except: url = None

    if url:
        caption = "💡 Daily Wisdom. #Motivation #LucasHart #Inspiration"
        if TELEGRAM_TOKEN and CHAT_ID:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", 
                         json={"chat_id": CHAT_ID, "photo": url, "caption": caption}, timeout=10)
        if WEBHOOK_URL:
            requests.post(WEBHOOK_URL, json={"content": f"{caption}\n{url}"}, timeout=5)
    else:
        print("⚠️ Upload failed.")

if __name__ == "__main__":
    upload_and_send()
