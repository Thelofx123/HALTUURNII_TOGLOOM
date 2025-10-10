import random

import pygame


class Gate:
    def __init__(self, rect, req_level=1, allow_under=False, label="Gate"):
        self.rect = pygame.Rect(rect)
        self.req_level = req_level
        self.allow_under = allow_under
        self.label = label
        self.cleared = False
        base = 60 + req_level * 25
        spread = int(base * 0.3)
        low = max(25, base - spread)
        high = base + spread
        self._reward_range = (low, high)
        self._cached_reward: int | None = None

    def draw(self, surf, offset: pygame.Vector2 | None = None) -> None:
        offset = offset or pygame.Vector2(0, 0)
        rect = self.rect.move(-offset.x, -offset.y)
        color = (100, 70, 160) if not self.cleared else (70, 70, 90)
        pygame.draw.rect(surf, color, rect, 3)
        f = pygame.font.SysFont(None, 22)
        tag = "*" if self.allow_under else "+"
        label = f"{self.label} (Lv.{self.req_level}{tag})"
        if self.cleared:
            label += " [Cleared]"
        t = f.render(label, True, (210, 200, 230))
        surf.blit(t, (rect.x, rect.y - 20))

    def contains(self, rect: pygame.Rect) -> bool:
        return self.rect.colliderect(rect)

    def reward_gold(self) -> int:
        if self._cached_reward is None:
            self._cached_reward = random.randint(*self._reward_range)
        return self._cached_reward

    def mark_cleared(self) -> None:
        self.cleared = True
