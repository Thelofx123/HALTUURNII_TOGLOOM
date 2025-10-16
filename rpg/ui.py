from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pygame

from .constants import DASH_COOLDOWN_MS
from .inventory import Inventory
from .utils import load_desert_tile, load_pixel_font


DASH_COOLDOWN = DASH_COOLDOWN_MS / 1000.0


def draw_text_with_shadow(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    color: tuple[int, int, int],
    pos: tuple[int, int],
    *,
    shadow_offset: tuple[int, int] = (1, 1),
    shadow_color: tuple[int, int, int] = (0, 0, 0),
) -> pygame.Surface:
    shadow = font.render(text, True, shadow_color)
    if shadow_offset != (0, 0):
        surface.blit(shadow, (pos[0] + shadow_offset[0], pos[1] + shadow_offset[1]))
    text_surface = font.render(text, True, color)
    surface.blit(text_surface, pos)
    return text_surface


@dataclass
class HudPalette:
    hp_color: tuple[int, int, int] = (232, 96, 88)
    stamina_color: tuple[int, int, int] = (124, 196, 166)
    bar_bg: tuple[int, int, int] = (32, 24, 20)
    outline: tuple[int, int, int] = (252, 236, 208)
    dash_ready: tuple[int, int, int] = (236, 222, 148)
    dash_wait: tuple[int, int, int] = (176, 148, 120)
    panel_bg: tuple[int, int, int] = (28, 22, 18)
    panel_shadow: tuple[int, int, int] = (12, 8, 6)
    panel_highlight: tuple[int, int, int] = (92, 72, 48)
    state_idle: tuple[int, int, int] = (240, 214, 174)
    state_attack: tuple[int, int, int] = (255, 174, 120)
    state_dash: tuple[int, int, int] = (214, 198, 255)


class HudRenderer:
    """Draws core player stats."""

    def __init__(self, palette: Optional[HudPalette] = None) -> None:
        self.palette = palette or HudPalette()
        self.font = load_pixel_font(16)
        self.small = load_pixel_font(14)
        self.big = load_pixel_font(24)
        self._level_up_timer = 0.0
        self._level_up_text = ""
        self._panel_texture = self._load_panel_texture()

    def notify_level_up(self, level: int) -> None:
        self._level_up_timer = 2.0
        self._level_up_text = f"LEVEL UP! Lv {level}"

    def _load_panel_texture(self) -> Optional[pygame.Surface]:
        try:
            return load_desert_tile("Interface", 0, scale=2.0)
        except FileNotFoundError:
            return None

    def update(self, dt: float) -> None:
        if self._level_up_timer > 0.0:
            self._level_up_timer = max(0.0, self._level_up_timer - dt)

    def draw(self, surface: pygame.Surface, player, dash_cooldown: float) -> None:
        margin = 24
        panel_height = 176
        panel_width = 260
        panel_top = surface.get_height() - margin - panel_height
        panel = pygame.Rect(margin, panel_top, panel_width, panel_height)
        self._draw_panel(surface, panel)

        bar_left = panel.x + 16
        rect_hp = pygame.Rect(bar_left, panel.y + 24, panel.width - 32, 20)
        rect_stamina = pygame.Rect(bar_left, rect_hp.bottom + 18, panel.width - 32, 14)
        self._draw_bar(surface, rect_hp, player.hp / max(1.0, player.max_hp), self.palette.hp_color)
        self._draw_bar(
            surface,
            rect_stamina,
            player.stamina / max(1.0, player.max_stamina),
            self.palette.stamina_color,
        )

        draw_text_with_shadow(
            surface,
            self.font,
            f"HP {int(player.hp)}/{int(player.max_hp)}",
            self.palette.outline,
            (bar_left, rect_hp.y - 20),
        )
        draw_text_with_shadow(
            surface,
            self.small,
            f"STM {player.stamina:05.1f}",
            self.palette.outline,
            (bar_left, rect_stamina.y - 18),
        )

        dash_rect = pygame.Rect(bar_left, rect_stamina.bottom + 24, panel.width - 32, 14)
        pct = 1.0 - min(1.0, dash_cooldown / DASH_COOLDOWN) if DASH_COOLDOWN > 0 else 1.0
        dash_color = self.palette.dash_ready if pct >= 0.999 else self.palette.dash_wait
        self._draw_bar(surface, dash_rect, pct, dash_color)
        dash_label = "Dash Ready" if pct >= 0.999 else f"Dash {dash_cooldown:.1f}s"
        draw_text_with_shadow(surface, self.small, dash_label, self.palette.outline, (bar_left, dash_rect.y - 16))

        self._draw_facing(surface, panel, player)
        self._draw_state(surface, panel, player)

        level = player.leveling.level
        xp = player.leveling.xp
        xp_to_next = player.leveling.xp_to_next
        xp_text = f"XP {xp}/{xp_to_next}"
        xp_y = dash_rect.bottom + 16
        level_radius = self.small.get_height() // 2 + 4
        level_center = (bar_left + level_radius, xp_y + self.small.get_height() // 2)
        pygame.draw.circle(surface, self.palette.bar_bg, level_center, level_radius)
        pygame.draw.circle(surface, self.palette.outline, level_center, level_radius, 2)
        level_surface = self.small.render(str(level), True, self.palette.outline)
        level_rect = level_surface.get_rect(center=level_center)
        surface.blit(level_surface, level_rect)

        xp_text_x = level_center[0] + level_radius + 8
        draw_text_with_shadow(surface, self.small, xp_text, self.palette.outline, (xp_text_x, xp_y))

        line_y = xp_y + self.small.get_height() + 4
        gold_text = f"Gold: {player.gold}"
        draw_text_with_shadow(surface, self.small, gold_text, self.palette.outline, (xp_text_x, line_y))

        weapon_label = f"Weapon: {player.weapon_item.name}"
        weapon_width, _ = self.small.size(weapon_label)
        weapon_pos = (panel.right - 16 - weapon_width, panel.y + 24)
        draw_text_with_shadow(surface, self.small, weapon_label, self.palette.outline, weapon_pos)

        if self._level_up_timer > 0.0:
            width, _ = self.big.size(self._level_up_text)
            pos = (surface.get_width() // 2 - width // 2, panel.y - 40)
            draw_text_with_shadow(
                surface,
                self.big,
                self._level_up_text,
                self.palette.outline,
                pos,
                shadow_offset=(0, 2),
            )

    def _draw_bar(self, surface: pygame.Surface, rect: pygame.Rect, pct: float, color: tuple[int, int, int]) -> None:
        pct = max(0.0, min(1.0, pct))
        pygame.draw.rect(surface, self.palette.bar_bg, rect, border_radius=6)
        fill = rect.copy()
        fill.width = int(rect.width * pct)
        if fill.width > 0:
            pygame.draw.rect(surface, color, fill, border_radius=6)
        pygame.draw.rect(surface, self.palette.outline, rect, 1, border_radius=6)

    def _draw_panel(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        shadow = rect.move(6, 8)
        pygame.draw.rect(surface, self.palette.panel_shadow, shadow, border_radius=14)

        panel_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        panel_surface.fill((*self.palette.panel_bg, 235))
        if self._panel_texture:
            tex = self._panel_texture.copy()
            tex.set_alpha(70)
            for x in range(0, rect.width, tex.get_width()):
                for y in range(0, rect.height, tex.get_height()):
                    panel_surface.blit(tex, (x, y))
        glow = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(glow, (*self.palette.panel_highlight, 48), glow.get_rect(), border_radius=12)
        panel_surface.blit(glow, (0, 0))
        surface.blit(panel_surface, rect)
        pygame.draw.rect(surface, self.palette.outline, rect, 2, border_radius=12)

    def _draw_facing(self, surface: pygame.Surface, panel: pygame.Rect, player) -> None:
        area = pygame.Rect(panel.x + panel.width - (260), panel.y + (-80), 48, 48)
        pygame.draw.rect(surface, self.palette.bar_bg, area, border_radius=8)
        pygame.draw.rect(surface, self.palette.outline, area, 1, border_radius=8)
        arrow_center = area.center
        size = 18
        orientation = getattr(player, "orientation", "right" if player.facing == "right" else "left")
        if orientation == "right":
            points = [
                (arrow_center[0] + size // 2, arrow_center[1]),
                (arrow_center[0] - size // 2, arrow_center[1] - size // 2),
                (arrow_center[0] - size // 2, arrow_center[1] + size // 2),
            ]
        elif orientation == "left":
            points = [
                (arrow_center[0] - size // 2, arrow_center[1]),
                (arrow_center[0] + size // 2, arrow_center[1] - size // 2),
                (arrow_center[0] + size // 2, arrow_center[1] + size // 2),
            ]
        elif orientation == "up":
            points = [
                (arrow_center[0], arrow_center[1] - size // 2),
                (arrow_center[0] - size // 2, arrow_center[1] + size // 2),
                (arrow_center[0] + size // 2, arrow_center[1] + size // 2),
            ]
        else:  # down
            points = [
                (arrow_center[0], arrow_center[1] + size // 2),
                (arrow_center[0] - size // 2, arrow_center[1] - size // 2),
                (arrow_center[0] + size // 2, arrow_center[1] - size // 2),
            ]
        pygame.draw.polygon(surface, self.palette.outline, points)
        draw_text_with_shadow(surface, self.small, "Direction", self.palette.outline, (area.x, area.bottom + 4))

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


class InventoryOverlay:
    """Simple overlay for purchasing and equipping inventory items."""

    KEY_ORDER: tuple[int, ...] = (
        pygame.K_1,
        pygame.K_2,
        pygame.K_3,
        pygame.K_4,
        pygame.K_5,
        pygame.K_6,
        pygame.K_7,
        pygame.K_8,
        pygame.K_9,
        pygame.K_0,
    )

    def __init__(self) -> None:
        self.font = load_pixel_font(18)
        self.small = load_pixel_font(14)
        self.header = load_pixel_font(24)
        self._message = ""
        self._message_timer = 0.0
        self._panel_texture = self._load_panel_texture()

    def update(self, dt: float) -> None:
        if self._message_timer > 0.0:
            self._message_timer = max(0.0, self._message_timer - dt)
            if self._message_timer == 0.0:
                self._message = ""

    def show_message(self, text: str) -> None:
        self._message = text
        self._message_timer = 2.0

    @classmethod
    def key_to_index(cls, key: int) -> Optional[int]:
        try:
            return cls.KEY_ORDER.index(key)
        except ValueError:
            return None

    def draw(self, surface: pygame.Surface, inventory: Inventory, gold: int) -> None:
        width = 440
        height = 420
        panel = pygame.Rect(36, surface.get_height() - height - 36, width, height)
        self._draw_panel(surface, panel)

        draw_text_with_shadow(surface, self.header, "Inventory", (238, 230, 255), (panel.x + 16, panel.y + 16))
        gold_label = f"Gold {gold}"
        gold_size = self.font.size(gold_label)
        draw_text_with_shadow(
            surface,
            self.font,
            gold_label,
            (236, 224, 250),
            (panel.x + panel.width - gold_size[0] - 20, panel.y + 20),
        )

        owned_ids = {item.id for item in inventory.owned()}
        equipped = inventory.equipped()
        items = inventory.catalogue()
        line_y = panel.y + 64
        line_height = 20

        for index, item in enumerate(items):
            number_label = "0" if index == 9 else str(index + 1)
            label = f"[{number_label}] {item.name}"
            draw_text_with_shadow(surface, self.font, label, (242, 240, 252), (panel.x + 18, line_y))

            status_parts: list[str] = []
            if item.id in owned_ids:
                status_parts.append("Owned")
            if equipped.get(item.slot) and equipped[item.slot].id == item.id:
                status_parts.append("Equipped")
            if not status_parts:
                status_parts.append(f"{item.price}G")
            status = " / ".join(status_parts)
            status_surface = self.small.render(status, True, (198, 198, 230))
            surface.blit(status_surface, (panel.x + width - status_surface.get_width() - 20, line_y + 4))

            info = f"+{item.attack_bonus} ATK" if item.attack_bonus else ""
            if item.hp_bonus:
                info += (", " if info else "") + f"+{int(item.hp_bonus)} HP"
            if item.stamina_bonus:
                info += (", " if info else "") + f"{item.stamina_bonus:+.0f} STM"
            if not info:
                info = item.description
            info_surface = self.small.render(info, True, (170, 170, 210))
            surface.blit(info_surface, (panel.x + 28, line_y + 18))

            line_y += line_height + 12
            if line_y > panel.bottom - 72:
                break

        draw_text_with_shadow(
            surface,
            self.small,
            "Press number to buy/equip, I to close",
            (216, 216, 236),
            (panel.x + 18, panel.bottom - 48),
        )
        if self._message:
            draw_text_with_shadow(surface, self.small, self._message, (255, 226, 176), (panel.x + 18, panel.bottom - 28))

    def _load_panel_texture(self) -> Optional[pygame.Surface]:
        try:
            return load_desert_tile("Interface", 0, scale=2.0)
        except FileNotFoundError:
            return None

    def _draw_panel(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        shadow = rect.move(8, 10)
        pygame.draw.rect(surface, (8, 6, 4), shadow, border_radius=16)

        panel_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        panel_surface.fill((26, 20, 16, 235))
        if self._panel_texture:
            tex = self._panel_texture.copy()
            tex.set_alpha(60)
            for x in range(0, rect.width, tex.get_width()):
                for y in range(0, rect.height, tex.get_height()):
                    panel_surface.blit(tex, (x, y))
        vignette = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(vignette, (120, 96, 72, 55), vignette.get_rect(), border_radius=14)
        panel_surface.blit(vignette, (0, 0))
        surface.blit(panel_surface, rect)
        pygame.draw.rect(surface, (246, 230, 206), rect, 2, border_radius=14)
