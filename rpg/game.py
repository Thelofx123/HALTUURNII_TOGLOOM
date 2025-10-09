import sys, pygame
from .constants import WIDTH, HEIGHT, FPS
from .scenes.menu import SceneMenu
from .state import GameState
from .save import save_game

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Solo Leveling 2D — Modular + Save")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.state = GameState()
        self.scene = SceneMenu(self)

    def change(self, scene, name=None, autosave=True):
        if name:
            self.state.scene_name = name
        self.scene = scene
        if autosave and self.state.player:
            save_game(self.state)

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    if self.state.player:
                        save_game(self.state)
                    pygame.quit(); sys.exit()
                if e.type == pygame.KEYDOWN and e.mod & pygame.KMOD_CTRL:
                    if e.key == pygame.K_s and self.state.player:
                        save_game(self.state)
                self.scene.handle(e)
            self.scene.update(dt)
            self.scene.draw(self.screen)
            pygame.display.flip()
