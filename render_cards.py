# -*- coding: utf-8 -*-
"""인스타 뉴스카드 렌더러 v2: 콘텐츠 JSON + niches.json 테마 → 1080x1350 캐러셀.

디자인: 커버/아웃트로는 니치 컬러 풀배경, 본문 카드는 흰 배경 + 형광펜 제목 강조.
사용: python render_cards.py content/파일.json
출력: output/<slug>/card_00.png ~ card_NN.png
"""
import json
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

W, H = 1080, 1350
M = 90

WHITE = (255, 255, 255)
INK = (23, 23, 28)
GRAY = (95, 95, 105)
LIGHT_ON_DARK = (225, 225, 240)
DIM_DOT = (205, 205, 205)

FONT_BOLD = r"C:\Windows\Fonts\malgunbd.ttf"
FONT_REG = r"C:\Windows\Fonts\malgun.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


def wrap(text, width_chars):
    lines = []
    for para in text.split("\n"):
        lines += textwrap.wrap(para, width=width_chars) or [""]
    return lines


def draw_lines(d, lines, x, y, f, fill, line_gap=18, marker=None):
    """marker=(r,g,b)면 각 줄 뒤에 형광펜 박스를 깐다."""
    for ln in lines:
        bbox = d.textbbox((x, y), ln, font=f)
        if marker and ln.strip():
            pad = 14
            d.rectangle([bbox[0] - pad, bbox[1] + (bbox[3] - bbox[1]) * 0.18,
                         bbox[2] + pad, bbox[3] + 8], fill=marker)
        d.text((x, y), ln, font=f, fill=fill)
        y = bbox[3] + line_gap
    return y


def chip(d, text, x, y, bg, fg):
    f = font(FONT_BOLD, 36)
    tw = d.textbbox((0, 0), text, font=f)[2]
    d.rounded_rectangle([x, y, x + tw + 60, y + 70], radius=35, fill=bg)
    d.text((x + 30, y + 12), text, font=f, fill=fg)


def dots(d, idx, total, active, inactive):
    x0 = W - M - total * 34
    for i in range(total):
        d.ellipse([x0 + i * 34, H - 104, x0 + i * 34 + 18, H - 86],
                  fill=active if i == idx else inactive)


def render_cover(spec, cfg, total):
    t = cfg["theme"]
    img = Image.new("RGB", (W, H), tuple(t["cover_bg"]))
    d = ImageDraw.Draw(img)
    chip(d, cfg["display"], M, 120, tuple(t["highlight"]), tuple(t["chip_text"]))
    y = draw_lines(d, wrap(spec["cover"]["headline"], 8), M, 380,
                   font(FONT_BOLD, 118), WHITE, line_gap=28)
    d.rectangle([M, y + 24, M + 180, y + 40], fill=tuple(t["highlight"]))
    draw_lines(d, wrap(spec["cover"]["sub"], 18), M, y + 90,
               font(FONT_REG, 48), LIGHT_ON_DARK, line_gap=20)
    d.text((M, H - 200), spec["date"], font=font(FONT_BOLD, 42), fill=tuple(t["highlight"]))
    d.text((M, H - 110), cfg["handle"], font=font(FONT_BOLD, 34), fill=LIGHT_ON_DARK)
    dots(d, 0, total, tuple(t["highlight"]), (255, 255, 255, 90)[:3])
    return img


def render_content(spec, cfg, i, card, total):
    t = cfg["theme"]
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 18], fill=tuple(t["accent"]))  # 상단 컬러 바
    d.text((M, 110), f"{i:02d}", font=font(FONT_BOLD, 140), fill=tuple(t["accent"]))
    y = draw_lines(d, wrap(card["title"], 11), M, 360, font(FONT_BOLD, 80), INK,
                   line_gap=26, marker=tuple(t["highlight"]))
    draw_lines(d, wrap(card["body"], 17), M, y + 60, font(FONT_REG, 52), GRAY, line_gap=24)
    d.text((M, H - 110), cfg["handle"], font=font(FONT_BOLD, 34), fill=GRAY)
    dots(d, i, total, tuple(t["accent"]), DIM_DOT)
    return img


def render_outro(spec, cfg, total):
    t = cfg["theme"]
    img = Image.new("RGB", (W, H), tuple(t["cover_bg"]))
    d = ImageDraw.Draw(img)
    y = draw_lines(d, wrap(spec["outro"]["text"], 10), M, 460,
                   font(FONT_BOLD, 92), WHITE, line_gap=28)
    note = spec["outro"].get("note")
    if note:
        draw_lines(d, wrap(note, 24), M, y + 70, font(FONT_REG, 38), LIGHT_ON_DARK, line_gap=16)
    d.text((M, H - 110), cfg["handle"], font=font(FONT_BOLD, 34), fill=LIGHT_ON_DARK)
    dots(d, total - 1, total, tuple(t["highlight"]), (170, 170, 200))
    return img


def main():
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    niches = json.loads((Path(__file__).parent / "niches.json").read_text(encoding="utf-8"))
    cfg = niches[spec["niche"]]

    out_dir = Path(__file__).parent / "output" / spec["slug"]
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(spec["cards"]) + 2
    render_cover(spec, cfg, total).save(out_dir / "card_00.png")
    for i, card in enumerate(spec["cards"], start=1):
        render_content(spec, cfg, i, card, total).save(out_dir / f"card_{i:02d}.png")
    render_outro(spec, cfg, total).save(out_dir / f"card_{total-1:02d}.png")
    print(f"[{spec['niche']}] {total}장 생성 → {out_dir}")


if __name__ == "__main__":
    main()
