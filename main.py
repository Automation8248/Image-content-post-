import os
import requests
import textwrap
import time
from PIL import Image, ImageDraw, ImageFont

# --- CONFIGURATION ---
PIXABAY_KEY = os.getenv('PIXABAY_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN_MOTIVATION')
WEBHOOK_URL = os.getenv('WEBHOOK_MOTIVATION')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
HISTORY_FILE = "history.txt"
FIXED_AUTHOR = "- Lucas Hart"

def get_font():
    """Download Font"""
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

        # 2. Get Quote
        quote_text = ""
        raw_q = ""
        # Browser Headers to bypass Pixabay Block
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://pixabay.com/'
        }

        for _ in range(5):
            try:
                res = requests.get("https://zenquotes.io/api/random", headers=headers, timeout=10).json()[0]
                if res['q'] not in used_quotes:
                    quote_text = f'"{res["q"]}"'
                    raw_q = res['q']
                    break
            except: continue
        
        if not quote_text: 
            quote_text = "\"The only way to do great work is to love what you do.\""
            raw_q = "Default"

        # 3. Get Background (Fixed Logic)
        print("🔍 Searching Pixabay...")
        p_url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q=nature+dark+forest&orientation=vertical&image_type=photo&per_page=10"
        pix_resp = requests.get(p_url, headers=headers, timeout=10)
        pix_data = pix_resp.json()
        
        final_img = None
        
        # Try multiple images if one fails
        for hit in pix_data.get('hits', []):
            try:
                img_url = hit['webformatURL']
                # Download to Disk (Safer than Memory)
                img_res = requests.get(img_url, headers=headers, timeout=15)
                
                with open("temp_bg.jpg", "wb") as f:
                    f.write(img_res.content)
                
                # Check File Size (Avoid empty/corrupt files)
                if os.path.getsize("temp_bg.jpg") < 1000: # Less than 1KB means error page
                    continue

                # Verify Image
                try:
                    test_img = Image.open("temp_bg.jpg")
                    test_img.verify() # Check content
                    final_img = Image.open("temp_bg.jpg").convert("RGB") # Re-open for use
                    print(f"✅ Image loaded: {img_url}")
                    break
                except:
                    print("⚠️ Invalid image format, trying next...")
                    continue

            except Exception as e:
                print(f"⚠️ Download error: {e}")
                continue

        if not final_img: 
            print("❌ All images failed.")
            return None
        
        # 4. Processing (Resize & Merge)
        final_img = final_img.resize((1080, 1350), Image.Resampling.LANCZOS)
        
        overlay = Image.new('RGBA', final_img.size, (0, 0, 0, 150))
        final_img.paste(overlay, (0, 0), overlay)
        
        draw, font_p = ImageDraw.Draw(final_img), get_font()
        f_quote = ImageFont.truetype(font_p, 55) if font_p else ImageFont.load_default()
        f_author = ImageFont.truetype(font_p, 35) if font_p else ImageFont.load_default()
        
        # Draw Text
        lines = textwrap.wrap(quote_text, width=22)
        y = (1350 - (len(lines) * 75)) / 2
        for line in lines:
            w = draw.textbbox((0, 0), line, font=f_quote)[2]
            draw.text(((1080 - w) / 2, y), line, font=f_quote, fill="white")
            y += 75
        
        y += 30
        w_auth = draw.textbbox((0, 0), FIXED_AUTHOR, font=f_author)[2]
        draw.text(((1080 - w_auth) / 2, y), FIXED_AUTHOR, font=f_author, fill="white")
        
        final_img.save("post.jpg", optimize=True, quality=85)
        
        # History Save
        with open(HISTORY_FILE, "a") as f: f.write(raw_q + "\n")
        
        return "post.jpg"

    except Exception as e:
        print(f"❌ Fatal Error: {e}")
        return None

def main():
    path = create_motivation_image()
    if not path: return

    # Catbox Upload
    url = None
    try:
        print("🚀 Uploading...")
        with open(path, 'rb') as f:
            r = requests.post("https://catbox.moe/user/api.php", 
                            data={'reqtype': 'fileupload'}, 
                            files={'fileToUpload': f}, timeout=30)
            if "http" in r.text: url = r.text
    except Exception as e: print(f"⚠️ Upload Error: {e}")

    if url:
        print(f"✅ Success: {url}")
        caption = "💡 Daily Motivation. #Inspiration #LucasHart"
        
        if TELEGRAM_TOKEN and CHAT_ID:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", 
                         json={"chat_id": CHAT_ID, "photo": url, "caption": caption})
        
        if WEBHOOK_URL:
            requests.post(WEBHOOK_URL, json={"content": f"{caption}\n{url}"})

if __name__ == "__main__":
    main()
