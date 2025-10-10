from __future__ import annotations

from types import SimpleNamespace
from typing import Optional

import pygame

from .base import SceneBase
from ..constants import COL_BG, Keys
from ..enemy import Enemy
from ..gate import Gate
from ..ui import HudRenderer, InventoryOverlay
from ..utils import load_pixel_font


class SceneDungeon(SceneBase):
    def __init__(self, game, player, gate: Gate, label: Optional[str] = None):
        super().__init__(game)
        self.player = player
        self.player.state = "idle"
        self.player.intangible = False
        if not self.player.alive:
            self.player.revive(full_heal=True)
        self._entry_gate = gate
        self._entry_return = pygame.Vector2(gate.rect.centerx, gate.rect.centery + self.player.size.y)
        self._spawn_point = pygame.Vector2(160, game.screen.get_height() // 2 + 80)
        self.player.pos = self._spawn_point.copy()
        self.gate = gate

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
        self.inventory_overlay = InventoryOverlay()
        self._ui_font = load_pixel_font(16)
        self._frame_events: list[pygame.event.Event] = []
        self._cleared_timer: float = 0.0
        self.inventory_open = False
        self._status_message = ""
        self._status_timer = 0.0
        self._reward_granted = False

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
                            if self.player.equip_item(item.id):
                                self.inventory_overlay.show_message(f"Equipped {item.name}")
                        elif self.player.try_purchase(item.id):
                            self.inventory_overlay.show_message(f"Purchased {item.name}")
                        else:
                            self.inventory_overlay.show_message("Not enough gold")
                return
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
        if not self.inventory_open:
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
                self._complete_gate()
                self._leave_to_overworld()

        if not self.player.alive:
            self._fail_gate()

        self.hud.update(dt)
        self.inventory_overlay.update(dt)
        self._tick_status(dt)

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
        if self.inventory_open:
            self.inventory_overlay.draw(surf, self.player.inventory, self.player.gold)
        if self._status_message:
            msg = self._ui_font.render(self._status_message, True, (255, 210, 140))
            surf.blit(msg, (surf.get_width() // 2 - msg.get_width() // 2, 40))

    # ------------------------------------------------------------------
    def _leave_to_overworld(self) -> None:
        from .overworld import SceneOverworld

        self.player.pos = self._entry_return.copy()
        self.game.change(SceneOverworld(self.game), name="overworld")

    def _complete_gate(self) -> None:
        if self._reward_granted:
            return
        reward = self._entry_gate.reward_gold()
        self.player.earn_gold(reward)
        self._entry_gate.mark_cleared()
        self._reward_granted = True
        self._set_status(f"Gate cleared! +{reward}G")
        if hasattr(self.game.state, "pending_status"):
            self.game.state.pending_status = f"Gate cleared! +{reward}G"

    def _fail_gate(self) -> None:
        penalty = int(self.player.gold * 0.2)
        if penalty:
            self.player.gold = max(0, self.player.gold - penalty)
        self.player.revive(self._entry_return, full_heal=True)
        self._set_status("Defeated in gate" + (f" (-{penalty}G)" if penalty else ""))
        if hasattr(self.game.state, "pending_status"):
            self.game.state.pending_status = "Defeated in gate" + (f" (-{penalty}G)" if penalty else "")
        self._leave_to_overworld()

    def _set_status(self, text: str, duration: float = 2.5) -> None:
        self._status_message = text
        self._status_timer = duration

    def _tick_status(self, dt: float) -> None:
        if self._status_timer > 0.0:
            self._status_timer = max(0.0, self._status_timer - dt)
            if self._status_timer == 0.0:
                self._status_message = ""
