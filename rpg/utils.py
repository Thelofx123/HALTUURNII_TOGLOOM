"""Utility helpers for math, assets, and UI support."""

from __future__ import annotations

import os
from pathlib import Path
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


# ---------------------------------------------------------------------------
# Asset helpers --------------------------------------------------------------

_sheet_cache: dict[tuple[str, float], list[pygame.Surface]] = {}
_tile_cache: dict[tuple[str, float], pygame.Surface] = {}


def _slice_sheet(
    image: pygame.Surface,
    tile_size: Tuple[int, int],
    *,
    scale: float = 1.0,
    spacing: int = 0,
    margin: int = 0,
) -> List[pygame.Surface]:
    """Split a sprite sheet into individual frames."""

    tile_w, tile_h = tile_size
    width, height = image.get_size()
    frames: List[pygame.Surface] = []

    y = margin
    while y + tile_h <= height - margin + spacing:
        x = margin
        while x + tile_w <= width - margin + spacing:
            frame = pygame.Surface((tile_w, tile_h), pygame.SRCALPHA)
            frame.blit(image, (0, 0), pygame.Rect(x, y, tile_w, tile_h))
            if scale != 1.0:
                w = max(1, int(tile_w * scale))
                h = max(1, int(tile_h * scale))
                frame = pygame.transform.scale(frame, (w, h))
            frames.append(frame)
            x += tile_w + spacing
        y += tile_h + spacing
    return frames


def load_sheet(
    path: str | os.PathLike[str],
    tile_size: Tuple[int, int],
    *,
    scale: float = 1.0,
    spacing: int = 0,
    margin: int = 0,
) -> List[pygame.Surface]:
    """Load and split a sprite sheet, caching the result."""

    key = (os.fspath(path), scale)
    if key in _sheet_cache:
        return [frame.copy() for frame in _sheet_cache[key]]

    surface = pygame.image.load(os.fspath(path)).convert_alpha()
    frames = _slice_sheet(surface, tile_size, scale=scale, spacing=spacing, margin=margin)
    _sheet_cache[key] = [frame.copy() for frame in frames]
    return [frame.copy() for frame in frames]


def load_desert_tile(category: str, index: int, *, scale: float = 1.0) -> pygame.Surface:
    """Load a single tile from the desert shooter asset pack."""

    base = Path("assets") / "desert-shooter" / "PNG" / category / "Tiles" / f"tile_{index:04d}.png"
    key = (str(base), scale)
    if key in _tile_cache:
        return _tile_cache[key].copy()
    if not base.is_file():
        raise FileNotFoundError(f"Missing desert shooter tile: {base}")
    surface = pygame.image.load(str(base)).convert_alpha()
    if scale != 1.0:
        w = max(1, int(surface.get_width() * scale))
        h = max(1, int(surface.get_height() * scale))
        surface = pygame.transform.scale(surface, (w, h))
    _tile_cache[key] = surface
    return surface.copy()


def load_desert_sheet(category: str, *, scale: float = 1.0) -> List[pygame.Surface]:
    """Convenience wrapper for loading packed tilemaps from the asset pack."""

    base = Path("assets") / "desert-shooter" / "PNG" / category / "Tilemap" / "tilemap_packed.png"
    if not base.is_file():
        raise FileNotFoundError(f"Missing desert shooter sheet: {base}")
    return load_sheet(base, (24, 24), scale=scale)
