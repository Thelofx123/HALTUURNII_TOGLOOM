"""Enemy behaviours for overworld and dungeon scenes."""
from __future__ import annotations

from typing import Optional

import pygame

from .utils import clamp


class Enemy(pygame.sprite.Sprite):
    size = pygame.Vector2(22, 26)

    def __init__(
        self,
        pos: tuple[float, float],
        hp: int = 60,
        speed: float = 110.0,
        detection_radius: float = 240.0,
        attack_range: float = 36.0,
        attack_damage: int = 8,
        knockback: float = 160.0,
        xp_reward: int = 25,
        color: tuple[int, int, int] = (200, 80, 90),
    ) -> None:
        super().__init__()
        self.pos = pygame.Vector2(pos)
        self.hp = hp
        self.max_hp = hp
        self.speed = speed
        self.detection_radius = detection_radius
        self.attack_range = attack_range
        self.attack_damage = attack_damage
        self.knockback = knockback
        self.xp_reward = xp_reward
        self.state: str = "idle"
        self.alive = True

        self._attack_cooldown = 0.6
        self._cooldown_timer = 0.0
        self._hurt_timer = 0.0
        self._hurt_cooldown = 0.1
        self._hurt_block = 0.0
        self._knockback_velocity = pygame.Vector2()
        self._knockback_timer = 0.0

        self.image = pygame.Surface((int(self.size.x), int(self.size.y)), pygame.SRCALPHA)
        pygame.draw.rect(self.image, color, self.image.get_rect(), border_radius=6)
        self.base_image = self.image.copy()
        self.color = color

    # ------------------------------------------------------------------
    def update(
        self,
        dt: float,
        player,
        collision_sprites: Optional[pygame.sprite.Group] = None,
        bounds: Optional[pygame.Rect] = None,
    ) -> None:
        if not self.alive:
            return

        dt = float(dt)
        self._cooldown_timer = max(0.0, self._cooldown_timer - dt)
        self._hurt_timer = max(0.0, self._hurt_timer - dt)
        self._hurt_block = max(0.0, self._hurt_block - dt)
        self._update_knockback(dt, collision_sprites)

        to_player = player.pos - self.pos
        distance = to_player.length()
        if distance <= self.attack_range:
            self.state = "idle"
            if self._cooldown_timer == 0.0:
                self._swing(player)
        elif distance <= self.detection_radius:
            self.state = "chase"
            if distance:
                direction = to_player / distance
                self._move(direction, dt, collision_sprites)
        else:
            self.state = "idle"

        if bounds:
            half_w = self.size.x / 2
            self.pos.x = clamp(self.pos.x, bounds.left + half_w, bounds.right - half_w)
            self.pos.y = clamp(self.pos.y, bounds.top + self.size.y, bounds.bottom)

    # ------------------------------------------------------------------
    def _update_knockback(self, dt: float, collision_sprites) -> None:
        if self._knockback_timer <= 0.0:
            return
        self._knockback_timer = max(0.0, self._knockback_timer - dt)
        displacement = self._knockback_velocity * dt
        self._move_axis(displacement.x, collision_sprites, axis="x")
        self._move_axis(displacement.y, collision_sprites, axis="y")
        if self._knockback_timer == 0.0:
            self._knockback_velocity.xy = (0, 0)

    def _move(self, direction: pygame.Vector2, dt: float, collision_sprites) -> None:
        velocity = direction * self.speed * dt
        self._move_axis(velocity.x, collision_sprites, axis="x")
        self._move_axis(velocity.y, collision_sprites, axis="y")

    def _move_axis(self, offset: float, collision_sprites, axis: str) -> None:
        if not offset:
            return
        if axis == "x":
            self.pos.x += offset
        else:
            self.pos.y += offset

        if not collision_sprites:
            return

        rect = self.rect
        for sprite in collision_sprites:
            target = getattr(sprite, "rect", None)
            if not target or not rect.colliderect(target):
                continue
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

    def _swing(self, player) -> None:
        player.take_damage(
            self.attack_damage,
            source=self,
            knockback=self.knockback,
            direction=(player.pos - self.pos),
        )
        self._cooldown_timer = self._attack_cooldown

    # ------------------------------------------------------------------
    def take_damage(
        self,
        amount: int,
        source=None,
        knockback: float = 0.0,
        direction: Optional[pygame.Vector2] = None,
    ) -> None:
        if not self.alive or self._hurt_block > 0.0:
            return
        self.hp = max(0, self.hp - int(max(1, amount)))
        self._hurt_timer = 0.18
        self._hurt_block = self._hurt_cooldown
        if self.hp <= 0:
            self.alive = False
            return
        if knockback > 0:
            if direction is None and source is not None:
                if isinstance(source, pygame.Vector2):
                    direction = self.pos - source
                elif hasattr(source, "pos"):
                    direction = self.pos - pygame.Vector2(getattr(source, "pos"))
            direction = direction or pygame.Vector2(0, 0)
            if direction.length_squared():
                self._knockback_velocity = direction.normalize() * knockback
                self._knockback_timer = 0.2

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, offset: Optional[pygame.Vector2] = None) -> None:
        if not self.alive:
            return
        offset = offset or pygame.Vector2(0, 0)
        rect = self.rect.move(-offset.x, -offset.y)
        image = self.base_image.copy()
        if self._hurt_timer > 0:
            image.fill((255, 200, 200, 160), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(image, rect)

        pct = self.hp / self.max_hp if self.max_hp else 0
        bar_rect = pygame.Rect(rect.x, rect.y - 8, rect.width, 4)
        pygame.draw.rect(surface, (30, 30, 40), bar_rect)
        fill = bar_rect.copy()
        fill.width = int(bar_rect.width * pct)
        if fill.width > 0:
            pygame.draw.rect(surface, (120, 220, 120), fill)
        pygame.draw.rect(surface, (235, 235, 245), bar_rect, 1)

    @property
    def center(self) -> pygame.Vector2:
        return pygame.Vector2(self.pos.x, self.pos.y - self.size.y / 2)

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            int(self.pos.x - self.size.x / 2),
            int(self.pos.y - self.size.y),
            int(self.size.x),
            int(self.size.y),
        )
