import pygame
import pygame, math
from collections import deque
from .base import SceneBase
from ..constants import COL_BG, COL_UI
from ..items import GroundItem
from ..projectiles import DaggerProjectile
from ..gate import Gate
from .dungeon import SceneDungeon

class SceneOverworld(SceneBase):
    def __init__(self, game):
        super().__init__(game)
        self.player = self.game.state.player
        self.player.game_enemies = []
        self.font = pygame.font.SysFont(None, 24)

        # world size (area to roam)
        self.world_rect = pygame.Rect(0, 0, 2400, 1600)
        
        self.player.pos.x = min(max(self.player.pos.x, 60), self.world_rect.width-60)
        self.player.pos.y = min(max(self.player.pos.y, 60), self.world_rect.height-60)

        self.items, self.projectiles, self.enemies = [], [], []
        if self.player.who == "JINWOO" and not self.player.has_sword:
            self.items.append(GroundItem((900, 900), kind="sword"))

        self.shop_rect = pygame.Rect(300, 1480, 140, 110)
        self.gates = [
            Gate((2000, 300, 160, 80), req_level=1, allow_under=True,  label="Gate: Forest"),
            Gate((1800, 1100,160, 80), req_level=4, allow_under=False, label="Gate: Ruins"),
        ]
        self.message = deque(maxlen=3)
        self.show_inventory = False
        self.near_gate = None
        self.near_shop = False

    def push_msg(self, text, color=(240,240,255)):
        self.message.append((text, color, 2.5))

    def handle(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                from .menu import SceneMenu
                self.game.change(SceneMenu(self.game), name="menu")
            if e.key == pygame.K_q:
                self.player.try_skill(self.enemies)
            if e.key == pygame.K_f and self.player.has_dagger:
                self.projectiles.append(DaggerProjectile(self.player.pos, self.player.face))
                self.player.has_dagger = False
            if e.key == pygame.K_e:
                # items
                for it in list(self.items):
                    if it.collides_player(self.player):
                        if it.kind == "dagger":
                            self.player.play_pickup()
                            self.items.remove(it); self.player.has_dagger = True; break
                        if it.kind == "sword":
                            self.player.play_pickup()
                            self.items.remove(it); self.player.has_sword = True; self.player.equipped = "sword"; break
                # gates
                if self.near_gate:
                    g = self.near_gate
                    lvl = self.player.leveling.level
                    if lvl < g.req_level and not g.allow_under:
                        self.push_msg(f"Requires Level {g.req_level}. You are Lv {lvl}.", (255,120,120))
                    else:
                        if lvl < g.req_level and g.allow_under:
                            self.push_msg("Warning: Under-leveled. Enter at your own risk!", (255,200,120))
                        self.game.change(SceneDungeon(self.game, self.player, gate_label=g.label, gate_level=g.req_level), name="dungeon")
                        return
            if e.key == pygame.K_i:
                self.show_inventory = not self.show_inventory
            if self.show_inventory:
                if e.key == pygame.K_1:
                    self.player.equipped = "fists"
                if e.key == pygame.K_2 and self.player.has_sword:
                    self.player.equipped = "sword"
                if e.key == pygame.K_h:
                    self.player.use_hp()
                if e.key == pygame.K_m:
                    self.player.use_mp()
            if e.key == pygame.K_b and self.near_shop:
                self.open_shop()

        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.player.try_melee(self.enemies)

    def open_shop(self):
        running = True
        font = pygame.font.SysFont(None, 28)
        win, clock = self.game.screen, self.game.clock
        while running:
            dt = clock.tick(60)/1000
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT: import sys; pygame.quit(); sys.exit()
                if ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_ESCAPE, pygame.K_b):
                        running = False
                    if ev.key == pygame.K_1 and self.player.gold >= 30:
                        self.player.gold -= 30; self.player.hp_pots += 1
                    if ev.key == pygame.K_2 and self.player.gold >= 25:
                        self.player.gold -= 25; self.player.mp_pots += 1
            overlay = pygame.Surface(win.get_size(), pygame.SRCALPHA); overlay.fill((0,0,0,160))
            win.blit(overlay, (0,0))
            box = pygame.Rect(win.get_width()//2-220, win.get_height()//2-140, 440, 260)
            pygame.draw.rect(win, (45,50,60), box); pygame.draw.rect(win, (200,200,220), box, 2)
            t = font.render("SHOP — [1] HP Potion (30g), [2] MP Potion (25g), [Esc/B] Close", True, (235,235,245))
            win.blit(t, (box.x+16, box.y+16))
            t2 = font.render(f"Gold: {self.player.gold} | HP Pots: {self.player.hp_pots} | MP Pots: {self.player.mp_pots}", True, (230,230,240))
            win.blit(t2, (box.x+16, box.y+60))
            pygame.display.flip()

    def update(self, dt):
        keys = pygame.key.get_pressed()
        self.player.game_enemies = self.enemies
        self.player.update(dt, keys, world_rect=self.world_rect)

        for p in list(self.projectiles):
            p.update(dt, [self.world_rect], self.items, self.enemies)
            if not p.alive and p.drop_spawned:
                self.projectiles.remove(p)

        for it in list(self.items):
            it.update(dt)
            if it.expired(): self.items.remove(it)

        self.near_gate = None
        for g in self.gates:
            if g.rect.collidepoint(self.player.pos.x, self.player.pos.y):
                self.near_gate = g; break
        self.near_shop = self.shop_rect.collidepoint(self.player.pos.x, self.player.pos.y)

        for i in range(len(self.message)):
            txt, col, ttl = self.message[i]
            ttl -= dt
            self.message[i] = (txt, col, ttl)
        while self.message and self.message[0][2] <= 0:
            self.message.popleft()

    def draw(self, surf):
        # camera
        vw, vh = surf.get_size()
        cam_x = int(self.player.pos.x - vw/2)
        cam_y = int(self.player.pos.y - vh/2)
        cam_x = max(0, min(cam_x, self.world_rect.width - vw))
        cam_y = max(0, min(cam_y, self.world_rect.height - vh))
        camera = pygame.Rect(cam_x, cam_y, vw, vh)

        surf.fill(COL_BG)
        grid = 80
        for x in range(self.world_rect.left, self.world_rect.right, grid):
            pygame.draw.line(surf, (40,44,52), (x - cam_x, 0), (x - cam_x, vh))
        for y in range(self.world_rect.top, self.world_rect.bottom, grid):
            pygame.draw.line(surf, (40,44,52), (0, y - cam_y), (vw, y - cam_y))

        # shop
        pygame.draw.rect(surf, (80,90,60), self._world_to_screen(self.shop_rect, camera))
        f = pygame.font.SysFont(None, 22)
        lab_pos = (self.shop_rect.x - cam_x + 6, self.shop_rect.y - cam_y - 20)
        surf.blit(f.render("SHOP (B)", True, (230,230,210)), lab_pos)

        # gates
        for g in self.gates:
            rect = self._world_to_screen(g.rect, camera)
            pygame.draw.rect(surf, (120,80,160), rect, 3)
            t = f.render(f"{g.label} (Lv.{g.req_level}{'*' if g.allow_under else '+'})", True, (210,200,230))
            surf.blit(t, (rect.x, rect.y-20))
            # pointer if offscreen
            self._draw_gate_pointer(surf, camera, g.rect, g.label)

        # items/projectiles
        for it in self.items:
            self._draw_world_circle(surf, it.pos, it, cam_x, cam_y)
        for p in self.projectiles:
            pygame.draw.circle(surf, (255,230,90), (int(p.pos.x - cam_x), int(p.pos.y - cam_y)), p.radius)

        # player
        old = self.player.pos.copy()
        self.player.pos -= pygame.Vector2(cam_x, cam_y)
        for m in self.player.minions:
            m.pos -= pygame.Vector2(cam_x, cam_y)
        self.player.draw(surf)
        # restore
        for m in self.player.minions:
            m.pos += pygame.Vector2(cam_x, cam_y)
        self.player.pos = old

        # HUD
        hud = f"{self.player.who}  Lv {self.player.leveling.level}  XP {self.player.leveling.xp}/{self.player.leveling.xp_to_next}  HP {int(self.player.hp)}/{self.player.max_hp}  MP {int(self.player.mp)}/{self.player.max_mp}  Gold {self.player.gold}  WEAPON:{self.player.equipped.upper()}"
        surf.blit(self.font.render(hud, True, (235,235,245)), (24, 24))
        surf.blit(self.font.render("I: Inventory | E: Gate/Items | B: Shop  (Ctrl+S to Save, L on menu to Load)", True, (190,200,210)), (24, 52))
        # msgs
        y = 90
        for txt, col, ttl in self.message:
            surf.blit(self.font.render(txt, True, col), (24, y)); y += 26

        if self.show_inventory:
            self._draw_inventory_panel(surf)

    def _world_to_screen(self, rect, cam):
        return pygame.Rect(rect.x - cam.x, rect.y - cam.y, rect.w, rect.h)

    def _draw_world_circle(self, surf, pos_obj, it, cam_x, cam_y):
        it.draw = it.draw  

        old = it.pos.copy()
        it.pos -= pygame.Vector2(cam_x, cam_y)
        it.draw(surf)
        it.pos = old

    def _draw_inventory_panel(self, surf):
        panel = pygame.Rect(surf.get_width()-420, 60, 380, 280)
        pygame.draw.rect(surf, (45,50,60), panel); pygame.draw.rect(surf, (200,200,220), panel, 2)
        f = pygame.font.SysFont(None, 26)
        surf.blit(f.render("Inventory & Skills (I to close)", True, (235,235,245)), (panel.x+12, panel.y+10))
        surf.blit(f.render(f"Gold: {self.player.gold}", True, (235,235,245)), (panel.x+12, panel.y+40))
        surf.blit(f.render(f"Potions: HP {self.player.hp_pots} (H), MP {self.player.mp_pots} (M)", True, (220,240,220)), (panel.x+12, panel.y+68))
        surf.blit(f.render(f"Weapons: [1] Fists  [2] Sword {'(owned)' if self.player.has_sword else '(need)'}", True, (230,230,250)), (panel.x+12, panel.y+96))
        y = panel.y+130
        surf.blit(f.render("Skills:", True, (235,235,245)), (panel.x+12, y)); y+=26
        if self.player.who == "JINWOO":
            surf.blit(f.render(f"- Shadow Step (Q)  MP:12", True, (180,220,255)), (panel.x+22, y)); y+=22
            surf.blit(f.render(f"- Shadow Extraction (E on corpse)", True, (180,220,255)), (panel.x+22, y)); y+=22
        else:
            surf.blit(f.render(f"- Sword Dash (Q)  MP:10", True, (255,230,180)), (panel.x+22, y)); y+=22
        surf.blit(f.render("Note: Ctrl+S saves, L loads on menu.", True, (210,210,210)), (panel.x+12, panel.y+panel.height-36))
    def _draw_gate_pointer(self, surf, camera, gate_rect, label, color=(210,200,230)):

        vw, vh = surf.get_size()
        cx, cy = self.player.pos.x, self.player.pos.y
        gx, gy = gate_rect.centerx, gate_rect.centery
        dx, dy = gx - cx, gy - cy
        if camera.collidepoint(gx, gy):
            return
        ang = math.atan2(dy, dx)
        px = cx + math.cos(ang) * 300
        py = cy + math.sin(ang) * 300
        sx = int(px - camera.x); sy = int(py - camera.y)
        sx = max(24, min(vw-24, sx))
        sy = max(24, min(vh-24, sy))
        pygame.draw.circle(surf, (120,80,160), (sx, sy), 10, 2)
        f = pygame.font.SysFont(None, 20)
        surf.blit(f.render(label, True, color), (sx+12, sy-10))

