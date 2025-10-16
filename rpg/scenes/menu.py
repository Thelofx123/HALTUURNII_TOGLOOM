import math
import random
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
        self._background = self._build_background()
        self._menu_items = (
            ("Sung Jin-woo — agile skirmisher", self._start_as_jinwoo),
            ("Cha Hae-In — relentless duelist", self._start_as_chae),
            ("Load last patrol", self._load_last_patrol),
        )
        self._selection = 0

    def _spawn_player(self, who):
        p = Player((self.game.screen.get_width()//2, self.game.screen.get_height()//2), who=who)
        self.game.state.player = p

    def handle(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_UP, pygame.K_w):
                self._selection = (self._selection - 1) % len(self._menu_items)
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self._selection = (self._selection + 1) % len(self._menu_items)
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate_selection()
            elif e.key == pygame.K_1:
                self._selection = 0
                self._activate_selection()
            elif e.key == pygame.K_2:
                self._selection = 1
                self._activate_selection()
            elif e.key == pygame.K_l:  # Load
                self._selection = 2
                self._activate_selection()
            elif e.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit()

    def draw(self, surf):
        if self._background:
            surf.blit(self._background, (0, 0))
        else:
            surf.fill((56, 40, 28))
        title = self.font.render("Desert Outpost Patrol", True, (247, 226, 186))
        surf.blit(title, (surf.get_width() // 2 - title.get_width() // 2, 120))
        prompt = self.small.render("Choose your hunter to defend the oasis", True, (250, 236, 200))
        surf.blit(prompt, (surf.get_width() // 2 - prompt.get_width() // 2, 190))

        list_top = 240
        arrow_offset = 70
        line_spacing = self.small.get_height() + 14
        for idx, (label, _) in enumerate(self._menu_items):
            is_selected = idx == self._selection
            color = (255, 236, 205) if is_selected else (210, 220, 230)
            item = self.small.render(label, True, color)
            x = surf.get_width() // 2 - item.get_width() // 2 + 14
            y = list_top + idx * line_spacing
            if is_selected:
                self._draw_selector_arrow(surf, (x - arrow_offset, y + item.get_height() // 2))
            surf.blit(item, (x, y))

        help_text = self.small.render("↑/↓: Navigate  •  Enter: Confirm  •  Esc: Quit", True, (235, 215, 195))
        surf.blit(help_text, (surf.get_width() // 2 - help_text.get_width() // 2, list_top + len(self._menu_items) * line_spacing + 30))
        quick_text = self.small.render("F5: Quick Save  •  F9: Quick Load", True, (215, 198, 182))
        surf.blit(quick_text, (surf.get_width() // 2 - quick_text.get_width() // 2, list_top + len(self._menu_items) * line_spacing + 70))

    def _build_background(self):
        width, height = self.game.screen.get_size()
        surface = pygame.Surface((width, height)).convert()

        top_color = pygame.Color(26, 17, 13)
        bottom_color = pygame.Color(82, 64, 48)
        for y in range(height):
            t = y / max(1, height - 1)
            color = (
                int(top_color.r + (bottom_color.r - top_color.r) * t),
                int(top_color.g + (bottom_color.g - top_color.g) * t),
                int(top_color.b + (bottom_color.b - top_color.b) * t),
            )
            pygame.draw.line(surface, color, (0, y), (width, y))

        pattern = pygame.Surface((width, height), pygame.SRCALPHA)
        rng = random.Random(123)
        cell = 18
        accent = (255, 220, 180, 18)
        for gy in range(0, height, cell):
            offset = (gy // cell) % 2
            for gx in range(offset * (cell // 2), width, cell):
                if rng.random() < 0.45:
                    pygame.draw.rect(pattern, accent, pygame.Rect(gx, gy, cell // 2, cell // 2))
        surface.blit(pattern, (0, 0))

        spotlight = pygame.Surface((width, height), pygame.SRCALPHA)
        center = pygame.Vector2(width // 2, height // 2 - 60)
        max_radius = math.hypot(width, height) / 2.2
        for radius in range(int(max_radius), 0, -40):
            alpha = max(0, 70 - int((radius / max_radius) * 70))
            if alpha <= 0:
                continue
            pygame.draw.circle(spotlight, (255, 230, 190, alpha), center, radius)
        surface.blit(spotlight, (0, 0))

        vignette = pygame.Surface((width, height), pygame.SRCALPHA)
        for radius in range(30, max(width, height), 40):
            fade = min(140, int(radius * 0.6))
            pygame.draw.circle(vignette, (0, 0, 0, min(180, fade)), (width // 2, height // 2), radius, width=2)
        surface.blit(vignette, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)

        return surface.convert()

    def _draw_selector_arrow(self, surf, center):
        x, y = center
        half_height = self.small.get_height() // 2 + 4
        points = [
            (x, y),
            (x + 24, y - half_height),
            (x + 24, y + half_height),
        ]
        pygame.draw.polygon(surf, (255, 200, 120), points)
        pygame.draw.polygon(surf, (130, 70, 30), points, width=2)

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

    def _activate_selection(self):
        _, action = self._menu_items[self._selection]
        action()
