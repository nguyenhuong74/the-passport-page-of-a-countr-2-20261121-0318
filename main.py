#!/usr/bin/env python3
"""The Passport Page of a Country That Isn't There.

Draws an invented passport spread for the Republic of Talverra, a small
island fishing nation, in pure Python 3.13 standard library: own 5x7 bitmap
font, own vector drawing, own PNG encoder (zlib + struct + CRC32).
Deterministic: no time, no randomness, no network.
Writes /output/entry.png (1024x640).
"""

import math
import os
import struct
import zlib

# ---------------------------------------------------------------- font -----
# 5x7 bitmap glyphs, drawn by hand for this entry. Each glyph is 7 rows of
# 5 bits, '1' = ink. Uppercase Latin, digits and the punctuation the
# document needs.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "<": ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    ">": ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "*": ("00000", "10101", "01110", "10101", "00000", "00000", "00000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "#": ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
}

CHAR_W, CHAR_H = 5, 7


def text_width(text, scale, spacing=1):
    return len(text) * (CHAR_W * scale + spacing) - spacing


# --------------------------------------------------------------- canvas ----
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.clip = None
        self.px = bytearray(bg) * (w * h)

    def set(self, x, y, color):
        if self.clip is not None:
            cx0, cy0, cx1, cy1 = self.clip
            if not (cx0 <= x < cx1 and cy0 <= y < cy1):
                return
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(color)

    def blend(self, x, y, color, alpha):
        """Alpha-blend color over the pixel (alpha 0..1)."""
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            for k in range(3):
                self.px[i + k] = int(self.px[i + k] * (1 - alpha) + color[k] * alpha)

    def fill_rect(self, x, y, w, h, color):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def rect(self, x, y, w, h, color, t=1):
        self.fill_rect(x, y, w, t, color)
        self.fill_rect(x, y + h - t, w, t, color)
        self.fill_rect(x, y, t, h, color)
        self.fill_rect(x + w - t, y, t, h, color)

    def line(self, x0, y0, x1, y1, color, t=1):
        dx, dy = x1 - x0, y1 - y0
        steps = max(abs(dx), abs(dy), 1)
        for s in range(steps + 1):
            x = int(round(x0 + dx * s / steps))
            y = int(round(y0 + dy * s / steps))
            for a in range(-(t // 2), t // 2 + 1):
                for b in range(-(t // 2), t // 2 + 1):
                    self.set(x + a, y + b, color)

    def ellipse(self, cx, cy, rx, ry, color):
        for yy in range(int(cy - ry), int(cy + ry) + 1):
            dy = (yy - cy) / ry
            if abs(dy) > 1:
                continue
            dx = rx * math.sqrt(1 - dy * dy)
            for xx in range(int(cx - dx), int(cx + dx) + 1):
                self.set(xx, yy, color)

    def ellipse_outline(self, cx, cy, rx, ry, color, t=1):
        for deg in range(360):
            a = math.radians(deg)
            for k in range(t):
                self.set(int(cx + (rx - k) * math.cos(a)),
                         int(cy + (ry - k) * math.sin(a)), color)

    def circle(self, cx, cy, r, color):
        self.ellipse(cx, cy, r, r, color)

    def text(self, x, y, s, scale, color, spacing=1):
        cx = x
        for ch in s:
            glyph = FONT.get(ch.upper(), FONT[" "])
            for gy in range(CHAR_H):
                row = glyph[gy]
                for gx in range(CHAR_W):
                    if row[gx] == "1":
                        self.fill_rect(cx + gx * scale, y + gy * scale,
                                       scale, scale, color)
            cx += CHAR_W * scale + spacing
        return cx

    def text_centered(self, cx, y, s, scale, color, spacing=1):
        w = text_width(s, scale, spacing)
        return self.text(cx - w // 2, y, s, scale, color, spacing)

    def blit_rotated(self, src, cx, cy, angle_deg, alpha=1.0):
        """Blit src canvas centred at (cx, cy), rotated angle_deg clockwise,
        skipping near-white pixels of the source (treated as transparent)."""
        a = math.radians(angle_deg)
        ca, sa = math.cos(a), math.sin(a)
        hw, hh = src.w / 2.0, src.h / 2.0
        diag = int(math.hypot(hw, hh)) + 2
        for dy in range(-diag, diag + 1):
            for dx in range(-diag, diag + 1):
                # inverse rotate: source coords of this destination pixel
                sx = ca * dx + sa * dy + hw
                sy = -sa * dx + ca * dy + hh
                ix, iy = int(sx), int(sy)
                if 0 <= ix < src.w and 0 <= iy < src.h:
                    i = (iy * src.w + ix) * 3
                    r, g, b = src.px[i], src.px[i + 1], src.px[i + 2]
                    if r > 235 and g > 235 and b > 235:
                        continue
                    self.blend(cx + dx, cy + dy, (r, g, b), alpha)


# ------------------------------------------------------------ PNG writer ---
def write_png(path, canvas):
    def chunk(kind, data):
        c = struct.pack(">I", len(data)) + kind + data
        return c + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    w, h = canvas.w, canvas.h
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = bytearray()
    for y in range(h):
        raw.append(0)  # filter: none
        raw += canvas.px[y * w * 3:(y + 1) * w * 3]
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + chunk(b"IEND", b""))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    return len(png)

# ------------------------------------------------------------- palette -----
INK = (28, 43, 57)          # dark navy ink
INK_SOFT = (74, 88, 102)    # grey-blue for labels
TEAL = (15, 95, 92)         # Talverra accent
GOLD = (146, 110, 42)
PAPER = (243, 237, 218)     # passport paper
PAPER_DARK = (232, 225, 200)
DESK = (22, 36, 46)         # surface the spread lies on
MRZ_BG = (226, 224, 212)
STAMP_BLUE = (31, 78, 156)
STAMP_PURPLE = (122, 46, 109)
STAMP_RED = (138, 47, 35)
PHOTO_BG = (168, 182, 190)
SKIN = (217, 165, 131)
SKIN_DARK = (198, 145, 112)
HAIR = (58, 42, 32)
JACKET = (24, 68, 74)

W, H = 1024, 640
PAGE_L = (14, 14, 494, 612)   # x, y, w, h of the left page
PAGE_R = (516, 14, 494, 612)


# ------------------------------------------------------------ MRZ helpers --
def mrz_check(s):
    total = 0
    for i, ch in enumerate(s):
        if ch == "<":
            v = 0
        elif ch.isdigit():
            v = int(ch)
        else:
            v = ord(ch) - 55  # A=10
        total += v * (7, 3, 1)[i % 3]
    return str(total % 10)


def mrz_lines():
    line1 = "P<TLVVOSS<<ELENA<MARIS"
    line1 = line1 + "<" * (44 - len(line1))
    doc = "TLV047381"
    dob = "910314"
    exp = "310601"
    personal = "<" * 14
    body = (doc + mrz_check(doc) + "TLV" + dob + mrz_check(dob) + "F"
            + exp + mrz_check(exp) + personal + mrz_check(personal))
    line2 = body + mrz_check(body)
    assert len(line1) == 44 and len(line2) == 44, (len(line1), len(line2))
    return line1, line2


# -------------------------------------------------------------- portrait ---
def draw_portrait(c, x, y, w, h):
    c.clip = (x, y, x + w, y + h)
    c.fill_rect(x, y, w, h, PHOTO_BG)
    # faint studio backdrop bands
    c.fill_rect(x, y + int(h * 0.62), w, h - int(h * 0.62), (158, 172, 180))
    cx, cy = x + w // 2, y + int(h * 0.40)
    # shoulders / jacket
    c.ellipse(cx, y + h + 18, w // 2 + 6, int(h * 0.42), JACKET)
    # shirt collar
    c.fill_rect(cx - 16, y + int(h * 0.66), 32, 12, (238, 236, 228))
    c.line(cx - 16, y + int(h * 0.66) + 11, cx, y + int(h * 0.66) + 26,
           (210, 208, 198), 2)
    c.line(cx + 16, y + int(h * 0.66) + 11, cx, y + int(h * 0.66) + 26,
           (210, 208, 198), 2)
    # neck
    c.fill_rect(cx - 13, cy + 34, 26, 22, SKIN_DARK)
    # head
    c.ellipse(cx, cy, 34, 44, SKIN)
    # ears
    c.ellipse(cx - 35, cy + 2, 5, 9, SKIN)
    c.ellipse(cx + 35, cy + 2, 5, 9, SKIN)
    # hair: cap over the top, kept clear of the eyes, with short side locks
    c.ellipse(cx, cy - 26, 37, 26, HAIR)
    c.fill_rect(cx - 37, cy - 30, 11, 30, HAIR)
    c.fill_rect(cx + 26, cy - 30, 11, 28, HAIR)
    c.ellipse(cx - 8, cy - 34, 30, 14, HAIR)
    # brows
    c.line(cx - 22, cy - 12, cx - 8, cy - 14, HAIR, 2)
    c.line(cx + 8, cy - 14, cx + 22, cy - 12, HAIR, 2)
    # eyes
    c.ellipse(cx - 15, cy - 4, 5, 3, (32, 28, 26))
    c.ellipse(cx + 15, cy - 4, 5, 3, (32, 28, 26))
    # nose
    c.line(cx, cy + 2, cx - 2, cy + 16, SKIN_DARK, 2)
    c.line(cx - 2, cy + 16, cx + 3, cy + 17, SKIN_DARK, 2)
    # mouth
    c.line(cx - 9, cy + 28, cx + 9, cy + 28, (146, 84, 72), 2)
    # chin shadow
    c.ellipse(cx, cy + 38, 12, 5, SKIN_DARK)
    c.clip = None
    c.rect(x, y, w, h, INK, 2)


# ---------------------------------------------------------------- stamps ---
def stamp_canvas(country, kind, date, port, color, w=252, h=112):
    s = Canvas(w, h, (255, 255, 255))
    s.rect(4, 4, w - 8, h - 8, color, 3)
    s.rect(10, 10, w - 20, h - 20, color, 1)
    s.text_centered(w // 2, 18, country, 2, color)
    s.line(22, 40, w - 22, 40, color, 1)
    s.text_centered(w // 2, 48, kind, 2, color)
    s.text_centered(w // 2, 70, date, 2, color)
    s.text_centered(w // 2, 90, port, 1, color)
    return s


def coat_of_arms(c, cx, cy, r):
    c.ellipse_outline(cx, cy, r, r, TEAL, 2)
    c.ellipse_outline(cx, cy, r - 5, r - 5, GOLD, 1)
    # five-point star
    pts = []
    for i in range(5):
        a = math.radians(-90 + i * 72)
        pts.append((cx + int((r - 12) * math.cos(a)),
                    cy + int((r - 12) * math.sin(a))))
        a2 = math.radians(-90 + i * 72 + 36)
        pts.append((cx + int((r - 22) * math.cos(a2)),
                    cy + int((r - 22) * math.sin(a2))))
    for i in range(10):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % 10]
        c.line(x0, y0, x1, y1, TEAL, 2)
    # three waves below the star
    for k in range(3):
        yy = cy + r - 16 + k * 4
        for xx in range(cx - r + 10, cx + r - 9):
            off = int(2 * math.sin((xx - cx) / 6.0))
            c.set(xx, yy + off, TEAL)


def field(c, x, y, label, value, scale=2):
    c.text(x, y, label, 1, INK_SOFT)
    c.text(x, y + 10, value, scale, INK)


def guilloche(c, px, py, pw, ph):
    # faint concentric arcs, like a security background
    for r in range(60, 420, 34):
        c.ellipse_outline(px + pw - 40, py + ph - 30, r, int(r * 0.7),
                          (231, 222, 196), 1)


def speckle(c, px, py, pw, ph, seed=12345):
    # deterministic paper grain (fixed-seed LCG, no time, no randomness)
    state = seed
    for _ in range(2200):
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        x = px + state % pw
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        y = py + state % ph
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        c.blend(x, y, (120, 105, 70) if state % 2 else (255, 255, 250), 0.05)


# -------------------------------------------------------------- the spread --
def draw():
    c = Canvas(W, H, DESK)
    # pages
    for (px, py, pw, ph) in (PAGE_L, PAGE_R):
        c.fill_rect(px, py, pw, ph, PAPER)
        guilloche(c, px, py, pw, ph)
        speckle(c, px, py, pw, ph)
        c.rect(px, py, pw, ph, (120, 105, 70), 1)
    # spine shadow between the pages
    for k in range(8):
        c.fill_rect(508 + k, 14, 1, 612, (0, 0, 0))
        c.blend(508 + k, 14, (0, 0, 0), 0.0)  # keep loop explicit
    c.fill_rect(508, 14, 2, 612, (90, 78, 50))
    c.fill_rect(512, 14, 2, 612, (255, 250, 235))

    lx, ly, lw, lh = PAGE_L
    rx, ry, rw, rh = PAGE_R

    # ---- left page: the data page ----
    coat_of_arms(c, lx + lw // 2, ly + 52, 30)
    c.text_centered(lx + lw // 2, ly + 92, "REPUBLIC OF TALVERRA", 2, INK, 2)
    c.line(lx + 60, ly + 118, lx + lw - 60, ly + 118, TEAL, 2)
    c.text_centered(lx + lw // 2, ly + 126, "PASSPORT", 4, INK, 2)
    c.text_centered(lx + lw // 2, ly + 158, "PASSEPORT", 1, INK_SOFT, 2)

    # portrait
    draw_portrait(c, lx + 26, ly + 178, 150, 185)
    # signature under the portrait
    c.line(lx + 26, ly + 392, lx + 176, ly + 392, INK, 1)
    c.text(lx + 26, ly + 398, "HOLDER'S SIGNATURE", 1, INK_SOFT)
    # a hand-drawn style signature squiggle
    sx, sy = lx + 34, ly + 386
    for t in range(0, 120):
        c.set(sx + t, sy + int(4 * math.sin(t / 9.0)) - t // 40, INK)
    c.text(lx + 30, ly + 412, "ELENA M. VOSS", 1, INK)

    # data fields
    fx = lx + 196
    c.text(fx, ly + 178, "TYPE", 1, INK_SOFT)
    c.text(fx, ly + 188, "P", 2, INK)
    c.text(fx + 62, ly + 178, "CODE", 1, INK_SOFT)
    c.text(fx + 62, ly + 188, "TLV", 2, INK)
    c.text(fx + 140, ly + 178, "PASSPORT NO.", 1, INK_SOFT)
    c.text(fx + 140, ly + 188, "TLV047381", 2, INK)
    c.line(fx, ly + 212, lx + lw - 26, ly + 212, (190, 178, 148), 1)

    field(c, fx, ly + 222, "SURNAME", "VOSS")
    field(c, fx, ly + 258, "GIVEN NAMES", "ELENA MARIS")
    field(c, fx, ly + 294, "NATIONALITY", "TALVERRAN")
    field(c, fx, ly + 330, "DATE OF BIRTH", "14 MAR 1991")
    field(c, fx, ly + 366, "PLACE OF BIRTH", "PORT LIRENN")
    field(c, fx + 150, ly + 222, "SEX", "F")
    field(c, fx + 150, ly + 258, "DATE OF ISSUE", "02 JUN 2021")
    field(c, fx + 150, ly + 294, "DATE OF EXPIRY", "01 JUN 2031")
    field(c, fx + 150, ly + 330, "HEIGHT", "1.68 M")
    field(c, fx + 150, ly + 366, "AUTHORITY", "PORT LIRENN")
    c.text(fx, ly + 408, "THIS PASSPORT IS ISSUED IN", 1, INK_SOFT)
    c.text(fx, ly + 420, "TALVERRAN AND ENGLISH.", 1, INK_SOFT)

    # machine-readable zone
    c.fill_rect(lx + 18, ly + 446, lw - 36, 64, MRZ_BG)
    c.rect(lx + 18, ly + 446, lw - 36, 64, (170, 162, 140), 1)
    l1, l2 = mrz_lines()
    c.text(lx + 30, ly + 456, l1, 2, INK, 0)
    c.text(lx + 30, ly + 478, l2, 2, INK, 0)
    c.text(lx + 26, ly + 522, "P<TLVVOSS<<ELENA<MARIS  -  TLV047381  -  ISSUED PORT LIRENN",
           1, INK_SOFT)

    # ---- right page: visas and stamps ----
    c.text(rx + 24, ry + 24, "VISAS", 3, INK)
    c.text(rx + rw - 60, ry + 24, "12", 2, INK_SOFT)
    c.line(rx + 24, ry + 52, rx + rw - 24, ry + 52, TEAL, 2)

    # the telling detail: a seaman's visa from Marova
    vx, vy, vw, vh = rx + 24, ry + 64, rw - 48, 118
    c.fill_rect(vx, vy, vw, vh, (247, 243, 228))
    c.rect(vx, vy, vw, vh, STAMP_BLUE, 2)
    c.rect(vx + 5, vy + 5, vw - 10, vh - 10, STAMP_BLUE, 1)
    c.text(vx + 14, vy + 12, "VISA  -  REPUBLIC OF MAROVA", 2, STAMP_BLUE)
    c.text(vx + 14, vy + 36, "TYPE: SEAMAN'S ENTRY  -  SINGLE ENTRY, 90 DAYS", 1, INK)
    c.text(vx + 14, vy + 52, "CONDITION: HOLDER IS LICENSED TO CREW THE FISHING", 1, INK)
    c.text(vx + 14, vy + 66, "VESSEL SV MERIDIAN. MUST REGISTER WITH THE", 1, INK)
    c.text(vx + 14, vy + 80, "HARBOUR OFFICE WITHIN 48 HOURS OF ARRIVAL.", 1, INK)
    c.text(vx + 14, vy + 98, "VALID FOR THE FISHING SEASON ONLY. FEE: 12 TALERS PAID.", 1, INK)

    # travel history: arrival / departure stamps from the three neighbours
    trips = [
        ("MAROVA", "18 AUG 2021", "02 SEP 2021", "PORT OF MAROVA",
         STAMP_BLUE, -6, 5),
        ("KESTREL ISLES", "11 JAN 2023", "27 JAN 2023", "KESTREL QUAY",
         STAMP_PURPLE, 5, -7),
        ("SANTHOR", "05 MAY 2024", "19 MAY 2024", "SANTHOR HARBOUR",
         STAMP_RED, -5, 6),
    ]
    row_y = [ry + 206, ry + 322, ry + 438]
    for (country, arr, dep, port, color, a1, a2), cy in zip(trips, row_y):
        s1 = stamp_canvas(country, "ARRIVAL", arr, port, color)
        s2 = stamp_canvas(country, "DEPARTURE", dep, port, color)
        c.blit_rotated(s1, rx + 150, cy + 56, a1, 0.85)
        c.blit_rotated(s2, rx + 350, cy + 56, a2, 0.85)

    # observations at the foot of the visa page
    c.line(rx + 24, ry + 556, rx + rw - 24, ry + 556, (190, 178, 148), 1)
    c.text(rx + 24, ry + 566, "OBSERVATIONS: HOLDER'S RIGHT OF ABODE IN TALVERRA", 1, INK_SOFT)
    c.text(rx + 24, ry + 580, "IS UNCONDITIONAL. NEXT OF KIN: A. VOSS, PORT LIRENN.", 1, INK_SOFT)
    return c


def main():
    canvas = draw()
    path = "/output/entry.png"
    size = write_png(path, canvas)
    print(f"wrote {path}: {canvas.w}x{canvas.h}, {size} bytes")


if __name__ == "__main__":
    main()
