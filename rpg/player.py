"""Player implementation with movement, animation, attacks, and dash."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Literal, Optional

import os
import pygame

from .constants import (
    ATTACK_HITBOX_MS,
    ATTACK_LOCK_MS,
    DASH_COOLDOWN_MS,
    DASH_DISTANCE,
    DASH_TIME_MS,
    PLAYER_SPEED,
    Keys,
)
from .leveling import Leveling
from .stats import Stats
from .utils import clamp, load_anim_folder, vnorm

Facing = Literal["left", "right"]
PlayerState = Literal["idle", "walk", "attack", "dash"]


@dataclass
class Hitbox:
    rect: pygame.Rect
    ttl_ms: float
    damage: int
    knockback: float
    size: pygame.Vector2
    follow_player: bool = True
    hits: set[int] = field(default_factory=set)


def _dash_speed() -> float:
    return DASH_DISTANCE / max(0.001, (DASH_TIME_MS / 1000.0))


class Player(pygame.sprite.Sprite):
    """Main controllable hero character."""

    size = pygame.Vector2(20, 28)

    def __init__(self, pos: Iterable[float], who: str = "JINWOO") -> None:
        super().__init__()
        self.who = who
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2()
        self.move_intent = pygame.Vector2()
        self.facing: Facing = "left"
        self.state: PlayerState = "idle"

        # Core stats
        self.stats = Stats()
        self.leveling = Leveling()
        self.max_hp: float = 100.0
        self.hp: float = self.max_hp
        self.max_stamina: float = 100.0
        self.stamina: float = self.max_stamina
        self.dash_cost: float = 20.0
        self.gold: int = 0

        # Legacy compat fields (used by other systems)
        self.radius = 16
        self.face = pygame.Vector2(1, 0)
        self.minions: list[object] = []
        self.game_enemies: list[object] = []
        self.has_dagger = False
        self.has_sword = False
        self.equipped = "fists"
        self.hp_pots = 0
        self.mp_pots = 0
        self.mp = 50
        self.max_mp = 50

        # Animation
        base_path = os.path.join("assets", "rpg", "player")
        self.animations = {
            "idle": load_anim_folder(os.path.join(base_path, "idle")),
            "walk": load_anim_folder(os.path.join(base_path, "walk")),
            "attack": load_anim_folder(os.path.join(base_path, "attack")),
        }
        self.anim_timer: float = 0.0
        self.frame_index: float = 0.0
        self.image: Optional[pygame.Surface] = None

        # Action timers (seconds)
        self._attack_timer: float = 0.0
        self._dash_timer: float = 0.0
        self._dash_cooldown: float = 0.0
        self._dash_vector = pygame.Vector2()
        self._attack_requested = False
        self._dash_requested = False

        self._hitboxes: list[Hitbox] = []
        self.intangible: bool = False

        self._external_velocity = pygame.Vector2()
        self._external_timer: float = 0.0
        self._invuln_timer: float = 0.0
        self._hurt_timer: float = 0.0

    # ------------------------------------------------------------------
    # Input
    def handle_input(
        self,
        keys: pygame.key.ScancodeWrapper,
        events: Iterable[pygame.event.Event],
    ) -> None:
        """Collect per-frame intent and queued actions."""

        intent = pygame.Vector2(0, 0)
        if keys[Keys.MOVE_UP]:
            intent.y -= 1
        if keys[Keys.MOVE_DOWN]:
            intent.y += 1
        if keys[Keys.MOVE_LEFT]:
            intent.x -= 1
        if keys[Keys.MOVE_RIGHT]:
            intent.x += 1

        horizontal = intent.x
        self.move_intent = vnorm(intent)
        if horizontal < 0:
            self.facing = "left"
        elif horizontal > 0:
            self.facing = "right"

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == Keys.ATTACK:
                    self._attack_requested = True
                if event.key == Keys.DASH:
                    self._dash_requested = True

        # Maintain legacy face vector for older systems.
        self.face.xy = (1 if self.facing == "right" else -1, 0)

    # ------------------------------------------------------------------
    def update(self, dt: float, world) -> None:
        """Advance simulation."""

        dt = float(dt)
        ms = dt * 1000.0
        prev_state = self.state

        self._invuln_timer = max(0.0, self._invuln_timer - dt)
        self._hurt_timer = max(0.0, self._hurt_timer - dt)

        self._update_dash(dt)
        self._update_attack(dt)
        self._update_movement(dt, world)
        self._update_hitboxes(ms, getattr(world, "enemies", None))
        self._update_state()

        if self.state != prev_state:
            self.anim_timer = 0.0
        self._update_animation(dt)
        self._recover_resources(dt)
        self._update_external_velocity(dt)

    # ------------------------------------------------------------------
    def _update_dash(self, dt: float) -> None:
        self._dash_cooldown = max(0.0, self._dash_cooldown - dt)
        if self._dash_timer > 0.0:
            self._dash_timer = max(0.0, self._dash_timer - dt)
            if self._dash_timer == 0.0:
                self.intangible = False
        elif self._dash_requested:
            self._dash_requested = False
            if self._dash_cooldown == 0.0 and self.stamina >= self.dash_cost and self.state != "attack":
                dash_vec = (
                    self.move_intent
                    if self.move_intent.length_squared()
                    else pygame.Vector2(1 if self.facing == "right" else -1, 0)
                )
                if dash_vec.length_squared() == 0:
                    dash_vec = pygame.Vector2(1 if self.facing == "right" else -1, 0)
                self._dash_vector = dash_vec.normalize()
                self._dash_timer = DASH_TIME_MS / 1000.0
                self._dash_cooldown = DASH_COOLDOWN_MS / 1000.0
                self.intangible = True
                self.state = "dash"
                self.stamina = max(0.0, self.stamina - self.dash_cost)

    def _update_attack(self, dt: float) -> None:
        if self._attack_timer > 0.0:
            self._attack_timer = max(0.0, self._attack_timer - dt)
            if self._attack_timer == 0.0 and self.state == "attack":
                self.state = "idle"
        elif self._attack_requested and self.state != "dash":
            self._attack_requested = False
            self.state = "attack"
            self._attack_timer = ATTACK_LOCK_MS / 1000.0
            self._spawn_attack_hitbox()

    def _update_movement(self, dt: float, world) -> None:
        if self.state == "dash" and self._dash_timer > 0.0:
            displacement = self._dash_vector * _dash_speed() * dt
            self.pos += displacement
            self._clamp_to_bounds(world)
            return

        if self.state == "attack" and self._attack_timer > 0.0:
            self.vel.update(0, 0)
        else:
            self.vel = self.move_intent * PLAYER_SPEED

        collision_group = getattr(world, "collision_sprites", None)
        if self.intangible or collision_group is None:
            total_velocity = self.vel + self._external_velocity
            self.pos += total_velocity * dt
            self._clamp_to_bounds(world)
            return

        self._move_axis(dt, collision_group, axis="x")
        self._move_axis(dt, collision_group, axis="y")
        self._clamp_to_bounds(world)

    def _move_axis(self, dt: float, collision_group, axis: Literal["x", "y"]) -> None:
        total_velocity = self.vel + self._external_velocity
        offset = total_velocity.x * dt if axis == "x" else total_velocity.y * dt
        if not offset:
            return

        if axis == "x":
            self.pos.x += offset
        else:
            self.pos.y += offset

        rect = self.rect
        for sprite in collision_group:
            target = getattr(sprite, "rect", None)
            if target and rect.colliderect(target):
                if axis == "x":
                    if offset > 0:
                        self.pos.x = target.left - self.size.x / 2
                    else:
                        self.pos.x = target.right + self.size.x / 2
                else:
                    if offset > 0:
                        self.pos.y = target.top + self.size.y
                    else:
                        self.pos.y = target.bottom
                rect = self.rect

    def _spawn_attack_hitbox(self) -> None:
        size = pygame.Vector2(28, 20)
        rect = self._attack_rect_from_size(size)
        damage = 14 + int(self.stats.strength * 0.5)
        knockback = 180.0
        self._hitboxes.append(
            Hitbox(rect=rect, ttl_ms=ATTACK_HITBOX_MS, damage=damage, knockback=knockback, size=size)
        )

    def _attack_rect_from_size(self, size: pygame.Vector2) -> pygame.Rect:
        base_rect = self.rect
        width, height = int(size.x), int(size.y)
        rect = pygame.Rect(0, 0, width, height)
        if self.facing == "right":
            centerx = base_rect.centerx + base_rect.width // 2 + width // 2
        else:
            centerx = base_rect.centerx - base_rect.width // 2 - width // 2
        rect.center = (centerx, base_rect.centery)
        return rect

    def _update_hitboxes(self, ms: float, enemies) -> None:
        for hb in list(self._hitboxes):
            if hb.follow_player:
                hb.rect = self._attack_rect_from_size(hb.size)
            hb.ttl_ms -= ms
            if hb.ttl_ms <= 0:
                self._hitboxes.remove(hb)
                continue
            if enemies:
                for enemy in list(enemies):
                    if not getattr(enemy, "alive", True):
                        continue
                    rect = getattr(enemy, "rect", None)
                    if not rect or not hb.rect.colliderect(rect):
                        continue
                    enemy_id = id(enemy)
                    if enemy_id in hb.hits:
                        continue
                    hb.hits.add(enemy_id)
                    direction = pygame.Vector2(1 if self.facing == "right" else -1, 0)
                    if hasattr(enemy, "take_damage"):
                        enemy.take_damage(hb.damage, source=self, knockback=hb.knockback, direction=direction)

    def _update_state(self) -> None:
        if self.state in {"attack", "dash"}:
            return
        self.state = "walk" if self.move_intent.length_squared() else "idle"

    def _update_animation(self, dt: float) -> None:
        frames = self.animations.get(self.state) or self.animations["idle"]
        fps = 8.0 if self.state != "attack" else 12.0
        self.anim_timer += dt * fps
        if frames:
            idx = int(self.anim_timer) % len(frames)
            self.frame_index = idx
            frame = frames[idx]
            frame_to_draw = frame
            if self.facing == "right":
                frame_to_draw = pygame.transform.flip(frame, True, False)
            if self._hurt_timer > 0:
                frame_to_draw = frame_to_draw.copy()
                frame_to_draw.fill((255, 160, 160, 180), special_flags=pygame.BLEND_RGBA_MULT)
            self.image = frame_to_draw
        else:
            self.image = None

    def _recover_resources(self, dt: float) -> None:
        """Passive HP/stamina regeneration."""

        hp_regen = 0.8
        stam_regen = 0.2 if self.state != "dash" else 0.0
        if self.hp < self.max_hp:
            self.hp = clamp(self.hp + hp_regen * dt, 0.0, self.max_hp)
        self.stamina = clamp(self.stamina + stam_regen * dt, 0.0, self.max_stamina)

    def _update_external_velocity(self, dt: float) -> None:
        if self._external_timer > 0.0:
            self._external_timer = max(0.0, self._external_timer - dt)
            decay = 0.85 ** (dt * 60.0)
            self._external_velocity *= decay
            if self._external_timer == 0.0:
                self._external_velocity.xy = (0, 0)
        else:
            self._external_velocity.xy = (0, 0)

    # ------------------------------------------------------------------
    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            int(self.pos.x - self.size.x / 2),
            int(self.pos.y - self.size.y),
            int(self.size.x),
            int(self.size.y),
        )

    @property
    def dash_cooldown(self) -> float:
        return self._dash_cooldown

    def draw(self, surface: pygame.Surface, offset: Optional[pygame.Vector2] = None) -> None:
        offset = offset or pygame.Vector2(0, 0)
        if self.image is None:
            frames = self.animations.get(self.state, [])
            frame = frames[int(self.frame_index) % len(frames)] if frames else pygame.Surface((32, 32))
            img = pygame.transform.flip(frame, True, False) if self.facing == "right" else frame
        else:
            img = self.image
        rect = self.rect.move(-offset.x, -offset.y)
        surface.blit(img, rect)

    def _clamp_to_bounds(self, world) -> None:
        bounds = getattr(world, "bounds", None)
        if not bounds:
            return
        half_w = self.size.x / 2
        self.pos.x = clamp(self.pos.x, bounds.left + half_w, bounds.right - half_w)
        self.pos.y = clamp(self.pos.y, bounds.top + self.size.y, bounds.bottom)

    # ------------------------------------------------------------------
    # Damage & status ---------------------------------------------------
    def take_damage(
        self,
        amount: int,
        source: Optional[pygame.Vector2 | pygame.math.Vector2 | object] = None,
        knockback: float = 0.0,
        direction: Optional[pygame.Vector2] = None,
    ) -> None:
        if self.intangible or self._invuln_timer > 0.0:
            return
        self.hp = max(0, self.hp - int(max(1, amount)))
        self._invuln_timer = 0.35
        self._hurt_timer = 0.2
        if knockback > 0:
            if direction is None and source is not None:
                if isinstance(source, pygame.Vector2):
                    direction = self.pos - source
                elif hasattr(source, "pos"):
                    direction = self.pos - pygame.Vector2(getattr(source, "pos"))
            direction = direction or pygame.Vector2(1 if self.facing == "right" else -1, 0)
            if direction.length_squared():
                self._external_velocity = direction.normalize() * knockback
                self._external_timer = 0.18
        if self.hp <= 0:
            self.state = "idle"

    def on_level_up(self) -> None:
        self.stats.strength += 1
        self.stats.endurance += 1
        self.max_hp += 8
        self.hp = self.max_hp
        self.max_stamina = min(150.0, self.max_stamina + 5.0)
        self.stamina = self.max_stamina

    # Legacy shim helpers -----------------------------------------------
    def update_legacy(self, dt: float, keys, world_rect=None):  # pragma: no cover
        self.handle_input(keys, [])
        dummy_world = type("LegacyWorld", (), {"collision_sprites": [], "enemies": [], "bounds": world_rect})
        self.update(dt, dummy_world)

    def try_skill(self, _enemies):
        self._dash_requested = True

    def play_pickup(self) -> None:
        pass

    def try_melee(self, enemies) -> None:
        self._attack_requested = True

    def use_hp(self) -> None:
        pass

    def use_mp(self) -> None:
        pass


def _assert_facing_priority() -> None:
    """Reproduction: press D, keep W held, ensure facing stays right until A is pressed."""
    player = Player((0, 0))
    events: list[pygame.event.Event] = []
    keys = _FakeKeys({Keys.MOVE_RIGHT})
    player.handle_input(keys, events)
    assert player.facing == "right"
    keys = _FakeKeys({Keys.MOVE_UP})
    player.handle_input(keys, events)
    assert player.facing == "right", "Vertical input should not change facing"
    keys = _FakeKeys({Keys.MOVE_LEFT})
    player.handle_input(keys, events)
    assert player.facing == "left", "Horizontal input should flip facing"


class _FakeKeys:
    def __init__(self, pressed):
        self._pressed = pressed

    def __getitem__(self, key):
        return key in self._pressed


if __name__ == "__main__":  # pragma: no cover
    _assert_facing_priority()
