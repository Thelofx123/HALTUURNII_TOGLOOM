import pygame
from .utils import vnorm
from .items import GroundItem
from .constants import DAMAGE_DAGGER

class DaggerProjectile:
    SPEED = 520
    MAX_DIST = 420

    def __init__(self, pos, direction):
        self.start = pygame.Vector2(pos)
        self.pos = pygame.Vector2(pos)
        self.dir = vnorm(direction) if direction.length_squared() else pygame.Vector2(1,0)
        self.radius = 6
        self.alive = True
        self.drop_spawned = False

    def update(self, dt, walls, items, enemies):
        if not self.alive:
            return
        step = self.dir * self.SPEED * dt
        next_pos = self.pos + step

        # enemy hit
        for en in enemies:
            if en.alive and (next_pos - en.pos).length() <= (self.radius + en.radius):
                en.take_damage(DAMAGE_DAGGER)
                self._drop(items, next_pos)
                return

        hit_wall = any(rect.collidepoint(next_pos.x, next_pos.y) for rect in walls)
        maxed = (next_pos - self.start).length() >= self.MAX_DIST
        if hit_wall or maxed:
            self._drop(items, next_pos)
            return

        self.pos = next_pos

    def _drop(self, items, where):
        self.alive = False
        if not self.drop_spawned:
            items.append(GroundItem(where, "dagger"))
            self.drop_spawned = True

    def draw(self, surf):
        pygame.draw.circle(surf, (255, 230, 90), self.pos, self.radius)
        tail = self.pos - self.dir * 14
        pygame.draw.line(surf, (200, 180, 70), self.pos, tail, 3)
