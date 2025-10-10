from __future__ import annotations

import json
import os
from typing import Callable

from pygame import Vector2

from .inventory import Inventory

SAVE_DIR = os.path.join(os.getcwd(), "save")
SAVE_PATH = os.path.join(SAVE_DIR, "slot1.json")


def ensure_dir() -> None:
    if not os.path.isdir(SAVE_DIR):
        os.makedirs(SAVE_DIR, exist_ok=True)


def save_game(state) -> None:
    if not state.player:
        return
    ensure_dir()
    player = state.player
    state.gold = int(getattr(player, "gold", 0))
    data = {
        "map": state.scene_name or "overworld",
        "pos": [float(player.pos.x), float(player.pos.y)],
        "hp": int(player.hp),
        "stamina": float(player.stamina),
        "who": getattr(player, "who", "JINWOO"),
        "level": player.leveling.level,
        "xp": player.leveling.xp,
        "xp_to_next": player.leveling.xp_to_next,
        "gold": state.gold,
        "inventory": player.inventory.data(),
    }
    with open(SAVE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_game(state, player_factory: Callable[[str], object]) -> bool:
    if not os.path.isfile(SAVE_PATH):
        print("[info] no save found to load")
        return False
    with open(SAVE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    who = data.get("who", "JINWOO")
    player = state.player or player_factory(who)
    if getattr(player, "who", who) != who:
        player = player_factory(who)
    pos = data.get("pos", [0, 0])
    player.pos = Vector2(pos[0], pos[1])
    player.hp = max(0, min(player.max_hp, int(data.get("hp", player.hp))))
    player.stamina = max(0.0, min(player.max_stamina, float(data.get("stamina", player.stamina))))
    player.leveling.level = int(data.get("level", player.leveling.level))
    player.leveling.xp = int(data.get("xp", player.leveling.xp))
    player.leveling.xp_to_next = int(data.get("xp_to_next", player.leveling.xp_to_next))
    player.gold = int(data.get("gold", getattr(player, "gold", 0)))
    player.inventory = Inventory.from_data(data.get("inventory"))
    player.recalculate_stats(full_heal=False)

    state.player = player
    state.gold = player.gold
    state.scene_name = data.get("map", "overworld")
    return True
