import random, pygame
from .utils import clamp

class Enemy:
    def __init__(self, pos, hp=40, xp_reward=30, boss=False, area_rect=None):
        self.pos = pygame.Vector2(pos)
        self.radius = 16 if not boss else 26
        self.max_hp = hp
        self.hp = hp
        self.color = (200, 60, 70) if not boss else (200, 90, 30)
        self.alive = True
        self.xp_reward = xp_reward
        self.hit_flash = 0
        self.boss = boss
        self.area_rect = area_rect
        self.rewarded = False


        self.base_speed = 110 if not boss else 140
        self.attack_cd = 0.0
        self.touch_range = self.radius + 14
        self.touch_damage = 6 if not boss else 12
        self.knockback = 120 if not boss else 180

    def update(self, dt, player=None):
        if not self.alive: return
        if player:
            dv = player.pos - self.pos
            if dv.length_squared():
                dv = dv.normalize()
            self.pos += dv * self.base_speed * dt
        else:
            self.pos += pygame.Vector2(random.uniform(-1,1), random.uniform(-1,1)) * 30 * dt

        # bounds
        pad = 40
        if self.area_rect:
            left  = self.area_rect.left + pad
            right = self.area_rect.right - pad
            top   = self.area_rect.top + pad
            bot   = self.area_rect.bottom - pad
        else:
            from .constants import WIDTH, HEIGHT
            left, right, top, bot = 40, WIDTH-40, 40, HEIGHT-40
        self.pos.x = clamp(self.pos.x, left, right)
        self.pos.y = clamp(self.pos.y, top, bot)

        # attack
        self.attack_cd = max(0.0, self.attack_cd - dt)
        if player and (player.pos - self.pos).length() <= self.touch_range and self.attack_cd <= 0:
            player.take_damage(self.touch_damage, source=self.pos, knockback=self.knockback)
            self.attack_cd = 0.6 if not self.boss else 0.4

        self.hit_flash = max(0.0, self.hit_flash - dt)

    def take_damage(self, dmg: int):
        if not self.alive: return
        self.hp -= max(1, dmg)
        self.hit_flash = 0.12
        if self.hp <= 0:
            self.alive = False

    def draw(self, surf):
        if not self.alive: return
        col = (255,120,120) if self.hit_flash>0 else self.color
        pygame.draw.circle(surf, col, self.pos, self.radius)
        w = 40 if not self.boss else 80
        pct = max(0.0, min(1.0, self.hp / self.max_hp))
        pygame.draw.rect(surf, (40,40,40), pygame.Rect(self.pos.x-w/2, self.pos.y-28, w, 6))
        pygame.draw.rect(surf, (90,220,90), pygame.Rect(self.pos.x-w/2, self.pos.y-28, w*pct, 6))
