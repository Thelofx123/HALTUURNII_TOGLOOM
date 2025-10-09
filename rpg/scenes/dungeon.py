import random, pygame
from .base import SceneBase
from ..constants import COL_UI, CORPSE_TTL
from ..enemy import Enemy
from ..items import GroundItem
from ..projectiles import DaggerProjectile
from ..save import save_game

class SceneDungeon(SceneBase):
    def __init__(self, game, player, gate_label="Gate", gate_level=1):
        super().__init__(game)
        self.player = player
        self.player.pos = pygame.Vector2(100, self.game.screen.get_height()//2)
        self.player.game_enemies = []
        self.font = pygame.font.SysFont(None, 24)
        self.items, self.projectiles = [], []
        self.area_rect = pygame.Rect(20, 20, self.game.screen.get_width()-40, self.game.screen.get_height()-40)

        self.enemies = []
        for _ in range(6):
            self.enemies.append(Enemy((random.randint(260, self.game.screen.get_width()-120), random.randint(120, self.game.screen.get_height()-120)), hp=50, xp_reward=35, area_rect=self.area_rect))
        self.boss = Enemy((self.game.screen.get_width()-220, self.game.screen.get_height()//2), hp=180, xp_reward=120, boss=True, area_rect=self.area_rect)
        self.enemies.append(self.boss)
        self.player.game_enemies = self.enemies

        self.exit_rect = pygame.Rect(20, self.game.screen.get_height()//2-40, 30, 80)
        self.gate_label = gate_label

    def handle(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                from .overworld import SceneOverworld
                self.game.change(SceneOverworld(self.game), name="overworld")
            if e.key == pygame.K_q:
                self.player.try_skill(self.enemies)
            if e.key == pygame.K_f and self.player.has_dagger:
                self.projectiles.append(DaggerProjectile(self.player.pos, self.player.face))
                self.player.has_dagger = False
            if e.key == pygame.K_e and self.player.who == "JINWOO":
                if len(self.player.minions) < 4:
                    for it in list(self.items):
                        if it.kind == "corpse" and it.collides_player(self.player):
                            self.player.play_pickup()
                            self.items.remove(it)
                            from ..minion import Minion
                            self.player.minions.append(Minion(it.pos))
                            break
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.player.try_melee(self.enemies)

    def update(self, dt):
        keys = pygame.key.get_pressed()
        self.player.update(dt, keys, world_rect=self.area_rect)

        for p in list(self.projectiles):
            p.update(dt, [self.area_rect], self.items, self.enemies)
            if not p.alive and p.drop_spawned:
                self.projectiles.remove(p)

        for en in self.enemies:
            if (not en.alive) and (not en.rewarded):
                self.items.append(GroundItem(en.pos, "corpse", ttl=CORPSE_TTL))
                self.player.leveling.gain_xp(en.xp_reward)
                self.player.gold += (random.randint(8, 20) if not en.boss else random.randint(40, 80))
                en.rewarded = True

        # corpses & rewards
        for en in list(self.enemies):
            if not en.alive and not any((it.kind=="corpse" and (it.pos - en.pos).length() < 1) for it in self.items):
                self.items.append(GroundItem(en.pos, "corpse", ttl=CORPSE_TTL))
                self.player.leveling.gain_xp(en.xp_reward)
                self.player.gold += random.randint(8, 20) if not en.boss else random.randint(40, 80)

        # decay corpses/items
        for it in list(self.items):
            it.update(dt)
            if it.expired(): self.items.remove(it)

        # death warp back to overworld if hp <= 0
        if self.player.hp <= 0:
            from .overworld import SceneOverworld
            self.game.change(SceneOverworld(self.game), name="overworld")
            return

        # exit
        if self.exit_rect.collidepoint(self.player.pos.x, self.player.pos.y):
            from .overworld import SceneOverworld
            self.game.change(SceneOverworld(self.game), name="overworld")
            return
        
        if all((not en.alive) for en in self.enemies):
            self.game.state.unlocked[self.gate_label] = True
            if not hasattr(self, "_clear_timer"):
                self._clear_timer = 1
            else:
                self._clear_timer -= dt
                if self._clear_timer <= 0:
                    from .overworld import SceneOverworld
                    self.game.change(SceneOverworld(self.game), name="overworld")
                    return

    def draw(self, surf):
        surf.fill((20,22,26))
        pygame.draw.rect(surf, (60,65,75), self.area_rect, 2)
        pygame.draw.rect(surf, (80,120,80), self.exit_rect)

        for it in self.items: it.draw(surf)
        for p in self.projectiles: p.draw(surf)
        for en in self.enemies: en.draw(surf)
        self.player.draw(surf)

        hud = f"{self.gate_label}  |  Lv {self.player.leveling.level}  XP {self.player.leveling.xp}/{self.player.leveling.xp_to_next}  HP {int(self.player.hp)}/{self.player.max_hp}  MP {int(self.player.mp)}/{self.player.max_mp}  Gold {self.player.gold}"
        surf.blit(self.font.render(hud, True, (235,235,245)), (24, 24))
        surf.blit(self.font.render("Esc: Exit  |  E: Extract corpse (Jin-woo)  |  Defeat boss to clear", True, (195,205,210)), (24, 52))
