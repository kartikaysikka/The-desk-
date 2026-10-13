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


def brand_tag(draw, x, y, name):
    f = anton(38)
    tw = draw.textlength(name.upper(), font=f)
    draw.rectangle([x, y, x + tw + 36, y + 62], fill="white")
    draw.text((x + 18, y + 6), name.upper(), font=f, fill="black")


def render_cover(photo, headline, kicker, brand, handle, date_str):
    img = cover_crop(photo, W, H)
    black = Image.new("RGB", (W, H), "black")
    img = Image.composite(black, img, gradient(W, H, 480))
    d = ImageDraw.Draw(img)
    brand_tag(d, PAD, PAD, brand)
    df = franklin(28, b"SemiBold")
    d.text((W - PAD - d.textlength(date_str, font=df), PAD + 16), date_str, font=df, fill="white")

    font, lines, size = fit_text(d, headline.upper(), anton, W - 2 * PAD, 5, 112, 64)
    lh = int(size * 1.12)
    bottom = H - 150
    y = bottom - lh * len(lines)
    if kicker:
        kf = franklin(30, b"Black")
        k = kicker.upper()
        kw = d.textlength(k, font=kf)
        d.rectangle([PAD, y - 78, PAD + kw + 32, y - 26], fill="white")
        d.text((PAD + 16, y - 72), k, font=kf, fill="black")
    for i, line in enumerate(lines):
        d.text((PAD, y + i * lh), line, font=font, fill="white")

    d.line([PAD, H - 108, W - PAD, H - 108], fill="white", width=2)
    sf = franklin(26, b"Bold")
    d.text((PAD, H - 88), handle, font=sf, fill="white")
    sw = "SWIPE FOR MORE  >>"
    d.text((W - PAD - d.textlength(sw, font=sf), H - 88), sw, font=sf, fill="white")
    return to_jpeg(img)


def render_detail(photo, title, body, brand, handle, idx, total):
    img = Image.new("RGB", (W, H), "black")
    ph_h = 620
    img.paste(cover_crop(photo, W, ph_h), (0, 0))
    d = ImageDraw.Draw(img)
    brand_tag(d, PAD, PAD, brand)
    d.rectangle([0, ph_h, W, ph_h + 10], fill="white")

    nf = franklin(28, b"Bold")
    d.text((PAD, ph_h + 56), f"{idx:02d} / {total:02d}", font=nf, fill="white")
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

    d.line([PAD, H - 108, W - PAD, H - 108], fill=(110, 110, 110), width=2)
    sf = franklin(26, b"Bold")
    d.text((PAD, H - 88), handle, font=sf, fill="white")
    label = brand.upper()
    d.text((W - PAD - d.textlength(label, font=sf), H - 88), label, font=sf, fill=(160, 160, 160))
    return to_jpeg(img)
