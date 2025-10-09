import pygame

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def vnorm(v: pygame.Vector2) -> pygame.Vector2:
    if v.length_squared():
        v = v.normalize()
    return v
