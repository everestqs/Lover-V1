#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Neon Parçacıklarla Kalbin Doğuşu  (v2 - referans görsele göre)
==============================================================
Pygame + math ile yazılmış, 9 aşamalı neon kalp animasyonu.

Kontroller
----------
  ESC / Q : çıkış          SPACE : duraklat / devam
  R       : baştan başlat  H     : aşama bilgisini aç/kapat
  1 - 9   : ilgili aşamanın başlangıcına atla

Çalıştırma:  pip install pygame   ->   python neon_kalp.py
"""

import math
import random
import sys

import pygame

# ----------------------------------------------------------------------------
# GENEL AYARLAR
# ----------------------------------------------------------------------------
W, H = 960, 720
FPS = 60
CX, CY = W // 2, 250          # kalbin merkezi (parametrik denklemin orijini)
S0 = 9.0                      # kalbin temel ölçeği (birim -> piksel)
Y0 = -2.5                     # kalbin dikey orta noktası (denklem biriminde)
HC_Y = CY + 2.5 * S0          # kalbin ekrandaki görsel merkezi
FLOOR = 470                   # zemin çizgisinin y konumu
REFL_H = 105                  # yansıma yüksekliği
N_PART = 420                  # ana parçacık sayısı
BPM = 72                      # kalp atış hızı
TEXT_Y, RULE_Y = 565, 628     # "Love" yazısı ve altındaki çizgi/kalp simgesi

# Aşama başlangıç zamanları (saniye)
T = {1: 0.0, 2: 5.0, 3: 9.0, 4: 13.0, 5: 16.5, 6: 20.0, 7: 24.0, 8: 28.0, 9: 32.0}
T_MINI = 22.0                 # küçük kalplerin doğuşu (6. aşamanın ortası)
STAGE_NAMES = {
    1: "",
    2: "",
    3: "  ",
    4: " ",
    5: " ",
    6: "",
    7: "  ",
    8: " ",
    9: " ",
}

# Neon renkler
PINK = (255, 50, 190)
PURPLE = (160, 70, 255)
BLUE = (50, 130, 255)
CYAN = (0, 240, 255)
MAGENTA = (255, 0, 220)
ELECTRIC = (30, 90, 255)
GOLD = (255, 200, 70)
TEAL = (60, 255, 210)
ORANGE = (255, 150, 60)
WHITE = (255, 255, 255)

PAL_A = [GOLD, TEAL, PINK]               # 3. aşama: altın - turkuaz - pembe
PAL_B = [PINK, PURPLE, BLUE]             # 4. aşama: pembe - mor - mavi
PAL_C = [CYAN, BLUE, PINK, ORANGE]       # 6. aşama: çok renkli gradyan
CYCLE = [CYAN, MAGENTA, ELECTRIC, PURPLE]   # 8. aşama RGB döngüsü
HOLO = [GOLD, CYAN, PINK, BLUE]          # 7. aşama holografik şeritler


# ----------------------------------------------------------------------------
# YARDIMCI FONKSİYONLAR
# ----------------------------------------------------------------------------
def clamp01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def ramp(t, start, dur):
    return clamp01((t - start) / dur)


def smooth(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def lerp(a, b, k):
    return a + (b - a) * k


def lerp_col(c1, c2, k):
    return (lerp(c1[0], c2[0], k), lerp(c1[1], c2[1], k), lerp(c1[2], c2[2], k))


def ci(c, f=1.0):
    """Rengi f ile çarpıp 0-255 arası tamsayıya çevirir."""
    return (int(max(0, min(255, c[0] * f))),
            int(max(0, min(255, c[1] * f))),
            int(max(0, min(255, c[2] * f))))


def pal(stops, p):
    """Renk duraklarından oluşan paletten p (0..1) konumundaki rengi örnekler."""
    p = clamp01(p) * (len(stops) - 1)
    i = min(int(p), len(stops) - 2)
    return lerp_col(stops[i], stops[i + 1], smooth(p - i))


def cyc_pal(stops, ph):
    """Döngüsel palet: ph sonsuza kadar artabilir (RGB cycle)."""
    p = (ph % 1.0) * len(stops)
    i = int(p)
    return lerp_col(stops[i % len(stops)], stops[(i + 1) % len(stops)], smooth(p - i))


def cycle_color(ph):
    return cyc_pal(CYCLE, ph)


class Style:
    """Her karede hesaplanan zamana bağlı stil katsayıları."""
    __slots__ = ("tm", "w4", "w6", "cyc", "white")


def heart_color(u, st, off=0.0):
    """
    Kalp hattının rengi (u: kalp parametresi).
    3. aşama altın-turkuaz-pembe, 4. aşama pembe-mor-mavi, 6. aşama çok renkli,
    8. aşama CYCLE listesinde kesintisiz dönen renkler, 5. aşama camsı beyaz.
    """
    sx = math.sin(u) ** 3
    a = pal(PAL_A, 0.5 + 0.5 * sx)
    pos = 0.5 + 0.5 * math.sin(u + st.tm * 0.6 + off)
    col = lerp_col(a, pal(PAL_B, pos), st.w4)
    col = lerp_col(col, pal(PAL_C, pos), st.w6)
    if st.cyc > 0.001:
        col = lerp_col(col, cycle_color(st.tm * 0.18 + 0.3 * pos + off * 0.1), st.cyc)
    if st.white > 0.001:
        col = lerp_col(col, WHITE, 0.55 * st.white)
    return col


# ----------------------------------------------------------------------------
# KALP MATEMATİĞİ  (parametrik kalp denklemi)
#   x = 16 sin^3(t)
#   y = 13 cos(t) - 5 cos(2t) - 2 cos(3t) - cos(4t)
# ----------------------------------------------------------------------------
def heart_xy(u):
    x = 16 * math.sin(u) ** 3
    y = (13 * math.cos(u) - 5 * math.cos(2 * u)
         - 2 * math.cos(3 * u) - math.cos(4 * u))
    return x, y


def heart_screen(u, S, sc=1.0):
    """Parametreyi ekran koordinatına çevirir (sc<1: içteki küçük kalp)."""
    x, y = heart_xy(u)
    return CX + x * sc * S, CY - (Y0 + (y - Y0) * sc) * S


OUT_M = 56                                    # çizgi yarısındaki parça sayısı
RIGHT_RAW = [heart_xy(math.pi - math.pi * k / OUT_M) for k in range(OUT_M + 1)]
LEFT_RAW = [heart_xy(math.pi + math.pi * k / OUT_M) for k in range(OUT_M + 1)]
FULL_RAW = [heart_xy(2 * math.pi * i / 120) for i in range(120)]
MINI_UNIT = []
for _i in range(28):
    _x, _y = heart_xy(2 * math.pi * _i / 28)
    MINI_UNIT.append((_x / 16.0, (_y - Y0) / 16.0))


# ----------------------------------------------------------------------------
# 3B YÖRÜNGE HALKALARI  (5. aşama: noktalı halkalar, 7. aşama: büyük şeritler)
# ----------------------------------------------------------------------------
def make_ring(R, tilt, roll, speed):
    return dict(R=R, speed=speed, ct=math.cos(tilt), st=math.sin(tilt),
                cr=math.cos(roll), sr=math.sin(roll))


RINGS = [make_ring(250, 1.20, 0.35, 0.75), make_ring(290, 0.80, -0.55, -0.55),
         make_ring(215, 1.50, 1.25, 1.00)]
LOOPS = [make_ring(310, 1.05, 0.50, 0.45), make_ring(285, 0.85, -0.70, -0.38),
         make_ring(330, 1.30, 1.50, 0.30)]
COMET = make_ring(235, 0.95, 0.20, 0.0)


def ring_point(ring, a, spin, R=None):
    """Halka üzerindeki noktayı 3B döndürüp ekrana izdüşürür. z: -1..1 (derinlik)."""
    R0 = ring["R"]
    r = R0 if R is None else R
    x, y = r * math.cos(a), r * math.sin(a)
    x, y = x * ring["cr"] - y * ring["sr"], x * ring["sr"] + y * ring["cr"]
    y, z = y * ring["ct"], y * ring["st"]
    cs, sn = math.cos(spin), math.sin(spin)
    x, z = x * cs + z * sn, -x * sn + z * cs
    return CX + x, HC_Y + y, z / R0


def heartbeat(ph):
    """Nabız eğrisi: 'lub-dub' iki Gauss tepesi (ph: 0..1)."""
    g1 = math.exp(-((ph - 0.10) / 0.055) ** 2)
    g2 = math.exp(-((ph - 0.32) / 0.070) ** 2)
    return g1 + 0.65 * g2


# ----------------------------------------------------------------------------
# NESNE SINIFLARI
# ----------------------------------------------------------------------------
class Particle:
    """Ana neon parçacık: serbest hareket + kalp yörüngesine çekim."""
    __slots__ = ("x", "y", "vx", "vy", "layer", "sc", "u", "du", "base",
                 "size", "ph", "f1", "f2")
    LAYER_SCALES = [1.00, 0.84, 0.68, 0.52]
    LAYER_WEIGHTS = [45, 28, 18, 9]
    COLORS = [PINK, PINK, PURPLE, PURPLE, BLUE, BLUE, CYAN, GOLD]

    def __init__(self):
        # [AŞAMA 1] merkezden dışarı saçılan rastgele parçacıklar
        ang = random.uniform(0, 2 * math.pi)
        sp = random.uniform(250, 750)
        self.x = CX + random.uniform(-20, 20)
        self.y = HC_Y + random.uniform(-20, 20)
        self.vx, self.vy = math.cos(ang) * sp, math.sin(ang) * sp
        self.layer = random.choices(range(4), self.LAYER_WEIGHTS)[0]
        self.sc = self.LAYER_SCALES[self.layer]
        self.u = random.uniform(0, 2 * math.pi)
        self.du = (0.20 if self.layer % 2 == 0 else -0.20) * random.uniform(0.7, 1.3)
        self.base = random.choice(self.COLORS)
        self.size = random.uniform(1.0, 2.2)
        self.ph = random.uniform(0, 6.28)
        self.f1 = random.uniform(0.6, 1.6)
        self.f2 = random.uniform(0.6, 1.6)

    def update(self, dt, t):
        self.vx += math.sin(t * self.f1 + self.ph) * 70 * dt
        self.vy += math.cos(t * self.f2 + self.ph * 1.3) * 70 * dt
        damp = math.exp(-0.9 * dt)
        self.vx *= damp
        self.vy *= damp
        sp = math.hypot(self.vx, self.vy)
        if sp < 40:
            if sp < 1e-3:
                self.vx, self.vy, sp = 1.0, 0.0, 1.0
            k = 40 / sp
            self.vx *= k
            self.vy *= k
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.x < 15:
            self.x, self.vx = 15, abs(self.vx)
        elif self.x > W - 15:
            self.x, self.vx = W - 15, -abs(self.vx)
        if self.y < 15:
            self.y, self.vy = 15, abs(self.vy)
        elif self.y > H - 15:
            self.y, self.vy = H - 15, -abs(self.vy)
        self.u += self.du * dt


class Streak:
    """[1. AŞAMA] Merkezden dışarı fırlayan renkli ışık çizgisi (kuyruklu)."""
    __slots__ = ("ca", "sa", "r", "v", "L", "col", "w", "on")
    COLS = [PINK, PURPLE, BLUE, CYAN, GOLD, ORANGE, WHITE, MAGENTA]

    def __init__(self):
        self.on = True
        self.reset(True)

    def reset(self, first=False):
        a = random.uniform(0, 2 * math.pi)
        self.ca, self.sa = math.cos(a), math.sin(a)
        self.v = random.uniform(380, 1050)
        self.L = random.uniform(50, 300)
        self.r = -random.uniform(0, self.v * 0.5) if first else -random.uniform(0, 40)
        self.col = random.choice(self.COLS)
        self.w = random.choice((1, 1, 2, 2, 3))

    def update(self, dt, respawn):
        self.r += self.v * dt
        if self.r - self.L > 520:
            if respawn:
                self.reset()
            else:
                self.on = False


class Shape:
    """[1-2. AŞAMA] Dışarı süzülen küçük içi boş elmas/kare."""
    __slots__ = ("a", "r", "v", "rot", "rv", "size", "col")

    def __init__(self):
        self.a = random.uniform(0, 2 * math.pi)
        self.r = random.uniform(20, 120)
        self.v = random.uniform(40, 130)
        self.rot = random.uniform(0, 6.28)
        self.rv = random.uniform(-1.5, 1.5)
        self.size = random.uniform(4, 8)
        self.col = random.choice([CYAN, PINK, GOLD, WHITE, TEAL])

    def update(self, dt):
        self.r += self.v * dt
        self.rot += self.rv * dt
        if self.r > 480:
            self.r = random.uniform(20, 80)
            self.a = random.uniform(0, 2 * math.pi)


class Cross:
    """[2. AŞAMA] Heykel gibi uzun, ince, kalbin üstünden geçen düz ışık çizgisi."""
    __slots__ = ("x", "y", "ca", "sa", "L", "spd", "col", "ph")

    def __init__(self):
        ang = random.uniform(0, 2 * math.pi)
        self.ca, self.sa = math.cos(ang), math.sin(ang)
        self.x = CX + random.uniform(-260, 260)
        self.y = HC_Y + random.uniform(-200, 200)
        self.L = random.uniform(380, 700)
        self.spd = random.uniform(-70, 70)
        self.col = random.choice([GOLD, PINK, CYAN, PURPLE, WHITE])
        self.ph = random.uniform(0, 6.28)


class Strand:
    """[2. AŞAMA] Kalp hattı boyunca örülen ince, dalgalı bağlar."""
    __slots__ = ("u0", "span", "sc", "k", "ph", "pos")

    def __init__(self):
        self.u0 = random.uniform(0, 2 * math.pi)
        self.span = random.uniform(1.4, 3.4)
        self.sc = random.choice([1.0, 1.0, 0.84, 0.68])
        self.k = random.uniform(3, 8)
        self.ph = random.uniform(0, 6.28)
        self.pos = random.random()


class MiniHeart:
    """[6-7. AŞAMA] Kalbin etrafında uçuşan küçük neon kalp."""
    __slots__ = ("x", "y", "vx", "vy", "size", "life", "age", "ph", "cph", "base")

    def __init__(self, S):
        u = random.uniform(0, 2 * math.pi)
        x, y = heart_screen(u, S)
        dx, dy = x - CX, y - HC_Y
        d = math.hypot(dx, dy) or 1.0
        nx, ny = dx / d, dy / d
        off = random.uniform(10, 60)
        self.x, self.y = x + nx * off, y + ny * off
        sp = random.uniform(12, 35)
        self.vx, self.vy = nx * sp, ny * sp - random.uniform(25, 60)
        self.size = random.uniform(4, 10)
        self.life = random.uniform(3.5, 6.0)
        self.age = 0.0
        self.ph = random.uniform(0, 6.28)
        self.cph = random.uniform(0, 1)
        self.base = random.choice([PINK, CYAN, PURPLE, BLUE, MAGENTA])

    def update(self, dt):
        self.age += dt
        self.x += (self.vx + math.sin(self.age * 2 + self.ph) * 18) * dt
        self.y += self.vy * dt


# ----------------------------------------------------------------------------
# ÇİZİM YARDIMCILARI
# ----------------------------------------------------------------------------
def draw_heart_shape(surf, cx, cy, size, col, bright):
    """Katmanlı (halo + çekirdek) küçük neon kalp."""
    for scale, f in ((1.55, 0.20), (1.25, 0.42)):
        pts = [(cx + ux * size * scale, cy - uy * size * scale) for ux, uy in MINI_UNIT]
        pygame.draw.polygon(surf, ci(col, f * bright), pts)
    pts = [(cx + ux * size, cy - uy * size) for ux, uy in MINI_UNIT]
    pygame.draw.polygon(surf, ci(lerp_col(col, WHITE, 0.2), bright), pts)


def draw_heart_icon(surf, cx, cy, size, col, bright):
    """[9. AŞAMA] Küçük neon kalp simgesi (sadece kontur)."""
    pts = [(cx + ux * size, cy - uy * size) for ux, uy in MINI_UNIT]
    pygame.draw.polygon(surf, ci(col, 0.18 * bright), pts, 8)
    pygame.draw.polygon(surf, ci(col, 0.50 * bright), pts, 4)
    pygame.draw.polygon(surf, ci(lerp_col(col, WHITE, 0.6), bright), pts, 2)


# Zemin ışıltıları için sabit rastgele noktalar
SPARKLES = [(random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(0, 6.28),
             random.uniform(1.5, 4.0)) for _ in range(90)]
# Yatay dalga kuşağı (6. aşama) için sabit rastgele noktalar
RIBBON = [(random.random(), random.gauss(0, 1), random.randrange(3),
           random.uniform(0, 6.28)) for _ in range(260)]


# ----------------------------------------------------------------------------
# SAHNE
# ----------------------------------------------------------------------------
class Scene:
    def __init__(self):
        self.fade = pygame.Surface((W, REFL_H)).convert()
        for y in range(REFL_H):
            v = int(255 * (1 - y / REFL_H) ** 1.7)
            pygame.draw.line(self.fade, (v, v, v), (0, y), (W, y))
        base = pygame.Surface((W, 80)).convert()
        base.fill((0, 0, 0))
        for i in range(10):
            k = 1 - i / 10
            rect = pygame.Rect(0, 0, int(640 * k), max(2, int(70 * k)))
            rect.center = (W // 2, 40)
            v = int(10 + 14 * (i + 1))
            pygame.draw.ellipse(base, (v, v, v), rect)
        small = pygame.transform.smoothscale(base, (W // 8, 10))
        self.floor_glow = pygame.transform.smoothscale(small, (W, 80))
        # [9. AŞAMA] ince, italik el yazısı tarzı "Love"
        names = ("segoescript,brushscriptmt,lucidahandwriting,snellroundhand,zapfino,"
                 "z003,urwchanceryl,chancery,georgia,dejavuserif")
        self.font = pygame.font.SysFont(names, 100, italic=True)
        self.text_white = self.font.render("Love", True, WHITE, (0, 0, 0))
        tw, th = self.text_white.get_size()
        self.text_halo = pygame.Surface((tw + 24, th + 24)).convert()
        self.text_halo.fill((0, 0, 0))
        dim = self.text_white.copy()
        dim.fill((60, 60, 60), special_flags=pygame.BLEND_RGB_MULT)
        for r in (2, 4, 6):
            for k in range(12):
                a = k * math.pi / 6
                self.text_halo.blit(dim, (12 + math.cos(a) * r, 12 + math.sin(a) * r),
                                    special_flags=pygame.BLEND_RGB_ADD)
        self.hud_font = pygame.font.SysFont("arial,dejavusans", 17)
        self.show_hud = True
        self.reset()

    def reset(self):
        self.t = 0.0
        self.parts = [Particle() for _ in range(N_PART)]
        self.streaks = [Streak() for _ in range(110)]
        self.shapes = [Shape() for _ in range(9)]
        self.crosses = [Cross() for _ in range(7)]
        self.strands = [Strand() for _ in range(12)]
        self.minis = []
        self.spawn_acc = 0.0
        self.S = S0

    def update(self, dt):
        self.t += dt
        t = self.t
        for p in self.parts:
            p.update(dt, t)
        respawn = t < T[2] + 1.5
        for s in self.streaks:
            s.update(dt, respawn)
        for s in self.shapes:
            s.update(dt)
        # küçük kalplerin doğuşu
        r = smooth(ramp(t, T_MINI, 3.0))
        self.spawn_acc += dt * 7.0 * r
        while self.spawn_acc >= 1.0:
            self.spawn_acc -= 1.0
            if len(self.minis) < 45:
                self.minis.append(MiniHeart(self.S))
        for m in self.minis:
            m.update(dt)
        self.minis = [m for m in self.minis if m.age < m.life]

    def stage(self):
        return max(i for i, v in T.items() if self.t >= v)

    # ------------------------------------------------------------------
    def render(self, layer):
        t = self.t
        layer.fill((0, 0, 0))

        a1 = 1 - smooth(ramp(t, T[2], 2.5))            # 1. aşama çizgileri sönüyor
        a2 = smooth(ramp(t, T[2], 4.0))
        a3 = smooth(ramp(t, T[3], 4.0))
        att = 0.55 * a2 + 0.45 * a3
        a4 = smooth(ramp(t, T[4], 3.2))
        a5 = smooth(ramp(t, T[5], 3.0))
        amp = smooth(ramp(t, T[6], 2.5))
        a7 = smooth(ramp(t, T[7], 3.0))
        a8 = smooth(ramp(t, T[8], 3.0))
        a9 = ramp(t, T[9], 3.0)

        st = Style()
        st.tm = t
        st.w4 = smooth(ramp(t, T[4], 3.0))
        st.w6 = smooth(ramp(t, T[6], 3.0))
        st.cyc = a8
        st.white = 0.9 * smooth(ramp(t, T[5], 1.5)) * (1 - smooth(ramp(t, T[6] - 0.5, 2.0)))

        ph = ((t - T[6]) * BPM / 60.0) % 1.0 if t >= T[6] else 0.0
        hb = heartbeat(ph) * amp
        S = S0 * (1 + 0.12 * hb)                       # [6. AŞAMA] ölçek = nabız
        self.S = S
        glow = 0.88 + 0.30 * hb
        clean = 1 - 0.9 * smooth(ramp(t, T[9], 3.0))   # 9. aşamada ekstra efektler sönükleşir

        # ---- [3. AŞAMA] yanlarda dalgalanan tel kafes ------------------
        mesh = smooth(ramp(t, T[3], 2.5)) * (1 - smooth(ramp(t, T[4] + 1.5, 2.5)))
        if mesh > 0.01:
            self.draw_mesh(layer, t, mesh)

        # ---- [6. AŞAMA] yatay parçacık dalga kuşağı --------------------
        rib = smooth(ramp(t, T[6], 2.5)) * (1 - smooth(ramp(t, T[9] - 1.0, 2.5)))
        if rib > 0.01:
            self.draw_ribbon(layer, t, st, rib)

        # ---- [1-2. AŞAMA] ışık çizgileri, elmaslar, uzun düz çizgiler ---
        if a1 > 0.01:
            self.draw_streaks(layer, a1)
        self.draw_crosses(layer, t,
                          smooth(ramp(t, T[2] - 1.0, 2.0)) * (1 - smooth(ramp(t, T[3] + 1.0, 3.0))))

        # ---- Ana parçacıklar [1-4. AŞAMA] ------------------------------
        self.draw_particles(layer, t, st, att, a2, a3, a4, S, glow)

        # ---- [2. AŞAMA] ince bağlar ------------------------------------
        sv = a2 * (1 - smooth(ramp(t, T[4], 3.0)))
        if sv > 0.01:
            self.draw_strands(layer, t, st, S, a2, a3, sv)

        # ---- [3-4. AŞAMA] iç içe neon kalp hatları ---------------------
        specs = [(1.0, (13, 7, 3), 1.0), (0.84, (9, 5, 2), 0.85),
                 (0.68, (0, 4, 2), 0.7), (0.52, (0, 3, 1), 0.55)]
        for i, (sc, wd, bri) in enumerate(specs):
            frac = smooth(ramp(t, T[3] + i * 0.6, 3.0))
            if frac > 0.001:
                k = 1 + 0.35 * a4 if i == 0 else 1.0     # ana hat 4. aşamada kalınlaşır
                wd2 = tuple(int(w * k) for w in wd)
                self.draw_outline(layer, S, sc, frac, st, glow * bri * (0.75 + 0.25 * a4), wd2, i)

        # ---- [6. AŞAMA] her atışta dışa yayılan yankı konturu ----------
        if amp > 0.05 and 0.05 < ph < 0.75:
            e = (ph - 0.05) / 0.70
            al = (1 - e) ** 2 * 0.65 * amp
            k = 1 + 0.38 * e
            pts = [(CX + x * S * k, CY - (Y0 + (y - Y0) * k) * S) for x, y in FULL_RAW]
            pygame.draw.lines(layer, ci(heart_color(2.0, st), al), True, pts, 2)

        # ---- [4. AŞAMA] kalbin etrafında dolanan ışık kuyruğu ----------
        if a4 > 0.01:
            self.draw_comet(layer, t, st, a4 * clean)
        # ---- [5. AŞAMA] noktalı orbital halkalar -----------------------
        if a5 > 0.01:
            self.draw_rings(layer, t, st, a5 * clean)
        # ---- [7. AŞAMA] büyük holografik şerit halkalar ----------------
        if a7 > 0.01:
            self.draw_loops(layer, t, st, a7 * clean)

        # ---- küçük neon kalpler ----------------------------------------
        for m in self.minis:
            al = math.sin(math.pi * m.age / m.life) ** 0.6
            col = lerp_col(m.base, cycle_color(t * 0.18 + m.cph), st.cyc)
            draw_heart_shape(layer, m.x, m.y, m.size * (1 + 0.12 * math.sin(m.age * 6 + m.ph)),
                             col, al * 0.95 * clean)

        # ---- [5. AŞAMA] zeminde yansıma, ışıltı ve dalgacıklar ---------
        if a5 > 0.01:
            region = layer.subsurface((0, FLOOR - REFL_H, W, REFL_H))
            refl = pygame.transform.flip(region, False, True)
            refl.blit(self.fade, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
            k = int(255 * 0.85 * a5)
            refl.fill((k, k, k), special_flags=pygame.BLEND_RGB_MULT)
            layer.blit(refl, (0, FLOOR), special_flags=pygame.BLEND_RGB_ADD)
            self.draw_floor(layer, t, st, a5, a8, glow)

        # ---- [9. AŞAMA] yatay ışık çizgileri, "Love" ve simge ----------
        if a9 > 0.001:
            self.draw_hlines(layer, t, st, a9)
            self.draw_love(layer, t, st, a9, hb)

    # ------------------------------------------------------------------
    def draw_streaks(self, layer, fade):
        ox, oy = CX, HC_Y
        for s in self.streaks:
            if not s.on:
                continue
            head = s.r
            tail = max(4.0, head - s.L)
            if head <= tail:
                continue
            prev = tail
            for k in range(1, 5):
                cur = tail + (head - tail) * k / 4
                b = ((k / 4) ** 1.4) * fade
                pygame.draw.line(layer, ci(s.col, 0.95 * b),
                                 (ox + s.ca * prev, oy + s.sa * prev),
                                 (ox + s.ca * cur, oy + s.sa * cur), s.w if k > 2 else 1)
                prev = cur
        for sh in self.shapes:                           # küçük içi boş elmaslar
            x, y = ox + math.cos(sh.a) * sh.r, oy + math.sin(sh.a) * sh.r
            pts = [(x + math.cos(sh.rot + k * math.pi / 2) * sh.size,
                    y + math.sin(sh.rot + k * math.pi / 2) * sh.size) for k in range(4)]
            pygame.draw.polygon(layer, ci(sh.col, 0.9 * fade), pts, 1)

    def draw_crosses(self, layer, t, a):
        if a < 0.01:
            return
        for c in self.crosses:
            s0 = c.spd * t
            n = 12
            for k in range(n):
                f0, f1 = k / n, (k + 1) / n
                b = math.sin(math.pi * (f0 + f1) * 0.5) ** 1.5 * a * (0.6 + 0.4 * math.sin(t * 2 + c.ph))
                p0 = (c.x + c.ca * (s0 + c.L * f0 - c.L / 2), c.y + c.sa * (s0 + c.L * f0 - c.L / 2))
                p1 = (c.x + c.ca * (s0 + c.L * f1 - c.L / 2), c.y + c.sa * (s0 + c.L * f1 - c.L / 2))
                pygame.draw.line(layer, ci(c.col, 0.8 * b), p0, p1, 1)

    def draw_mesh(self, layer, t, a):
        """[3. AŞAMA] Kalbin iki yanından yükselen altın/turkuaz tel kafes dalga."""
        rows, cols, span = 10, 14, 360
        for side in (0, 1):
            sgn = -1 if side == 0 else 1
            grid = []
            for j in range(rows):
                row = []
                for i in range(cols):
                    f = i / (cols - 1)                    # 0: kenar, 1: kalbe yakın
                    d = f * span
                    x = CX + sgn * (CX - d)
                    y = (HC_Y + 150 - j * 26 + 55 * math.sin(d * 0.012 + t * 0.8 + j * 0.28)
                         - d * 0.55 - (1 - f) * 40)
                    row.append((x, y))
                grid.append(row)
            col = GOLD if side == 0 else TEAL
            vcol = lerp_col(col, PINK, 0.4)
            for j in range(rows):
                for i in range(cols - 1):
                    b = (1 - (i + 0.5) / (cols - 1)) ** 0.9 * a
                    pygame.draw.line(layer, ci(col, 0.5 * b), grid[j][i], grid[j][i + 1], 1)
            for i in range(cols):
                b = (1 - i / (cols - 1)) ** 0.9 * a
                for j in range(rows - 1):
                    pygame.draw.line(layer, ci(vcol, 0.42 * b), grid[j][i], grid[j + 1][i], 1)

    def draw_ribbon(self, layer, t, st, a):
        """[6. AŞAMA] Kalbin arkasından geçen parıldayan parçacık dalgası."""
        for s, off, wave, ph in RIBBON:
            x = s * W
            env = 0.35 + 0.65 * min(1.0, abs(x - CX) / 260.0)
            y = (HC_Y + 70 + (60 + 25 * wave) * env *
                 math.sin(x * 0.0085 + t * 1.1 + wave * 2.1)) + off * (6 + 10 * env)
            col = lerp_col(pal([PINK, PURPLE, BLUE, CYAN], s), cycle_color(t * 0.18 + s * 0.4), st.cyc)
            b = a * (0.45 + 0.55 * math.sin(t * 3 + ph) ** 2)
            pygame.draw.circle(layer, ci(col, 0.25 * b), (int(x), int(y)), 3)
            pygame.draw.circle(layer, ci(lerp_col(col, WHITE, 0.4), b), (int(x), int(y)), 1)

    def draw_particles(self, layer, t, st, att, a2, a3, a4, S, glow):
        appear = ramp(t, 0.0, 0.8)
        jit = 1.0 + 9.0 * a2 * (1 - a3)
        mix_to_heart = max(0.85 * a3, st.cyc)
        pull = 1 - (1 - att) ** 2
        fade_late = 1 - 0.5 * a4                          # kalp tamamlanınca parçacıklar sönükleşir
        cores = []
        for p in self.parts:
            tx, ty = heart_screen(p.u, S, p.sc)
            x = lerp(p.x, tx, pull)
            y = lerp(p.y, ty, pull)
            if jit > 1.01:
                x += math.sin(t * 3.1 + p.ph) * jit
                y += math.cos(t * 2.7 + p.ph * 1.7) * jit
            col = lerp_col(p.base, heart_color(p.u, st, p.sc), mix_to_heart)
            br = (0.6 + 0.4 * att) * appear * glow * fade_late
            r = p.size * (0.9 + 0.25 * math.sin(t * 2.5 + p.ph)) * (1 + 0.35 * att)
            ix, iy = int(x), int(y)
            pygame.draw.circle(layer, ci(col, 0.16 * br), (ix, iy), max(2, int(r * 3.2)))
            pygame.draw.circle(layer, ci(col, 0.38 * br), (ix, iy), max(1, int(r * 1.9)))
            cores.append((ix, iy, r, col, br))
        for ix, iy, r, col, br in cores:
            pygame.draw.circle(layer, ci(lerp_col(col, WHITE, 0.55), br), (ix, iy), max(1, int(r)))

    def draw_strands(self, layer, t, st, S, a2, a3, vis):
        amp = 9.0 * (1 - a3)
        for s in self.strands:
            n = 26
            f = a2
            pts = []
            for j in range(n + 1):
                u = s.u0 + s.span * f * j / n
                x, y = heart_screen(u, S, s.sc)
                w = math.sin(u * s.k + s.ph + t * 1.5) * amp
                pts.append((x + w, y + math.cos(u * s.k + s.ph + t) * amp))
            col = lerp_col(pal([PINK, CYAN, GOLD], s.pos), heart_color(s.u0, st), st.w4)
            pygame.draw.lines(layer, ci(col, 0.9 * vis), False, pts, 1)

    def draw_outline(self, layer, S, sc, frac, st, bri, widths, idx):
        """Kalp hattı alt uçtan iki yana kendini çizer (üç katmanlı neon çizgi)."""
        wh, wm, wc = widths
        n = int(OUT_M * frac)
        if n < 1:
            return
        for side, raw in ((0, RIGHT_RAW), (1, LEFT_RAW)):
            pts = [(CX + x * sc * S, CY - (Y0 + (y - Y0) * sc) * S) for x, y in raw[:n + 1]]
            col = None
            for k in range(len(pts) - 1):
                if k % 2 == 0:
                    u = (math.pi - math.pi * k / OUT_M) if side == 0 else (math.pi + math.pi * k / OUT_M)
                    col = heart_color(u, st, idx * 0.7)
                p0, p1 = pts[k], pts[k + 1]
                if wh:
                    pygame.draw.line(layer, ci(col, 0.17 * bri), p0, p1, wh)
                pygame.draw.line(layer, ci(col, 0.50 * bri), p0, p1, wm)
                pygame.draw.line(layer, ci(lerp_col(col, WHITE, 0.55), 0.95 * bri), p0, p1, wc)

    def draw_comet(self, layer, t, st, a):
        """[4. AŞAMA] Kalbi saran kuyruklu ışık (ellips boyunca incelen iz)."""
        head = t * 1.3
        spin = t * 0.5
        prev = None
        for k in range(36):
            ang = head - k * 0.045
            x, y, z = ring_point(COMET, ang, spin)
            b = (1 - k / 36.0) ** 1.6 * a * (0.45 + 0.55 * (z * 0.5 + 0.5))
            col = heart_color(ang, st, 1.0)
            if prev:
                w = max(1, int(6 * (1 - k / 36.0)))
                pygame.draw.line(layer, ci(col, 0.35 * b), prev, (x, y), w + 4)
                pygame.draw.line(layer, ci(lerp_col(col, WHITE, 0.5), 0.9 * b), prev, (x, y), w)
            prev = (x, y)

    def draw_rings(self, layer, t, st, a5):
        """[5. AŞAMA] Kalbin etrafında dönen noktalı orbital ışık halkaları."""
        base = [CYAN, PINK, PURPLE]
        n = 110
        for i, ring in enumerate(RINGS):
            col = lerp_col(base[i], cycle_color(t * 0.18 + i * 0.25), st.cyc)
            col = lerp_col(col, WHITE, 0.5 * st.white)
            spin = t * ring["speed"]
            prev = None
            for j in range(n + 1):
                x, y, z = ring_point(ring, 2 * math.pi * j / n, spin)
                b = (0.25 + 0.75 * (z * 0.5 + 0.5)) * a5
                if prev:
                    pygame.draw.line(layer, ci(col, 0.30 * b), prev, (x, y), 1)
                if j < n:
                    pygame.draw.circle(layer, ci(lerp_col(col, WHITE, 0.5), b), (int(x), int(y)), 2 if j % 3 == 0 else 1)
                prev = (x, y)
            ang = t * (1.4 + 0.5 * i) * (1 if ring["speed"] > 0 else -1)
            bx, by, bz = ring_point(ring, ang, spin)
            bb = (0.5 + 0.5 * (bz * 0.5 + 0.5)) * a5
            pygame.draw.circle(layer, ci(col, 0.25 * bb), (int(bx), int(by)), 11)
            pygame.draw.circle(layer, ci(col, 0.6 * bb), (int(bx), int(by)), 6)
            pygame.draw.circle(layer, ci(WHITE, bb), (int(bx), int(by)), 3)

    def draw_loops(self, layer, t, st, a7):
        """[7. AŞAMA] Kalbi saran büyük, holografik renkli şerit halkalar."""
        n = 64
        for i, ring in enumerate(LOOPS):
            spin = t * ring["speed"] + i * 1.7
            for d, wd, bf in ((-8, 1, 0.45), (0, 2, 1.0), (8, 1, 0.45)):
                prev = None
                for j in range(n + 1):
                    x, y, z = ring_point(ring, 2 * math.pi * j / n, spin, ring["R"] + d)
                    if prev:
                        hp = j / n + t * 0.08 + i * 0.3
                        col = lerp_col(cyc_pal(HOLO, hp), cycle_color(t * 0.18 + hp * 0.5), st.cyc)
                        b = (0.2 + 0.8 * (z * 0.5 + 0.5)) * a7 * bf
                        pygame.draw.line(layer, ci(col, 0.9 * b), prev, (x, y), wd)
                    prev = (x, y)

    def draw_floor(self, layer, t, st, a5, a8, glow):
        fc = heart_color(0.5, st)
        fg = self.floor_glow.copy()
        fg.fill(ci(fc, 0.55 * a5 * glow), special_flags=pygame.BLEND_RGB_MULT)
        layer.blit(fg, (0, FLOOR - 40), special_flags=pygame.BLEND_RGB_ADD)
        # yayılan zemin dalgacıkları
        for i in range(5):
            p = (t * 0.28 + i / 5.0) % 1.0
            rx = 30 + 330 * p
            ry = max(2.0, rx * 0.11)
            b = (1 - p) ** 1.4 * a5
            rect = pygame.Rect(0, 0, int(rx * 2), int(ry * 2))
            rect.center = (CX, FLOOR)
            pygame.draw.ellipse(layer, ci(fc, 0.25 * b), rect.inflate(6, 4), 4)
            pygame.draw.ellipse(layer, ci(lerp_col(fc, WHITE, 0.35), 0.85 * b), rect, 1)
        # [8. AŞAMA] zeminde parıldayan ışıltılar
        if a8 > 0.01:
            for sx, sy, ph, sp in SPARKLES:
                x = CX + sx * 340
                y = FLOOR + sy * 30 * (1 - abs(sx) * 0.5)
                b = a8 * max(0.0, math.sin(t * sp + ph)) ** 2
                if b > 0.05:
                    col = cycle_color(t * 0.18 + sx * 0.3 + ph)
                    pygame.draw.circle(layer, ci(col, 0.35 * b), (int(x), int(y)), 3)
                    pygame.draw.circle(layer, ci(WHITE, b), (int(x), int(y)), 1)

    def draw_hlines(self, layer, t, st, a9):
        """[9. AŞAMA] Kalbin iki yanından uzanan yatay ışık çizgileri ve boncukları."""
        offs = [-72, -42, -14, 14, 42, 72, 100]
        for idx, dy in enumerate(offs):
            y = HC_Y + dy
            L = 200 + (idx % 3) * 45 + 60
            col = lerp_col(pal([PINK, PURPLE, BLUE, CYAN], idx / 6.0), cycle_color(t * 0.18 + idx * 0.1), st.cyc)
            sb = (t * 0.11 + idx * 0.19) % 1.0
            for sgn in (-1, 1):
                n = 16
                for k in range(n):
                    f0, f1 = k / n, (k + 1) / n
                    fm = (f0 + f1) * 0.5
                    b = (1 - fm) ** 0.8 * 0.45 + 1.4 * math.exp(-((fm - sb) / 0.05) ** 2)
                    b *= a9
                    x0 = CX + sgn * (178 + L * f0)
                    x1 = CX + sgn * (178 + L * f1)
                    pygame.draw.line(layer, ci(col, 0.9 * min(1.3, b)), (x0, y), (x1, y), 1)
                bx = CX + sgn * (178 + L * sb)
                pygame.draw.circle(layer, ci(col, 0.3 * a9), (int(bx), int(y)), 5)
                pygame.draw.circle(layer, ci(WHITE, 0.9 * a9), (int(bx), int(y)), 2)

    def draw_love(self, layer, t, st, a9, hb):
        """[9. AŞAMA] Neon "Love" yazısı + altında çizgi ve küçük kalp simgesi."""
        flick = 1 - 0.65 * max(0.0, math.sin(t * 45) * math.sin(t * 29)) * (1 - a9)
        f = smooth(a9) * flick
        if f < 0.01:
            return
        col = heart_color(1.0, st)
        tw, th = self.text_white.get_size()
        x = CX - tw // 2
        y = TEXT_Y - th // 2
        halo = self.text_halo.copy()
        halo.fill(ci(col, 0.55 * f), special_flags=pygame.BLEND_RGB_MULT)
        layer.blit(halo, (x - 12, y - 12), special_flags=pygame.BLEND_RGB_ADD)
        core = self.text_white.copy()
        core.fill(ci(lerp_col(col, WHITE, 0.75), f), special_flags=pygame.BLEND_RGB_MULT)
        layer.blit(core, (x, y), special_flags=pygame.BLEND_RGB_ADD)
        # alt çizgi + küçük neon kalp simgesi
        lc = lerp_col(col, WHITE, 0.5)
        for sgn in (-1, 1):
            for k in range(10):
                f0, f1 = k / 10, (k + 1) / 10
                b = (1 - (f0 + f1) * 0.5) ** 0.7 * f
                pygame.draw.line(layer, ci(lc, 0.85 * b), (CX + sgn * (26 + 150 * f0), RULE_Y),
                                 (CX + sgn * (26 + 150 * f1), RULE_Y), 1)
        draw_heart_icon(layer, CX, RULE_Y + 2, 11 * (1 + 0.08 * hb), heart_color(3.0, st), f)


# ----------------------------------------------------------------------------
# BLOOM: katmanlı glow/blur (küçültüp büyütme + toplamalı karıştırma)
# ----------------------------------------------------------------------------
def compose(screen, layer):
    small = pygame.transform.smoothscale(layer, (W // 4, H // 4))
    tiny = pygame.transform.smoothscale(small, (W // 14, H // 14))
    b1 = pygame.transform.smoothscale(small, (W, H))
    b2 = pygame.transform.smoothscale(tiny, (W, H))
    screen.blit(layer, (0, 0))
    screen.blit(b1, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    screen.blit(b2, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    screen.blit(b2, (0, 0), special_flags=pygame.BLEND_RGB_ADD)


# ----------------------------------------------------------------------------
# ANA DÖNGÜ
# ----------------------------------------------------------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Neon Parçacıklarla Kalbin Doğuşu")
    clock = pygame.time.Clock()
    layer = pygame.Surface((W, H)).convert()
    scene = Scene()
    paused = False

    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif ev.key == pygame.K_SPACE:
                    paused = not paused
                elif ev.key == pygame.K_r:
                    scene.reset()
                elif ev.key == pygame.K_h:
                    scene.show_hud = not scene.show_hud
                elif pygame.K_1 <= ev.key <= pygame.K_9:
                    n = ev.key - pygame.K_0
                    scene.t = T[n]
                    if n < 6:
                        scene.minis.clear()

        if not paused:
            scene.update(dt)
        scene.render(layer)
        compose(screen, layer)

        if scene.show_hud:
            st = scene.stage()
            label = "Aşama %d/9 — %s" % (st, STAGE_NAMES[st])
            screen.blit(scene.hud_font.render(label, True, (110, 110, 140)), (14, 10))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
