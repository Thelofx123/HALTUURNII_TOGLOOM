import random
import sys, pygame
from .base import SceneBase
from ..constants import CHAR_JINWOO, CHAR_CHA
from .overworld import SceneOverworld
from ..player import Player
from ..save import load_game
from ..utils import load_desert_tile, load_pixel_font

class SceneMenu(SceneBase):
    def __init__(self, game):
        super().__init__(game)
        self.font = load_pixel_font(48)
        self.small = load_pixel_font(22)
        self._background = self._build_background()

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
        if self._background:
            surf.blit(self._background, (0, 0))
        else:
            surf.fill((56, 40, 28))
        title = self.font.render("Desert Outpost Patrol", True, (247, 226, 186))
        surf.blit(title, (surf.get_width() // 2 - title.get_width() // 2, 140))
        prompt = self.small.render("Choose your hunter to defend the oasis", True, (250, 236, 200))
        surf.blit(prompt, (surf.get_width() // 2 - prompt.get_width() // 2, 210))
        t1 = self.small.render("[1] Sung Jin-woo — agile skirmisher", True, (220, 240, 255))
        t2 = self.small.render("[2] Cha Hae-In — relentless duelist", True, (255, 224, 180))
        surf.blit(t1, (surf.get_width() // 2 - t1.get_width() // 2, 260))
        surf.blit(t2, (surf.get_width() // 2 - t2.get_width() // 2, 300))
        surf.blit(
            self.small.render("[L] Load last patrol  •  Esc: Quit", True, (240, 220, 200)),
            (surf.get_width() // 2 - 190, 360),
        )
        surf.blit(
            self.small.render("F5: Quick Save  •  F9: Quick Load", True, (240, 220, 200)),
            (surf.get_width() // 2 - 180, 400),
        )

    def _build_background(self):
        try:
            tile = load_desert_tile("Interface", 147, scale=3.0)
        except FileNotFoundError:
            return None
        surface = pygame.Surface(self.game.screen.get_size(), pygame.SRCALPHA)
        tex_w, tex_h = tile.get_size()
        rng = random.Random(91)
        for y in range(0, surface.get_height(), tex_h):
            for x in range(0, surface.get_width(), tex_w):
                tint = tile.copy()
                if rng.random() < 0.3:
                    tint.fill((255, 210, 180, 25), special_flags=pygame.BLEND_RGBA_ADD)
                surface.blit(tint, (x, y))
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((30, 20, 10, 120))
        surface.blit(overlay, (0, 0))
        return surface.convert_alpha()
