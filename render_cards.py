# -*- coding: utf-8 -*-
"""인스타 뉴스카드 렌더러 v3: 콘텐츠 JSON + niches.json 테마 → 1080x1350 캐러셀.

디자인 v3:
- 폰트: Pretendard (SIL OFL, 상업용 무료) — 제목 ExtraBold / 본문 Regular
- 본문 카드: 니치 컬러 틴트 배경 + 흰 라운드 패널(소프트 섀도) + 형광펜 제목
- 카드별 컬러 이모지 아이콘 (Noto Color Emoji, OFL) — JSON의 "emoji" 필드
- 커버/아웃트로: 니치 컬러 풀배경 + 반투명 장식 원

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
INK = (28, 30, 38)          # 제목: 살짝 푸른 기 도는 잉크색
BODY = (68, 74, 88)         # 본문: 회색보다 진한 슬레이트 (가독성)
LIGHT_ON_DARK = (232, 232, 245)
DIM_DOT = (200, 202, 210)

FONTS = Path(__file__).parent / "fonts"
FONT_XB = str(FONTS / "Pretendard-ExtraBold.otf")
FONT_SB = str(FONTS / "Pretendard-SemiBold.otf")
FONT_REG = str(FONTS / "Pretendard-Regular.otf")
FONT_EMOJI = str(FONTS / "NotoColorEmoji.ttf")

DEFAULT_EMOJI = {"econ": "📊", "techlife": "💡"}


def font(path, size):
    return ImageFont.truetype(path, size)


def tint(rgb, factor):
    """factor 0→원색, 1→흰색."""
    return tuple(int(c + (255 - c) * factor) for c in rgb)


def emoji_img(ch, size):
    """Noto Color Emoji는 109px 비트맵이라 그 크기로 그린 뒤 리사이즈."""
    canvas = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    d.text((10, 10), ch, font=font(FONT_EMOJI, 109), embedded_color=True)
    box = canvas.getbbox()
    if not box:
        return None
    return canvas.crop(box).resize((size, size), Image.LANCZOS)


def paste_emoji(img, ch, x, y, size):
    if not ch:
        return
    e = emoji_img(ch, size)
    if e:
        img.paste(e, (x, y), e)


def circles(img, spots):
    """반투명 장식 원. spots = [(cx, cy, r, rgba), ...]"""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for cx, cy, r, rgba in spots:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=rgba)
    img.alpha_composite(layer)


def wrap(text, width_chars):
    lines = []
    for para in text.split("\n"):
        lines += textwrap.wrap(para, width=width_chars) or [""]
    return lines


def draw_lines(d, lines, x, y, f, fill, line_gap=18, marker=None):
    """marker=(r,g,b)면 각 줄 뒤에 형광펜 박스를 깐다. 행높이는 폰트 기준 고정."""
    ref = f.getbbox("한글Agj")
    lh = ref[3] - ref[1]
    for ln in lines:
        if marker and ln.strip():
            bbox = d.textbbox((x, y), ln, font=f)
            pad = 14
            d.rectangle([bbox[0] - pad, bbox[1] + (bbox[3] - bbox[1]) * 0.18,
                         bbox[2] + pad, bbox[3] + 8], fill=marker)
        d.text((x, y), ln, font=f, fill=fill)
        y += lh + line_gap
    return y


def chip(d, text, x, y, bg, fg):
    f = font(FONT_XB, 36)
    tw = d.textbbox((0, 0), text, font=f)[2]
    d.rounded_rectangle([x, y, x + tw + 60, y + 70], radius=35, fill=bg)
    d.text((x + 30, y + 14), text, font=f, fill=fg)


def dots(d, idx, total, active, inactive):
    x0 = W - M - total * 34
    for i in range(total):
        d.ellipse([x0 + i * 34, H - 104, x0 + i * 34 + 18, H - 86],
                  fill=active if i == idx else inactive)


def render_cover(spec, cfg, total):
    t = cfg["theme"]
    img = Image.new("RGBA", (W, H), tuple(t["cover_bg"]))
    circles(img, [(W - 60, 180, 320, (255, 255, 255, 18)),
                  (W - 250, 520, 150, (255, 255, 255, 12)),
                  (60, H - 240, 200, (255, 255, 255, 10))])
    d = ImageDraw.Draw(img)
    chip(d, cfg["display"], M, 120, tuple(t["highlight"]), tuple(t["chip_text"]))
    paste_emoji(img, spec["cover"].get("emoji"), W - M - 200, 90, 200)
    y = draw_lines(d, wrap(spec["cover"]["headline"], 8), M, 380,
                   font(FONT_XB, 112), WHITE, line_gap=28)
    d.rectangle([M, y + 24, M + 180, y + 40], fill=tuple(t["highlight"]))
    draw_lines(d, wrap(spec["cover"]["sub"], 21), M, y + 90,
               font(FONT_REG, 44), LIGHT_ON_DARK, line_gap=20)
    d.text((M, H - 200), spec["date"], font=font(FONT_XB, 42), fill=tuple(t["highlight"]))
    d.text((M, H - 110), cfg["handle"], font=font(FONT_SB, 34), fill=LIGHT_ON_DARK)
    dots(d, 0, total, tuple(t["highlight"]), (255, 255, 255))
    return img.convert("RGB")


def render_content(spec, cfg, i, card, total):
    t = cfg["theme"]
    accent = tuple(t["accent"])
    img = Image.new("RGBA", (W, H), tint(accent, 0.93))
    # 장식: 우상단 큰 원 + 좌하단 작은 원 (틴트 톤)
    circles(img, [(W - 100, 120, 300, (*accent, 26)),
                  (120, H - 90, 160, (*accent, 18))])
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 16], fill=accent)  # 상단 컬러 바
    # 흰 라운드 패널 + 소프트 섀도 (틴트 배경보다 한 단계 진한 톤)
    panel = [56, 292, W - 56, H - 168]
    d.rounded_rectangle([panel[0] + 10, panel[1] + 14, panel[2] + 10, panel[3] + 14],
                        radius=44, fill=tint(accent, 0.72))
    d.rounded_rectangle(panel, radius=44, fill=WHITE)
    # 헤더: 번호(좌) + 이모지(우)
    d.text((M, 96), f"{i:02d}", font=font(FONT_XB, 130), fill=accent)
    paste_emoji(img, card.get("emoji", DEFAULT_EMOJI.get(spec["niche"])),
                W - M - 170, 84, 170)
    d = ImageDraw.Draw(img)
    x = M + 30
    y = draw_lines(d, wrap(card["title"], 11), x, 372, font(FONT_XB, 74), INK,
                   line_gap=26, marker=tuple(t["highlight"]))
    draw_lines(d, wrap(card["body"], 18), x, y + 56, font(FONT_REG, 46), BODY, line_gap=26)
    src = card.get("source", {}).get("outlet")
    if src:
        community = src.startswith("r/") or src in ("Hacker News", "HN")
        label = f"출처: {src}" if community else f"자료: {src} 보도"
        d.text((x, panel[3] - 78), label, font=font(FONT_REG, 30), fill=(148, 152, 164))
    d.text((M, H - 116), cfg["handle"], font=font(FONT_SB, 34), fill=tint(accent, 0.35))
    dots(d, i, total, accent, DIM_DOT)
    return img.convert("RGB")


def render_outro(spec, cfg, total):
    t = cfg["theme"]
    img = Image.new("RGBA", (W, H), tuple(t["cover_bg"]))
    circles(img, [(W - 120, H - 200, 280, (255, 255, 255, 16)),
                  (100, 200, 180, (255, 255, 255, 12))])
    d = ImageDraw.Draw(img)
    paste_emoji(img, spec["outro"].get("emoji", "🙌"), M, 270, 150)
    d = ImageDraw.Draw(img)
    y = draw_lines(d, wrap(spec["outro"]["text"], 10), M, 480,
                   font(FONT_XB, 90), WHITE, line_gap=28)
    note = spec["outro"].get("note")
    if note:
        draw_lines(d, wrap(note, 24), M, y + 70, font(FONT_REG, 38), LIGHT_ON_DARK, line_gap=16)
    d.text((M, H - 110), cfg["handle"], font=font(FONT_SB, 34), fill=LIGHT_ON_DARK)
    dots(d, total - 1, total, tuple(t["highlight"]), (255, 255, 255))
    return img.convert("RGB")


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
