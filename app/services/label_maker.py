import qrcode
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import datetime

def generate_label(data):
    """
    Generates a 4x6 inch label (1200x1800 px @ 300 DPI).
    data dict expected:
    {
        "name": "Batch Name",
        "style": "Batch Notes / Style",
        "abv": "5.5",
        "og": "1.050",
        "fg": "1.010",
        "date": "2023-10-27"
    }
    """
    # Canvas Setup (4x6 @ 300 DPI)
    WIDTH, HEIGHT = 1200, 1800
    bg_color = (10, 10, 10) # Almost black
    text_color = (255, 255, 255)
    accent_color = (245, 158, 11) # Amber-500

    img = Image.new('RGB', (WIDTH, HEIGHT), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Fonts (Using default for now, could load custom TTF if available)
    # Since we can't easily rely on system fonts in container, we use load_default 
    # but scale it up strictly? No, Pilot default font is tiny.
    # We will try to load a standard font if possible, else fallback is tricky.
    # For Docker, typically /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf exists if installed.
    # Let's try basic load, else default.
    try:
        font_header = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
        font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 60)
        font_detail = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
    except:
        # Fallback for dev/mac without specific font paths, using default (will be small)
        # In a real app we'd ship a font file. For now, rely on PIL default which is readable but small.
        # Check if we can use a "better" default logic? 
        # Actually, let's just use default and warn user, OR download one in Dockerfile.
        # For this step, I'll assume we might fail gracefuly to default.
        font_header = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_detail = ImageFont.load_default()

    # 1. Header (Batch Name)
    draw.text((100, 200), str(data.get('name', 'Unknown Batch')), fill=text_color, font=font_header, anchor="ls")

    # 2. Key Stats (ABV)
    draw.text((100, 400), "ABV", fill=accent_color, font=font_detail)
    draw.text((100, 500), f"{data.get('abv', '--')}%", fill=text_color, font=font_header)

    # 3. Details (OG / FG / Date)
    y_start = 700
    spacing = 100
    draw.text((100, y_start), f"OG: {data.get('og', '--')}", fill=text_color, font=font_sub)
    draw.text((100, y_start + spacing), f"FG: {data.get('fg', '--')}", fill=text_color, font=font_sub)
    draw.text((100, y_start + spacing*2), f"Brewed: {data.get('date', '--')}", fill=text_color, font=font_sub)

    # 4. QR Code (Notes)
    qr_data = data.get('style') or f"Brew Brain Batch: {data.get('name')}"
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # Resize QR to fit nicely at bottom
    qr_size = 600
    qr_img = qr_img.resize((qr_size, qr_size))
    
    # Paste QR centered horizontally at bottom
    qr_x = (WIDTH - qr_size) // 2
    qr_y = HEIGHT - qr_size - 100
    img.paste(qr_img, (qr_x, qr_y))

    # Save to Bytes
    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)
    return output
