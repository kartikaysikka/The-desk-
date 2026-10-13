import io
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

FONT_DIR = Path(__file__).parent / "fonts"
W, H = 1080, 1350
PAD = 72


def anton(size):
    return ImageFont.truetype(str(FONT_DIR / "Anton-Regular.ttf"), size)


def franklin(size, weight=b"Regular"):
    f = ImageFont.truetype(str(FONT_DIR / "LibreFranklin.ttf"), size)
    f.set_variation_by_name(weight)
    return f


def wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for word in text.split():
        test = f"{cur} {word}".strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_text(draw, text, font_fn, max_w, max_lines, start, end):
    for size in range(start, end - 1, -4):
        font = font_fn(size)
        lines = wrap(draw, text, font, max_w)
        if len(lines) <= max_lines:
            return font, lines, size
    font = font_fn(end)
    return font, wrap(draw, text, font, max_w)[:max_lines], end


def cover_crop(img_bytes, w, h):
    img = Image.open(io.BytesIO(img_bytes))
    img = ImageOps.exif_transpose(img).convert("RGB")
    return ImageOps.fit(img, (w, h), Image.LANCZOS, centering=(0.5, 0.4))


def gradient(w, h, start_y, max_alpha=240):
    g = Image.new("L", (1, h), 0)
    for y in range(h):
        if y >= start_y:
            g.putpixel((0, y), int(max_alpha * min(1, ((y - start_y) / (h - start_y)) ** 0.8)))
    return g.resize((w, h))


def to_jpeg(img):
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=92)
    return buf.getvalue()


LOGO = Image.open(FONT_DIR / "ani_logo.png").convert("RGBA")
RED = (226, 27, 35)


def oswald(size, weight=b"Bold"):
    f = ImageFont.truetype(str(FONT_DIR / "Oswald.ttf"), size)
    f.set_variation_by_name(weight)
    return f


def paste_logo(img, width, right, top):
    lg = LOGO.resize((width, int(LOGO.height * width / LOGO.width)), Image.LANCZOS)
    img.paste(lg, (img.width - right - width, top), lg)


# ---------- Black And White Informative (1080x1350) ----------
def bw_footer(d, brand, right_text, right_fill):
    d.line([PAD, H - 108, W - PAD, H - 108], fill=(110, 110, 110) if right_fill != "white" else "white", width=2)
    sf = franklin(26, b"Bold")
    d.text((PAD, H - 88), brand.upper(), font=sf, fill="white")
    d.text((W - PAD - d.textlength(right_text, font=sf), H - 88), right_text, font=sf, fill=right_fill)


def bw_cover(photo, headline, kicker, brand, date_str):
    img = cover_crop(photo, W, H)
    img = Image.composite(Image.new("RGB", (W, H), "black"), img, gradient(W, H, 480))
    paste_logo(img, 150, PAD - 10, PAD - 20)
    d = ImageDraw.Draw(img)
    df = franklin(28, b"SemiBold")
    d.text((PAD, PAD + 16), date_str, font=df, fill="white")

    font, lines, size = fit_text(d, headline.upper(), anton, W - 2 * PAD, 5, 112, 64)
    lh = int(size * 1.12)
    y = H - 150 - lh * len(lines)
    if kicker:
        kf = franklin(30, b"Black")
        k = kicker.upper()
        kw = d.textlength(k, font=kf)
        d.rectangle([PAD, y - 78, PAD + kw + 32, y - 26], fill="white")
        d.text((PAD + 16, y - 72), k, font=kf, fill="black")
    for i, line in enumerate(lines):
        d.text((PAD, y + i * lh), line, font=font, fill="white")
    bw_footer(d, brand, "SWIPE FOR MORE  >>", "white")
    return to_jpeg(img)


def bw_detail(photo, title, body, brand, idx, total):
    img = Image.new("RGB", (W, H), "black")
    ph_h = 620
    img.paste(cover_crop(photo, W, ph_h), (0, 0))
    paste_logo(img, 150, PAD - 10, PAD - 20)
    d = ImageDraw.Draw(img)
    d.rectangle([0, ph_h, W, ph_h + 10], fill="white")
    d.text((PAD, ph_h + 56), f"{idx:02d} / {total:02d}", font=franklin(28, b"Bold"), fill="white")
    tf, tlines, tsize = fit_text(d, title.upper(), anton, W - 2 * PAD, 3, 76, 52)
    y = ph_h + 110
    for line in tlines:
        d.text((PAD, y), line, font=tf, fill="white")
        y += int(tsize * 1.15)
    y += 24
    space = H - 130 - y
    for size in range(40, 25, -2):
        bf = franklin(size, b"Regular")
        blines = wrap(d, body, bf, W - 2 * PAD)
        if len(blines) * size * 1.45 <= space:
            break
    for line in blines:
        if y + size > H - 130:
            break
        d.text((PAD, y), line, font=bf, fill=(220, 220, 220))
        y += int(size * 1.45)
    bw_footer(d, brand, "", (160, 160, 160))
    return to_jpeg(img)


# ---------- Standard (1080x1080, photo top + dark panel) ----------
SW, SH, PH = 1080, 1080, 710


def dark_panel(w, h):
    noise = Image.effect_noise((w, h), 18).point(lambda v: 12 + v // 10)
    return Image.merge("RGB", (noise, noise, noise))


def std_slide(photo, text, chevrons, max_lines, start, end):
    img = Image.new("RGB", (SW, SH), "black")
    img.paste(cover_crop(photo, SW, PH), (0, 0))
    img.paste(dark_panel(SW, SH - PH), (0, PH))
    paste_logo(img, 130, 40, 36)
    d = ImageDraw.Draw(img)
    d.line([0, PH, SW, PH], fill=(60, 60, 60), width=2)

    font, lines, size = fit_text(d, text.upper(), oswald, SW - 160, 2, 84, 56)
    if len(wrap(d, text.upper(), font, SW - 160)) > 2:
        font, lines, size = fit_text(d, text.upper(), oswald, SW - 160, max_lines, 54, 40)
    lh = int(size * 1.2)
    block = lh * len(lines)
    chev_h = 56 if chevrons else 0
    top = PH + max(28, (SH - PH - 30 - block - chev_h) // 2 - 6)
    d.rectangle([SW // 2 - 240, top, SW // 2 + 240, top + 5], fill=RED)
    y = top + 30
    for line in lines:
        d.text(((SW - d.textlength(line, font=font)) // 2, y), line, font=font, fill="white")
        y += lh
    if chevrons:
        cy, cx = y + 14, SW // 2 - 56
        for i in range(3):
            x = cx + i * 48
            d.line([(x, cy), (x + 16, cy + 16), (x, cy + 32)], fill=RED, width=9, joint="curve")
    return to_jpeg(img)


def std_cover(photo, headline, kicker, brand, date_str):
    return std_slide(photo, headline, True, 3, 0, 0)


def std_detail(photo, title, body, brand, idx, total):
    return std_slide(photo, title, idx < total, 3, 0, 0)


TEMPLATES = {
    "bw_informative": {"name": "Black And White Informative", "cover": bw_cover, "detail": bw_detail},
    "standard": {"name": "Standard", "cover": std_cover, "detail": std_detail},
}

