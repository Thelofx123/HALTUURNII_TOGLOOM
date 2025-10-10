from __future__ import annotations

import random
from types import SimpleNamespace
from typing import List, Optional

import pygame

from .base import SceneBase
from ..constants import COL_BG, Keys, WIDTH, HEIGHT
from ..enemy import Enemy
from ..gate import Gate
from ..player import Player
from ..ui import HudRenderer, InventoryOverlay
from ..utils import clamp, load_pixel_font


class SceneOverworld(SceneBase):
    """Exploration scene with roaming enemies and dungeon gates."""

    WORLD_SIZE = pygame.Vector2(3200, 2200)

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
        self.inventory_overlay = InventoryOverlay()
        self._ui_font = load_pixel_font(16)
        self._frame_events: list[pygame.event.Event] = []
        self.inventory_open = False
        self.spawn_point = pygame.Vector2(self.WORLD_SIZE.x * 0.2, self.WORLD_SIZE.y * 0.7)
        if not self.player.alive:
            self.player.revive(self.spawn_point, full_heal=True)
        self.player.pos = pygame.Vector2(
            clamp(self.player.pos.x, self.world.bounds.left + self.player.size.x, self.world.bounds.right - self.player.size.x),
            clamp(self.player.pos.y, self.world.bounds.top + self.player.size.y, self.world.bounds.bottom - self.player.size.y),
        )
        self._status_message = ""
        self._status_timer = 0.0
        pending = getattr(self.game.state, "pending_status", "")
        if pending:
            self._set_status(pending)
            self.game.state.pending_status = ""

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
        rng = random.Random(42)
        for _ in range(12):
            pos = (
                rng.uniform(self.WORLD_SIZE.x * 0.15, self.WORLD_SIZE.x * 0.85),
                rng.uniform(self.WORLD_SIZE.y * 0.15, self.WORLD_SIZE.y * 0.85),
            )
            hp = rng.randint(60, 110)
            speed = rng.uniform(85.0, 120.0)
            xp_reward = rng.randint(20, 55)
            enemy = Enemy(pos, hp=hp, speed=speed, detection_radius=360.0, xp_reward=xp_reward)
            self.enemies.add(enemy)

    def _build_gates(self) -> None:
        rng = random.Random()
        player_level = self.player.leveling.level
        min_gates = 2
        max_gates = 5 + max(0, player_level // 3)
        gate_count = rng.randint(min_gates, max_gates)
        for _ in range(gate_count):
            gate_level = max(1, player_level + rng.randint(-1, 3))
            width, height = 140, 160
            x = rng.uniform(self.WORLD_SIZE.x * 0.2, self.WORLD_SIZE.x * 0.9 - width)
            y = rng.uniform(self.WORLD_SIZE.y * 0.2, self.WORLD_SIZE.y * 0.9 - height)
            rect = pygame.Rect(int(x), int(y), width, height)
            label = f"Dungeon Gate (Lv{gate_level})"
            gate = Gate(rect, req_level=gate_level, allow_under=True, label=label)
            self.gates.append(gate)

    # ------------------------------------------------------------------
    def handle(self, event: pygame.event.Event) -> None:
        self._frame_events.append(event)
        if event.type == pygame.KEYDOWN:
            if event.key == Keys.INVENTORY:
                self.inventory_open = not self.inventory_open
                if not self.inventory_open:
                    self.inventory_overlay.show_message("Closed inventory")
                return
            if self.inventory_open:
                index = InventoryOverlay.key_to_index(event.key)
                if index is not None:
                    items = self.player.inventory.catalogue()
                    if index < len(items):
                        item = items[index]
                        if self.player.inventory.is_owned(item.id):
                            equipped = self.player.equip_item(item.id)
                            if equipped:
                                self.inventory_overlay.show_message(f"Equipped {item.name}")
                        elif self.player.try_purchase(item.id):
                            self.inventory_overlay.show_message(f"Purchased {item.name}")
                        else:
                            self.inventory_overlay.show_message("Not enough gold")
                return
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
        if not self.inventory_open:
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

        if not self.player.alive:
            self._handle_player_death()

        self.hud.update(dt)
        self.inventory_overlay.update(dt)
        self._update_camera()
        self._tick_status(dt)

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

        self._draw_minimap(surface)
        if self.inventory_open:
            self.inventory_overlay.draw(surface, self.player.inventory, self.player.gold)
        if self._status_message:
            msg = self._ui_font.render(self._status_message, True, (255, 210, 110))
            surface.blit(msg, (surface.get_width() // 2 - msg.get_width() // 2, 32))

    # ------------------------------------------------------------------
    def _current_gate(self) -> Optional[Gate]:
        for gate in self.gates:
            if not getattr(gate, "cleared", False) and gate.contains(self.player.rect):
                return gate
        return None

    def _enter_gate(self, gate: Gate) -> None:
        from .dungeon import SceneDungeon

        self.player.pos = pygame.Vector2(gate.rect.centerx, gate.rect.centery + self.player.size.y)
        dungeon = SceneDungeon(self.game, self.player, gate)
        self.game.change(dungeon, name="dungeon")

    def _handle_player_death(self) -> None:
        penalty = int(self.player.gold * 0.15)
        if penalty:
            self.player.gold = max(0, self.player.gold - penalty)
        self.player.revive(self.spawn_point, full_heal=True)
        self._set_status("Defeated... Returned to camp" + (f" (-{penalty}G)" if penalty else ""))

    def _set_status(self, text: str, duration: float = 3.0) -> None:
        self._status_message = text
        self._status_timer = duration

    def _tick_status(self, dt: float) -> None:
        if self._status_timer > 0.0:
            self._status_timer = max(0.0, self._status_timer - dt)
            if self._status_timer == 0.0:
                self._status_message = ""

    def _draw_minimap(self, surface: pygame.Surface) -> None:
        width, height = 220, 220
        margin = 24
        rect = pygame.Rect(surface.get_width() - width - margin, margin, width, height)
        pygame.draw.rect(surface, (20, 24, 32), rect, border_radius=10)
        pygame.draw.rect(surface, (235, 235, 245), rect, 2, border_radius=10)

        scale_x = rect.width / self.WORLD_SIZE.x
        scale_y = rect.height / self.WORLD_SIZE.y

        def world_to_map(pos: pygame.Vector2) -> tuple[int, int]:
            x = rect.x + int(pos.x * scale_x)
            y = rect.y + int(pos.y * scale_y)
            return x, y

        for gate in self.gates:
            color = (150, 110, 220) if not getattr(gate, "cleared", False) else (80, 80, 120)
            gx, gy = world_to_map(pygame.Vector2(gate.rect.center))
            pygame.draw.circle(surface, color, (gx, gy), 6)

        for enemy in self.enemies:
            ex, ey = world_to_map(enemy.pos)
            pygame.draw.circle(surface, (200, 90, 90), (ex, ey), 3)

        px, py = world_to_map(self.player.pos)
        pygame.draw.circle(surface, (120, 220, 220), (px, py), 5)
