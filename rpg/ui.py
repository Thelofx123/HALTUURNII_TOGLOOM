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
    bar_bg: tuple[int, int, int] = (26, 28, 36)
    outline: tuple[int, int, int] = (235, 235, 245)
    dash_ready: tuple[int, int, int] = (120, 200, 255)
    dash_wait: tuple[int, int, int] = (110, 110, 140)
    panel_bg: tuple[int, int, int] = (16, 18, 24)
    panel_shadow: tuple[int, int, int] = (0, 0, 0)
    state_idle: tuple[int, int, int] = (180, 180, 210)
    state_attack: tuple[int, int, int] = (255, 150, 110)
    state_dash: tuple[int, int, int] = (140, 200, 255)


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
        margin = 24
        panel_height = 150
        panel_width = 260
        panel_top = surface.get_height() - margin - panel_height
        panel = pygame.Rect(margin, panel_top, panel_width, panel_height)
        self._draw_panel(surface, panel)

        bar_left = panel.x + 16
        rect_hp = pygame.Rect(bar_left, panel.y + 18, panel.width - 32, 20)
        rect_stamina = pygame.Rect(bar_left, rect_hp.bottom + 12, panel.width - 32, 14)
        self._draw_bar(surface, rect_hp, player.hp / max(1.0, player.max_hp), self.palette.hp_color)
        self._draw_bar(
            surface,
            rect_stamina,
            player.stamina / max(1.0, player.max_stamina),
            self.palette.stamina_color,
        )

        hp_text = self.font.render(f"HP {int(player.hp)}/{int(player.max_hp)}", True, self.palette.outline)
        surface.blit(hp_text, (bar_left, rect_hp.y - 18))
        stamina_text = self.small.render(f"STM {player.stamina:05.1f}", True, self.palette.outline)
        surface.blit(stamina_text, (bar_left, rect_stamina.y - 16))

        dash_rect = pygame.Rect(bar_left, rect_stamina.bottom + 16, panel.width - 32, 14)
        pct = 1.0 - min(1.0, dash_cooldown / DASH_COOLDOWN) if DASH_COOLDOWN > 0 else 1.0
        dash_color = self.palette.dash_ready if pct >= 0.999 else self.palette.dash_wait
        self._draw_bar(surface, dash_rect, pct, dash_color)
        dash_label = "Dash Ready" if pct >= 0.999 else f"Dash {dash_cooldown:.1f}s"
        surface.blit(self.small.render(dash_label, True, self.palette.outline), (bar_left, dash_rect.y - 16))

        self._draw_facing(surface, panel, player)
        self._draw_state(surface, panel, player)

        level = player.leveling.level
        xp = player.leveling.xp
        xp_to_next = player.leveling.xp_to_next
        xp_text = self.small.render(f"Lv {level}  XP {xp}/{xp_to_next}", True, self.palette.outline)
        surface.blit(xp_text, (bar_left, dash_rect.bottom + 12))

        if self._level_up_timer > 0.0:
            text = self.big.render(self._level_up_text, True, self.palette.outline)
            x = surface.get_width() // 2 - text.get_width() // 2
            surface.blit(text, (x, panel.y - 40))

    def _draw_bar(self, surface: pygame.Surface, rect: pygame.Rect, pct: float, color: tuple[int, int, int]) -> None:
        pct = max(0.0, min(1.0, pct))
        pygame.draw.rect(surface, self.palette.bar_bg, rect, border_radius=6)
        fill = rect.copy()
        fill.width = int(rect.width * pct)
        if fill.width > 0:
            pygame.draw.rect(surface, color, fill, border_radius=6)
        pygame.draw.rect(surface, self.palette.outline, rect, 1, border_radius=6)

    def _draw_panel(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        shadow = rect.move(4, 6)
        pygame.draw.rect(surface, self.palette.panel_shadow, shadow, border_radius=12)
        pygame.draw.rect(surface, self.palette.panel_bg, rect, border_radius=12)
        pygame.draw.rect(surface, self.palette.outline, rect, 2, border_radius=12)

    def _draw_facing(self, surface: pygame.Surface, panel: pygame.Rect, player) -> None:
        area = pygame.Rect(panel.x + panel.width - 72, panel.y + 20, 48, 48)
        pygame.draw.rect(surface, self.palette.bar_bg, area, border_radius=8)
        pygame.draw.rect(surface, self.palette.outline, area, 1, border_radius=8)
        arrow_center = area.center
        size = 18
        if player.facing == "right":
            points = [
                (arrow_center[0] + size // 2, arrow_center[1]),
                (arrow_center[0] - size // 2, arrow_center[1] - size // 2),
                (arrow_center[0] - size // 2, arrow_center[1] + size // 2),
            ]
        else:
            points = [
                (arrow_center[0] - size // 2, arrow_center[1]),
                (arrow_center[0] + size // 2, arrow_center[1] - size // 2),
                (arrow_center[0] + size // 2, arrow_center[1] + size // 2),
            ]
        pygame.draw.polygon(surface, self.palette.outline, points)
        label = self.small.render("Facing", True, self.palette.outline)
        surface.blit(label, (area.x, area.bottom + 4))

    def _draw_state(self, surface: pygame.Surface, panel: pygame.Rect, player) -> None:
        base = pygame.Rect(panel.x + 16, panel.bottom - 36, panel.width - 32, 20)
        if player.state == "attack":
            color = self.palette.state_attack
            text = "ATTACKING"
        elif player.state == "dash":
            color = self.palette.state_dash
            text = "DASHING"
        elif player.move_intent.length_squared() > 0:
            color = self.palette.state_idle
            text = "MOVING"
        else:
            color = self.palette.state_idle
            text = "IDLE"
        pygame.draw.rect(surface, color, base, border_radius=6)
        pygame.draw.rect(surface, self.palette.outline, base, 1, border_radius=6)
        label = self.font.render(text, True, self.palette.panel_bg)
        label_rect = label.get_rect(center=base.center)
        surface.blit(label, label_rect)
