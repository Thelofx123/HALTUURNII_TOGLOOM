from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pygame

from .constants import DASH_COOLDOWN_MS
from .utils import load_pixel_font


DASH_COOLDOWN = DASH_COOLDOWN_MS / 1000.0


@dataclass
class HudPalette:
    hp_color: tuple[int, int, int] = (214, 84, 84)
    stamina_color: tuple[int, int, int] = (96, 186, 146)
    bar_bg: tuple[int, int, int] = (32, 36, 44)
    outline: tuple[int, int, int] = (235, 235, 245)
    dash_ready: tuple[int, int, int] = (120, 200, 255)
    dash_wait: tuple[int, int, int] = (110, 110, 140)


class HudRenderer:
    """Draws core player stats."""

    def __init__(self, palette: Optional[HudPalette] = None) -> None:
        self.palette = palette or HudPalette()
        self.font = load_pixel_font(16)
        self.small = load_pixel_font(14)
        self.big = load_pixel_font(24)
        self._level_up_timer = 0.0
        self._level_up_text = ""

    def notify_level_up(self, level: int) -> None:
        self._level_up_timer = 2.0
        self._level_up_text = f"LEVEL UP! Lv {level}"

    def update(self, dt: float) -> None:
        if self._level_up_timer > 0.0:
            self._level_up_timer = max(0.0, self._level_up_timer - dt)

    def draw(self, surface: pygame.Surface, player, dash_cooldown: float) -> None:
        rect_hp = pygame.Rect(24, 24, 240, 18)
        rect_stamina = pygame.Rect(24, 52, 240, 12)
        self._draw_bar(surface, rect_hp, player.hp / max(1, player.max_hp), self.palette.hp_color)
        self._draw_bar(surface, rect_stamina, player.stamina / 100.0, self.palette.stamina_color)

        hp_text = self.font.render(f"HP {int(player.hp)}/{player.max_hp}", True, self.palette.outline)
        surface.blit(hp_text, (rect_hp.x, rect_hp.y - 20))
        stamina_text = self.small.render(f"STM {int(player.stamina)}", True, self.palette.outline)
        surface.blit(stamina_text, (rect_stamina.x, rect_stamina.y - 18))

        dash_rect = pygame.Rect(24, 76, 120, 12)
        if DASH_COOLDOWN > 0:
            pct = 1.0 - min(1.0, dash_cooldown / DASH_COOLDOWN)
        else:
            pct = 1.0
        dash_color = self.palette.dash_ready if pct >= 0.999 else self.palette.dash_wait
        self._draw_bar(surface, dash_rect, pct, dash_color)
        label = "Dash Ready" if pct >= 0.999 else f"Dash {dash_cooldown:.1f}s"
        surface.blit(self.small.render(label, True, self.palette.outline), (dash_rect.x, dash_rect.y + 14))

        level = player.leveling.level
        xp = player.leveling.xp
        xp_to_next = player.leveling.xp_to_next
        xp_text = self.small.render(f"Lv {level}  XP {xp}/{xp_to_next}", True, self.palette.outline)
        surface.blit(xp_text, (24, 110))

        if self._level_up_timer > 0.0:
            text = self.big.render(self._level_up_text, True, self.palette.outline)
            x = surface.get_width() // 2 - text.get_width() // 2
            surface.blit(text, (x, 32))

    def _draw_bar(self, surface: pygame.Surface, rect: pygame.Rect, pct: float, color: tuple[int, int, int]) -> None:
        pct = max(0.0, min(1.0, pct))
        pygame.draw.rect(surface, self.palette.bar_bg, rect)
        fill = rect.copy()
        fill.width = int(rect.width * pct)
        if fill.width > 0:
            pygame.draw.rect(surface, color, fill)
        pygame.draw.rect(surface, self.palette.outline, rect, 1)
