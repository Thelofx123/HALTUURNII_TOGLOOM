import pygame


class Gate:
    def __init__(self, rect, req_level=1, allow_under=False, label="Gate"):
        self.rect = pygame.Rect(rect)
        self.req_level = req_level
        self.allow_under = allow_under
        self.label = label

    def draw(self, surf, offset: pygame.Vector2 | None = None) -> None:
        offset = offset or pygame.Vector2(0, 0)
        rect = self.rect.move(-offset.x, -offset.y)
        pygame.draw.rect(surf, (120, 80, 160), rect, 3)
        f = pygame.font.SysFont(None, 22)
        tag = "*" if self.allow_under else "+"
        t = f.render(f"{self.label} (Lv.{self.req_level}{tag})", True, (210, 200, 230))
        surf.blit(t, (rect.x, rect.y - 20))

    def contains(self, rect: pygame.Rect) -> bool:
        return self.rect.colliderect(rect)
