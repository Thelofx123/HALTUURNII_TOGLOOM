import os, math, pygame
from .stats import Stats
from .leveling import Leveling
from .utils import clamp
from .minion import Minion
from .constants import (
    BASE_HP, HEALTH_PER_END, CHAR_JINWOO, CHAR_CHA,
    DAMAGE_PUNCH, DAMAGE_SWORD, COOLDOWN_PUNCH, COOLDOWN_SWORD,
    PUNCH_RANGE, SWORD_RANGE, Q_BURST_RANGE,
    JIN_Q_COST, CHA_Q_COST, MINION_MAX
)
# sprite helpers
from .sprites import split_8dir, load_gif_frames, build_run4, dir4_from_vec, dir8_index_from_vec, reorder_8

class Player:
    BASE_SPEED = 240

    def __init__(self, pos, who=CHAR_JINWOO):
        self.who = who
        self.pos = pygame.Vector2(pos)
        self.radius = 16
        self.face = pygame.Vector2(1,0)

        # core stats
        self.stats = Stats(
            strength=6 if who==CHAR_CHA else 5,
            agility=6 if who==CHAR_JINWOO else 5,
            endurance=6, defense=3, intelligence=4, precision=2, crit_rate=0.07, crit_damage=1.6
        )
        self.leveling = Leveling()
        self.hp = BASE_HP + self.stats.endurance * HEALTH_PER_END
        self.max_hp = self.hp
        self.mp = 40; self.max_mp = 40
        self.gold = 100

        self.has_dagger = True
        self.has_sword  = (who==CHAR_CHA)
        self.equipped   = "sword" if self.has_sword else "fists"

        self.attack_cd  = 0.0
        self.dash_cd    = 0.0
        self.shadow_cd  = 0.0
        self.last_hit_preview = None

        self.minions = []
        self.hp_pots = 2
        self.mp_pots = 2
        self.game_enemies = []
        
        self.flip_ew = False 

        self.hp_regen_rate = 2.0
        self.mp_regen_rate = 1.0

        assets = "assets/sprites/jinwoo" if self.who==CHAR_JINWOO else "assets/sprites/cha"

        run_paths = {
            "E": os.path.join(assets, "son_ji_woo_running-4-frames_west.gif"),
            "W": os.path.join(assets, "son_ji_woo_running-4-frames_east.gif"),
            "N": os.path.join(assets, "son_ji_woo_running-4-frames_north.gif"),
            "S": os.path.join(assets, "son_ji_woo_running-4-frames_south.gif"),
        }
        self.run4 = build_run4(run_paths, scale=1.0, auto_flip=False)

        idle8_path = os.path.join(assets, "son_ji_woo_rotations_8dir.gif")
        if os.path.isfile(idle8_path):
            _idle_frames = split_8dir(load_gif_frames(idle8_path, 1.0))
            IDLE_GIF_ORDER = ("S","SW","W","NW","N","NE","E","SE")
            self.idle8 = reorder_8(_idle_frames, IDLE_GIF_ORDER)
        else:
            self.idle8 = [[]]*8

        pickup_path = os.path.join(assets, "son_ji_woo_picking-up_south.gif")
        self.pickup8 = split_8dir(load_gif_frames(pickup_path, 1.0)) if os.path.isfile(pickup_path) else [[]]*8

        atk_sword = {
            "E": os.path.join(assets, "son_ji_woo_lead-jab_west.gif"),  
            "W": None, "N": None, "S": None
        }
        atk_fists = {
            "E": os.path.join(assets, "son_ji_woo_lead-jab_east.gif"),
            "W": None, "N": None, "S": None
        }
        self.attack4_sword = build_run4(atk_sword, scale=1.0, auto_flip=True)
        self.attack4_fists = build_run4(atk_fists, scale=1.0, auto_flip=True)

        self.anim_state = "idle"   # idle | run | pickup | attack
        self.anim_time  = 0.0
        self.anim_frame = 0
        self.current_img = None
        self._pickup_once = False
        self._attack_once = False
        self._fps = {"idle": 4.0, "run": 10.0, "pickup": 8.0, "attack": 12.0}

    def update(self, dt, keys, world_rect=None):
        self.attack_cd = max(0.0, self.attack_cd - dt)
        self.dash_cd   = max(0.0, self.dash_cd - dt)
        self.shadow_cd = max(0.0, self.shadow_cd - dt)

        move = pygame.Vector2(0,0)
        if keys[pygame.K_w]: move.y -= 1
        if keys[pygame.K_s]: move.y += 1
        if keys[pygame.K_a]: move.x -= 1
        if keys[pygame.K_d]: move.x += 1
        if move.length_squared():
            move = move.normalize()
            self.face = move

        speed = self.BASE_SPEED + self.stats.agility * 6
        next_pos = self.pos + move * speed * dt

        r = self.radius + 2
        if world_rect is not None:
            left  = world_rect.left  + 20 + r
            right = world_rect.right - 20 - r
            top   = world_rect.top   + 20 + r
            bot   = world_rect.bottom- 20 - r
            next_pos.x = max(left,  min(right, next_pos.x))
            next_pos.y = max(top,   min(bot,   next_pos.y))
        else:
            from .constants import WIDTH, HEIGHT
            next_pos.x = max(20+r, min(WIDTH-20-r, next_pos.x))
            next_pos.y = max(20+r, min(HEIGHT-20-r, next_pos.y))
        self.pos = next_pos

        # decay melee preview ring
        if self.last_hit_preview:
            p, rad, t = self.last_hit_preview
            t -= dt
            self.last_hit_preview = (p, rad, t) if t>0 else None

        # minions
        for m in self.minions:
            m.update(dt, self.game_enemies)

        self.hp = min(self.max_hp, self.hp + self.hp_regen_rate * dt)
        self.mp = min(self.max_mp, self.mp + self.mp_regen_rate * dt)

        moving = (keys[pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d])

        if self.anim_state not in ("pickup", "attack"):
            self.anim_state = "run" if moving else "idle"

        prev_state = self.anim_state
        if self.anim_state not in ("pickup", "attack"):
            self.anim_state = "run" if moving else "idle"
            if self.anim_state != prev_state:
                self.anim_time = 0.0
                self.anim_frame = 0

        if self.anim_state == "run":
            d = dir4_from_vec(self.face)               # E/W/N/S
            frames = self.run4.get(d, [])
        elif self.anim_state == "attack":
            d = dir4_from_vec(self.face)
            setdict = self.attack4_sword if (self.equipped=="sword" and self.has_sword) else self.attack4_fists
            frames = setdict.get(d, [])
        else:
            idx = dir8_index_from_vec(self.face)
            frames = self.pickup8[idx] if self.anim_state=="pickup" else (self.idle8[idx] if idx < len(self.idle8) else [])

        fps = self._fps.get(self.anim_state, 6.0)
        if frames:
            self.anim_time += fps * dt
            if self._pickup_once and self.anim_time >= len(frames):
                self.anim_state = "idle"; self._pickup_once = False; self.anim_time = 0.0
            if self._attack_once and self.anim_time >= len(frames):
                self.anim_state = "idle"; self._attack_once = False; self.anim_time = 0.0
            self.anim_frame = int(self.anim_time) % max(1, len(frames))
            self.current_img = frames[self.anim_frame]
        else:
            self.current_img = None
            
        # run selection
        if self.anim_state == "run":
            d = self._dir4_with_fix()          
            frames = self.run4.get(d, [])

        # attack selection
        elif self.anim_state == "attack":
            d = self._dir4_with_fix()          
            setdict = self.attack4_sword if (self.equipped=="sword" and self.has_sword) else self.attack4_fists
            frames = setdict.get(d, [])


    # skills
    def try_skill(self, enemies):
        if self.who == CHAR_JINWOO:
            if self.shadow_cd <= 0 and self.mp >= JIN_Q_COST:
                self.mp -= JIN_Q_COST
                self.pos += self.face * 140
                from .constants import WIDTH, HEIGHT
                self.pos.x = clamp(self.pos.x, 40, WIDTH-40)
                self.pos.y = clamp(self.pos.y, 40, HEIGHT-40)
                self._aoe_damage(self.pos + self.face*20, Q_BURST_RANGE, int(DAMAGE_SWORD*0.9), enemies)
                self.shadow_cd = 1.2
        else:
            if self.dash_cd <= 0 and self.mp >= CHA_Q_COST:
                self.mp -= CHA_Q_COST
                self.pos += self.face * 220
                from .constants import WIDTH, HEIGHT
                self.pos.x = clamp(self.pos.x, 40, WIDTH-40)
                self.pos.y = clamp(self.pos.y, 40, HEIGHT-40)
                self._aoe_damage(self.pos + self.face*18, Q_BURST_RANGE, int(DAMAGE_SWORD*1.0), enemies)
                self.dash_cd = 1.5

    def try_melee(self, enemies):
        if self.attack_cd > 0: return
        if self.equipped == "sword" and self.has_sword:
            rng = SWORD_RANGE; dmg = DAMAGE_SWORD; cd = COOLDOWN_SWORD
        else:
            rng = PUNCH_RANGE; dmg = DAMAGE_PUNCH; cd = COOLDOWN_PUNCH

        self.play_attack()

        hit_pos = self.pos + self.face * (self.radius + rng*0.6)
        self._aoe_damage(hit_pos, rng, dmg, enemies)
        self.last_hit_preview = (hit_pos, rng, 0.10)
        self.attack_cd = cd

    def _aoe_damage(self, center, radius, dmg, enemies):
        for en in enemies:
            if en.alive and (en.pos - center).length() <= (en.radius + radius):
                en.take_damage(dmg)

    def play_pickup(self):
        has_frames = any(len(dir_frames) > 0 for dir_frames in self.pickup8)
        if has_frames:
            self.anim_state = "pickup"
            self.anim_time = 0.0
            self.anim_frame = 0
            self._pickup_once = True

    def play_attack(self):
        self.anim_state = "attack"
        self.anim_time = 0.0
        self.anim_frame = 0
        self._attack_once = True

    # inventory helpers
    def use_hp(self):
        if self.hp_pots > 0 and self.hp < self.max_hp:
            self.hp = min(self.max_hp, self.hp + 40); self.hp_pots -= 1

    def use_mp(self):
        if self.mp_pots > 0 and self.mp < self.max_mp:
            self.mp = min(self.max_mp, self.mp + 20); self.mp_pots -= 1

    # damage/death
    def take_damage(self, dmg, source=None, knockback=0):
        self.hp -= max(1, int(dmg))
        if source is not None:
            dv = self.pos - source
            if dv.length_squared(): dv = dv.normalize()
            self.pos += dv * (knockback * 0.05)
        if self.hp <= 0:
            self._on_death()

    def _on_death(self):
        penalty = min(50, self.gold)
        self.gold -= penalty
        self.hp = self.max_hp
        self.mp = self.max_mp
        self.minions.clear()

    # render
    def draw(self, surf):
        if self.current_img:
            rect = self.current_img.get_rect(center=(int(self.pos.x), int(self.pos.y)))
            surf.blit(self.current_img, rect)
        else:
            col = (90,200,255) if self.who==CHAR_JINWOO else (255,210,120)
            pygame.draw.circle(surf, col, self.pos, self.radius)

        if self.last_hit_preview:
            p, rad, _ = self.last_hit_preview
            pygame.draw.circle(surf, (255,255,255), (int(p.x), int(p.y)), int(rad), 1)

        for m in self.minions:
            m.draw(surf)
    def _dir4_with_fix(self):
        d = dir4_from_vec(self.face)  # 'E','W','N','S'
        if getattr(self, "flip_ew", True):   
            if d == "E": d = "W"
            elif d == "W": d = "E"
        return d
