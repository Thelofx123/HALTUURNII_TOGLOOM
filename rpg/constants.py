import pygame


WIDTH, HEIGHT = 1280, 720
FPS = 60

PLAYER_SPEED = 150.0
ATTACK_LOCK_MS = 220
ATTACK_HITBOX_MS = 120
DASH_COOLDOWN_MS = 600
DASH_TIME_MS = 120
DASH_DISTANCE = 160.0

# Colors
COL_BG = (214, 226, 186)
COL_UI = (247, 226, 186)

# Border walls (simple)
BORDER_WALLS = [
    # top, bottom, left, right
    __import__("pygame").Rect(0, 0, WIDTH, 50),
    __import__("pygame").Rect(0, HEIGHT - 50, WIDTH, 50),
    __import__("pygame").Rect(0, 0, 50, HEIGHT),
    __import__("pygame").Rect(WIDTH - 50, 0, 50, HEIGHT),
]

# Combat tuning
DAMAGE_PUNCH = 8
DAMAGE_SWORD = 18
DAMAGE_DAGGER = 22
COOLDOWN_PUNCH = 0.25
COOLDOWN_SWORD = 0.45
PUNCH_RANGE = 28
SWORD_RANGE = 60
Q_BURST_RANGE = 70

# Skills
JIN_Q_COST = 12
CHA_Q_COST = 10

# Minions
MINION_TOUCH_DPS = 14
MINION_SPEED = 180
MINION_MAX = 4
CORPSE_TTL = 5.0

# Vital scaling
HEALTH_PER_END = 5
BASE_HP = 80

# Characters
CHAR_JINWOO = "JINWOO"
CHAR_CHA    = "CHA"


class Keys:
    MOVE_UP = pygame.K_w
    MOVE_DOWN = pygame.K_s
    MOVE_LEFT = pygame.K_a
    MOVE_RIGHT = pygame.K_d
    ATTACK = pygame.K_j
    DASH = pygame.K_k
    INTERACT = pygame.K_e
    INVENTORY = pygame.K_i
    PAUSE = pygame.K_ESCAPE
    QUICK_SAVE = pygame.K_F5
    QUICK_LOAD = pygame.K_F9
