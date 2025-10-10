from __future__ import annotations

from types import SimpleNamespace
from typing import Optional

import pygame

from .base import SceneBase
from ..constants import COL_BG, Keys
from ..enemy import Enemy
from ..gate import Gate
from ..ui import HudRenderer
from ..utils import load_pixel_font


class SceneDungeon(SceneBase):
    def __init__(self, game, player, gate: Gate, label: Optional[str] = None):
        super().__init__(game)
        self.player = player
        self.player.state = "idle"
        self.player.intangible = False
        self._entry_gate = gate
        self._entry_return = pygame.Vector2(gate.rect.centerx, gate.rect.centery + self.player.size.y)
        self._spawn_point = pygame.Vector2(160, game.screen.get_height() // 2 + 80)
        self.player.pos = self._spawn_point.copy()

        self.bounds = pygame.Rect(0, 0, 960, 640)
        self.collision_sprites = pygame.sprite.Group()
        self._build_bounds()

        self.enemies = pygame.sprite.Group()
        self._spawn_enemies()

        self.world = SimpleNamespace(
            collision_sprites=self.collision_sprites,
            enemies=self.enemies,
            bounds=self.bounds,
        )

        exit_rect = pygame.Rect(self.bounds.right - 160, self.bounds.centery - 80, 120, 140)
        exit_label = label or f"{gate.label} Exit"
        self.exit_gate = Gate(exit_rect, label=exit_label, allow_under=True)

        self.hud = HudRenderer()
        self._ui_font = load_pixel_font(16)
        self._frame_events: list[pygame.event.Event] = []
        self._cleared_timer: float = 0.0

    # ------------------------------------------------------------------
    def _build_bounds(self) -> None:
        margin = 24
        rects = [
            pygame.Rect(self.bounds.left, self.bounds.top, self.bounds.width, margin),
            pygame.Rect(self.bounds.left, self.bounds.bottom - margin, self.bounds.width, margin),
            pygame.Rect(self.bounds.left, self.bounds.top, margin, self.bounds.height),
            pygame.Rect(self.bounds.right - margin, self.bounds.top, margin, self.bounds.height),
        ]
        for rect in rects:
            sprite = pygame.sprite.Sprite()
            sprite.rect = rect
            self.collision_sprites.add(sprite)

    def _spawn_enemies(self) -> None:
        positions = [
            (self.bounds.centerx - 180, self.bounds.centery - 120),
            (self.bounds.centerx + 60, self.bounds.centery - 60),
            (self.bounds.centerx, self.bounds.centery + 80),
            (self.bounds.centerx + 180, self.bounds.centery + 40),
        ]
        for idx, pos in enumerate(positions):
            enemy = Enemy(pos, hp=90 + idx * 10, speed=120.0, xp_reward=45)
            enemy.detection_radius = 420.0
            self.enemies.add(enemy)

    # ------------------------------------------------------------------
    def handle(self, event: pygame.event.Event) -> None:
        self._frame_events.append(event)
        if event.type == pygame.KEYDOWN:
            if event.key == Keys.PAUSE:
                from .overworld import SceneOverworld

                self.player.pos = self._entry_return.copy()
                self.game.change(SceneOverworld(self.game), name="overworld")
            elif event.key == Keys.INTERACT and self._at_exit():
                self._leave_to_overworld()

    def _at_exit(self) -> bool:
        return self.exit_gate.contains(self.player.rect)

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        self.player.handle_input(keys, self._frame_events)
        self.player.update(dt, self.world)
        self._frame_events.clear()

        for enemy in list(self.enemies):
            enemy.update(dt, self.player, self.collision_sprites, self.bounds)
            if not enemy.alive:
                self.enemies.remove(enemy)
                leveled = self.player.leveling.gain_xp(enemy.xp_reward)
                if leveled:
                    self.player.on_level_up()
                    self.hud.notify_level_up(self.player.leveling.level)

        if not self.enemies and self._cleared_timer == 0.0:
            self._cleared_timer = 1.0
        if self._cleared_timer > 0.0:
            self._cleared_timer = max(0.0, self._cleared_timer - dt)
            if self._cleared_timer == 0.0:
                self._leave_to_overworld()

        if self.player.hp <= 0:
            self.player.hp = self.player.max_hp
            self.player.stamina = self.player.max_stamina
            self._leave_to_overworld()

        self.hud.update(dt)

    # ------------------------------------------------------------------
    def draw(self, surf: pygame.Surface) -> None:
        surf.fill(COL_BG)
        offset = pygame.Vector2(0, 0)
        pygame.draw.rect(surf, (50, 45, 60), self.bounds.inflate(-32, -32), 2)

        for enemy in self.enemies:
            enemy.draw(surf, offset)
        self.player.draw(surf, offset)

        self.exit_gate.draw(surf, offset)
        if self._at_exit():
            prompt = self._ui_font.render("[E] Leave Gate", True, (235, 235, 245))
            surf.blit(prompt, (surf.get_width() // 2 - prompt.get_width() // 2, surf.get_height() - 72))

        self.hud.draw(surf, self.player, self.player.dash_cooldown)

    # ------------------------------------------------------------------
    def _leave_to_overworld(self) -> None:
        from .overworld import SceneOverworld

        self.player.pos = self._entry_return.copy()
        self.game.change(SceneOverworld(self.game), name="overworld")
