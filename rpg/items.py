import math, pygame
from .utils import clamp
from .constants import CORPSE_TTL

class GroundItem:
    def __init__(self, pos, kind="dagger", ttl=None):
        self.pos = pygame.Vector2(pos)
        self.kind = kind   # "dagger", "sword", "corpse"
        self.radius = 12 if kind != "corpse" else 18
        self.pulse = 0
        self.ttl = ttl  # seconds for corpse

    def update(self, dt):
        self.pulse += dt * 4
        if self.ttl is not None:
            self.ttl -= dt

    def expired(self):
        return self.ttl is not None and self.ttl <= 0

    def collides_player(self, player) -> bool:
        return (player.pos - self.pos).length() < (player.radius + self.radius)

    def draw(self, surf):
        r = self.radius + 2 * math.sin(self.pulse)
        if self.kind == "dagger":
            pygame.draw.circle(surf, (230, 205, 80), self.pos, max(6, r), 0)
            pygame.draw.rect(surf, (70, 60, 20), pygame.Rect(self.pos.x-2, self.pos.y-12, 4, 8))
        elif self.kind == "sword":
            pygame.draw.circle(surf, (200, 220, 255), self.pos, max(6, r), 0)
            pygame.draw.rect(surf, (80, 80, 105), pygame.Rect(self.pos.x-2, self.pos.y-14, 4, 10))
        elif self.kind == "corpse":
            pygame.draw.circle(surf, (100, 20, 20), self.pos, self.radius)
            pygame.draw.circle(surf, (60, 8, 8), self.pos, self.radius, 2)
