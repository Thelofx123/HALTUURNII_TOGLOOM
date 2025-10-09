import pygame

class Gate:
    def __init__(self, rect, req_level=1, allow_under=False, label="Gate"):
        self.rect = pygame.Rect(rect)
        self.req_level = req_level
        self.allow_under = allow_under
        self.label = label

    def draw(self, surf):
        pygame.draw.rect(surf, (120, 80, 160), self.rect, 3)
        f = pygame.font.SysFont(None, 22)
        tag = "*" if self.allow_under else "+"
        t = f.render(f"{self.label} (Lv.{self.req_level}{tag})", True, (210,200,230))
        surf.blit(t, (self.rect.x, self.rect.y-20))
