from __future__ import annotations

import os
from typing import Iterable, List, Tuple

import pygame


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def vnorm(vec: pygame.Vector2) -> pygame.Vector2:
    if vec.length_squared():
        vec = vec.normalize()
    return vec


_warned_anim_paths: set[str] = set()


def load_anim_folder(
    path: str, size: Tuple[int, int] = (32, 32), colorkey=None
) -> List[pygame.Surface]:
    """Load animation frames from a folder with graceful fallbacks."""

    frames: List[pygame.Surface] = []
    if os.path.isdir(path):
        for name in sorted(os.listdir(path)):
            if not name.lower().endswith(".png"):
                continue
            file_path = os.path.join(path, name)
            try:
                img = pygame.image.load(file_path).convert_alpha()
            except pygame.error:
                continue
            if colorkey is not None:
                img.set_colorkey(colorkey)
            frames.append(img)

    if not frames:
        if path not in _warned_anim_paths:
            print(f"[warn] missing animation frames at {path}, using placeholders")
            _warned_anim_paths.add(path)
        for idx in range(4):
            surf = pygame.Surface(size, pygame.SRCALPHA)
            color = (120 + idx * 20) % 255
            surf.fill((color, 60 + idx * 25, 90 + idx * 30))
            pygame.draw.rect(surf, (20, 20, 30), surf.get_rect(), 2)
            frames.append(surf)
    return frames


_warned_fonts: set[int] = set()


def load_pixel_font(size: int) -> pygame.font.Font:
    """Load a pixel font with graceful fallback."""

    path = os.path.join("assets", "fonts", "pixel.ttf")
    if os.path.isfile(path):
        try:
            return pygame.font.Font(path, size)
        except pygame.error:
            print(f"[warn] failed to load pixel font at {path}, falling back")

    if size not in _warned_fonts:
        print(f"[warn] pixel font missing, using default at size {size}")
        _warned_fonts.add(size)
    return pygame.font.SysFont("Courier New", size)


def iter_sprites_rects(group: Iterable[pygame.sprite.Sprite]) -> Iterable[pygame.Rect]:
    for sprite in group:
        rect = getattr(sprite, "rect", None)
        if rect:
            yield rect
