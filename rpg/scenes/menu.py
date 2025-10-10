import sys, pygame
from .base import SceneBase
from ..constants import CHAR_JINWOO, CHAR_CHA
from .overworld import SceneOverworld
from ..player import Player
from ..save import load_game
from ..utils import load_pixel_font

class SceneMenu(SceneBase):
    def __init__(self, game):
        super().__init__(game)
        self.font = load_pixel_font(48)
        self.small = load_pixel_font(22)

    def _spawn_player(self, who):
        p = Player((self.game.screen.get_width()//2, self.game.screen.get_height()//2), who=who)
        self.game.state.player = p

    def handle(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_1:
                self._spawn_player(CHAR_JINWOO)
                self.game.change(SceneOverworld(self.game), name="overworld")
            elif e.key == pygame.K_2:
                self._spawn_player(CHAR_CHA)
                self.game.change(SceneOverworld(self.game), name="overworld")
            elif e.key == pygame.K_l:  # Load
                ok = load_game(self.game.state, lambda who: Player((0,0), who=who))
                if ok:
                    self.game.change(SceneOverworld(self.game), name="overworld", autosave=False)
            elif e.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit()

    def draw(self, surf):
        surf.fill((18,20,28))
        t = self.font.render("2D Solo Leveling – Character Select", True, (235,235,245))
        surf.blit(t, (surf.get_width()//2 - t.get_width()//2, 140))
        t1 = self.small.render("[1] Sung Jin-woo — Shadow Step (Q)", True, (180,220,255))
        t2 = self.small.render("[2] Cha Hae-In — Sword Dash (Q)", True, (255,230,180))
        surf.blit(t1, (surf.get_width()//2 - t1.get_width()//2, 260))
        surf.blit(t2, (surf.get_width()//2 - t2.get_width()//2, 300))
        surf.blit(
            self.small.render("[L] Load last save  •  Esc: Quit", True, (200, 200, 210)),
            (surf.get_width() // 2 - 180, 360),
        )
        surf.blit(
            self.small.render("F5: Quick Save  •  F9: Quick Load", True, (195, 215, 235)),
            (surf.get_width() // 2 - 160, 400),
        )
