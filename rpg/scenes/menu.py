import sys
import pygame

from .base import SceneBase
from ..constants import CHAR_JINWOO, CHAR_CHA
from .overworld import SceneOverworld
from ..player import Player
from ..save import load_game


class SceneMenu(SceneBase):
    def __init__(self, game):
        super().__init__(game)

        self.f_title = pygame.font.Font(None, 48)  
        self.f_text  = pygame.font.Font(None, 28)

        self.items = [
            ("SUNG", self._start_as_jinwoo),
            ("HAE", self._start_as_chae),
            ("Load last session",                 self._load_last_patrol),
        ]
        self.sel = 0

        # Colors for black UI
        self.col = {
            "bg": (0, 0, 0),
            "title": (235, 235, 235),
            "subtitle": (200, 200, 200),
            "text": (235, 235, 245),
            "dim": (160, 160, 165),
            "shadow": (0, 0, 0),
            "accent": (255, 180, 0),
            "accent_dark": (150, 90, 0),
            "sel": (255, 255, 255),
        }

    def handle(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % len(self.items)
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % len(self.items)
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate()
            elif e.key == pygame.K_1:
                self.sel = 0; self._activate()
            elif e.key == pygame.K_2:
                self.sel = 1; self._activate()
            elif e.key == pygame.K_l:
                self.sel = 2; self._activate()
            elif e.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit()

    def draw(self, surf):
        surf.fill(self.col["bg"])
        W, H = surf.get_size()

        t = self.f_title.render("Poor Leveling – Character Select", True, self.col["title"])
        surf.blit(t, (W//2 - t.get_width()//2, 110))

        sub = self.f_text.render("Choose your hunter", True, self.col["subtitle"])
        surf.blit(sub, (W//2 - sub.get_width()//2, 150))

        top = 240
        gap = 44
        for i, (label, _) in enumerate(self.items):
            is_sel = (i == self.sel)
            color = self.col["sel"] if is_sel else self.col["text"]
            tex   = self.f_text.render(label, True, color)

            x = W//2 - tex.get_width()//2
            y = top + i*gap

            surf.blit(tex, (x, y))

            if is_sel:
                hh = 10
                pts = [(x - 24, y + tex.get_height()//2),
                       (x - 6,  y + tex.get_height()//2 - hh),
                       (x - 6,  y + tex.get_height()//2 + hh)]
                pygame.draw.polygon(surf, self.col["accent"], pts)
                pygame.draw.polygon(surf, self.col["accent_dark"], pts, 2)
                underline = pygame.Rect(x, y + tex.get_height() + 6, tex.get_width(), 2)
                pygame.draw.rect(surf, self.col["accent"], underline)

        help_line = "[L] Load last save  •  Esc: Quit"
        h = self.f_text.render(help_line, True, self.col["dim"])
        surf.blit(h, (W//2 - h.get_width()//2, top + len(self.items)*gap + 70))

    def _activate(self):
        _, action = self.items[self.sel]
        action()

    def _spawn_player(self, who):
        p = Player((self.game.screen.get_width()//2, self.game.screen.get_height()//2), who=who)
        self.game.state.player = p

    def _start_as_jinwoo(self):
        self._spawn_player(CHAR_JINWOO)
        self.game.change(SceneOverworld(self.game), name="overworld")

    def _start_as_chae(self):
        self._spawn_player(CHAR_CHA)
        self.game.change(SceneOverworld(self.game), name="overworld")

    def _load_last_patrol(self):
        ok = load_game(self.game.state, lambda who: Player((0, 0), who=who))
        if ok:
            self.game.change(SceneOverworld(self.game), name="overworld", autosave=False)
