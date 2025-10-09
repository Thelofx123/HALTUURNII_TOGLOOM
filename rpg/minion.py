import pygame
from .constants import MINION_SPEED, MINION_TOUCH_DPS

class Minion:
    def __init__(self, pos):
        self.pos = pygame.Vector2(pos)
        self.radius = 12
        self.alive = True
        self.hp = 40
        self.dps_timer = 0.0
        self.target = None

    def update(self, dt, enemies):
        if not self.alive: return
        if not self.target or not self.target.alive:
            self.target = None
            best = 1e9
            for en in enemies:
                if en.alive:
                    d = (en.pos - self.pos).length()
                    if d < best:
                        best, self.target = d, en
        # move & damage
        if self.target:
            dv = self.target.pos - self.pos
            if dv.length_squared():
                dv = dv.normalize()
            self.pos += dv * MINION_SPEED * dt
            if (self.target.pos - self.pos).length() <= (self.radius + self.target.radius):
                self.dps_timer += dt
                if self.dps_timer >= 0.4:
                    self.target.take_damage(MINION_TOUCH_DPS)
                    self.dps_timer = 0.0

    def draw(self, surf):
        if not self.alive: return
        pygame.draw.circle(surf, (90, 90, 160), self.pos, self.radius)
        pygame.draw.circle(surf, (60, 60, 120), self.pos, self.radius, 2)
