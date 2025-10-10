from __future__ import annotations

from types import SimpleNamespace
from typing import List, Optional

import pygame

from .base import SceneBase
from ..constants import COL_BG, Keys, WIDTH, HEIGHT
from ..enemy import Enemy
from ..gate import Gate
from ..player import Player
from ..ui import HudRenderer
from ..utils import clamp, load_pixel_font


class SceneOverworld(SceneBase):
    """Exploration scene with roaming enemies and dungeon gates."""

    WORLD_SIZE = pygame.Vector2(2400, 1600)

    def __init__(self, game):
        super().__init__(game)
        if not self.game.state.player:
            self.game.state.player = Player((WIDTH // 2, HEIGHT // 2))
        self.player = self.game.state.player
        self.player.state = "idle"

        self.collision_sprites = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self._build_bounds()
        self._spawn_enemies()

        world_rect = pygame.Rect(0, 0, int(self.WORLD_SIZE.x), int(self.WORLD_SIZE.y))
        self.world = SimpleNamespace(
            collision_sprites=self.collision_sprites,
            enemies=self.enemies,
            bounds=world_rect,
        )

        self.gates: List[Gate] = []
        self._build_gates()

        self.camera = pygame.Vector2(0, 0)
        self.hud = HudRenderer()
        self._ui_font = load_pixel_font(16)
        self._frame_events: list[pygame.event.Event] = []

    # ------------------------------------------------------------------
    def _build_bounds(self) -> None:
        margin = 32
        world_w, world_h = int(self.WORLD_SIZE.x), int(self.WORLD_SIZE.y)
        rects = [
            pygame.Rect(0, 0, world_w, margin),
            pygame.Rect(0, world_h - margin, world_w, margin),
            pygame.Rect(0, 0, margin, world_h),
            pygame.Rect(world_w - margin, 0, margin, world_h),
        ]
        for rect in rects:
            sprite = pygame.sprite.Sprite()
            sprite.rect = rect
            self.collision_sprites.add(sprite)

    def _spawn_enemies(self) -> None:
        positions = [
            (self.WORLD_SIZE.x * 0.35, self.WORLD_SIZE.y * 0.4),
            (self.WORLD_SIZE.x * 0.6, self.WORLD_SIZE.y * 0.55),
            (self.WORLD_SIZE.x * 0.75, self.WORLD_SIZE.y * 0.3),
        ]
        for pos in positions:
            enemy = Enemy(pos, hp=80, speed=95.0, detection_radius=320.0, xp_reward=35)
            self.enemies.add(enemy)

    def _build_gates(self) -> None:
        gate_rect = pygame.Rect(self.WORLD_SIZE.x * 0.8, self.WORLD_SIZE.y * 0.6, 120, 140)
        self.gates.append(Gate(gate_rect, req_level=1, allow_under=True, label="Dungeon Gate"))

    # ------------------------------------------------------------------
    def handle(self, event: pygame.event.Event) -> None:
        self._frame_events.append(event)
        if event.type == pygame.KEYDOWN:
            if event.key == Keys.PAUSE:
                from .menu import SceneMenu

                self.game.change(SceneMenu(self.game), name="menu")
            elif event.key == Keys.INTERACT:
                gate = self._current_gate()
                if gate:
                    self._enter_gate(gate)

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        self.player.handle_input(keys, self._frame_events)
        self.player.update(dt, self.world)
        self._frame_events.clear()

        for enemy in list(self.enemies):
            enemy.update(dt, self.player, self.collision_sprites, self.world.bounds)
            if not enemy.alive:
                self.enemies.remove(enemy)
                leveled = self.player.leveling.gain_xp(enemy.xp_reward)
                if leveled:
                    self.player.on_level_up()
                    self.hud.notify_level_up(self.player.leveling.level)

        self.hud.update(dt)
        self._update_camera()

    def _update_camera(self) -> None:
        view_w, view_h = self.game.screen.get_size()
        target = self.player.rect
        self.camera.x = clamp(target.centerx - view_w / 2, 0, max(0, self.WORLD_SIZE.x - view_w))
        self.camera.y = clamp(target.centery - view_h / 2, 0, max(0, self.WORLD_SIZE.y - view_h))

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(COL_BG)
        offset = self.camera

        grid = 96
        view_w, view_h = surface.get_size()
        for x in range(0, int(self.WORLD_SIZE.x), grid):
            x_screen = int(x - offset.x)
            if -grid <= x_screen <= view_w + grid:
                pygame.draw.line(surface, (40, 44, 52), (x_screen, 0), (x_screen, view_h))
        for y in range(0, int(self.WORLD_SIZE.y), grid):
            y_screen = int(y - offset.y)
            if -grid <= y_screen <= view_h + grid:
                pygame.draw.line(surface, (40, 44, 52), (0, y_screen), (view_w, y_screen))

        for gate in self.gates:
            gate.draw(surface, offset)

        for enemy in self.enemies:
            enemy.draw(surface, offset)

        self.player.draw(surface, offset)

        self.hud.draw(surface, self.player, self.player.dash_cooldown)
        gate = self._current_gate()
        if gate:
            prompt = self._ui_font.render("[E] Enter Gate", True, (235, 235, 245))
            surface.blit(prompt, (surface.get_width() // 2 - prompt.get_width() // 2, surface.get_height() - 72))

    # ------------------------------------------------------------------
    def _current_gate(self) -> Optional[Gate]:
        for gate in self.gates:
            if gate.contains(self.player.rect):
                return gate
        return None

    def _enter_gate(self, gate: Gate) -> None:
        from .dungeon import SceneDungeon

        self.player.pos = pygame.Vector2(gate.rect.centerx, gate.rect.centery + self.player.size.y)
        dungeon = SceneDungeon(self.game, self.player, gate)
        self.game.change(dungeon, name="dungeon")
