import sys, pygame
from .constants import FPS, HEIGHT, WIDTH, Keys
from .scenes.menu import SceneMenu
from .state import GameState
from .save import load_game, save_game

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Desert Outpost — Top-Down Shooter")
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
            self.clock.tick(FPS)
            dt = self.clock.get_time() / 1000.0
            events = pygame.event.get()
            for e in events:
                if e.type == pygame.QUIT:
                    if self.state.player:
                        save_game(self.state)
                    pygame.quit(); sys.exit()
                if e.type == pygame.KEYDOWN:
                    if e.mod & pygame.KMOD_CTRL and e.key == pygame.K_s and self.state.player:
                        save_game(self.state)
                        continue
                    if e.key == Keys.QUICK_SAVE and self.state.player:
                        save_game(self.state)
                        continue
                    if e.key == Keys.QUICK_LOAD:
                        from .player import Player

                        if load_game(self.state, lambda who: Player((WIDTH // 2, HEIGHT // 2), who=who)):
                            self._load_scene_from_state()
                        continue
                self.scene.handle(e)
            self.scene.update(dt)
            self.scene.draw(self.screen)
            pygame.display.flip()

    def _load_scene_from_state(self) -> None:
        name = self.state.scene_name or "overworld"
        if name == "overworld":
            from .scenes.overworld import SceneOverworld

            self.change(SceneOverworld(self), name="overworld", autosave=False)
        elif name == "dungeon":
            from .gate import Gate
            from .scenes.dungeon import SceneDungeon

            gate = Gate(pygame.Rect(0, 0, 120, 140), label="Loaded Gate", allow_under=True)
            self.change(SceneDungeon(self, self.state.player, gate), name="dungeon", autosave=False)
        else:
            self.change(SceneMenu(self), name="menu", autosave=False)
