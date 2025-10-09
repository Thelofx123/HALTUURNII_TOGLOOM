import json, os

SAVE_DIR = os.path.join(os.getcwd(), "saves")
SAVE_PATH = os.path.join(SAVE_DIR, "slot1.json")

def ensure_dir():
    if not os.path.isdir(SAVE_DIR):
        os.makedirs(SAVE_DIR, exist_ok=True)

def save_game(state):
    ensure_dir()
    p = state.player
    data = {
        "scene": state.scene_name,
        "unlocked": state.unlocked,
        "player": {
            "who": p.who,
            "pos": [float(p.pos.x), float(p.pos.y)],
            "level": p.leveling.level,
            "xp": p.leveling.xp,
            "xp_to_next": p.leveling.xp_to_next,
            "stat_points": p.leveling.stat_points,
            "skill_points": p.leveling.skill_points,
            "stats": {
                "strength": p.stats.strength, "agility": p.stats.agility,
                "endurance": p.stats.endurance, "defense": p.stats.defense,
                "intelligence": p.stats.intelligence, "precision": p.stats.precision,
                "crit_rate": p.stats.crit_rate, "crit_damage": p.stats.crit_damage,
            },
            "hp": p.hp, "max_hp": p.max_hp, "mp": p.mp, "max_mp": p.max_mp,
            "gold": p.gold,
            "has_dagger": p.has_dagger, "has_sword": p.has_sword, "equipped": p.equipped,
            "hp_pots": p.hp_pots, "mp_pots": p.mp_pots,
        }
    }
    with open(SAVE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_game(state, player_factory):
    if not os.path.isfile(SAVE_PATH):
        return False
    with open(SAVE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    pl = data["player"]
    p = player_factory(pl["who"])

    from pygame import Vector2
    p.pos = Vector2(pl["pos"][0], pl["pos"][1])
    p.leveling.level = pl["level"]
    p.leveling.xp = pl["xp"]
    p.leveling.xp_to_next = pl["xp_to_next"]
    p.leveling.stat_points = pl["stat_points"]
    p.leveling.skill_points = pl["skill_points"]
    # stats
    s = pl["stats"]
    p.stats.strength = s["strength"]; p.stats.agility = s["agility"]
    p.stats.endurance = s["endurance"]; p.stats.defense = s["defense"]
    p.stats.intelligence = s["intelligence"]; p.stats.precision = s["precision"]
    p.stats.crit_rate = s["crit_rate"]; p.stats.crit_damage = s["crit_damage"]
    p.max_hp = pl["max_hp"]; p.hp = min(pl["hp"], p.max_hp)
    p.max_mp = pl["max_mp"]; p.mp = min(pl["mp"], p.max_mp)
    p.gold = pl["gold"]
    p.has_dagger = pl["has_dagger"]; p.has_sword = pl["has_sword"]; p.equipped = pl["equipped"]
    p.hp_pots = pl["hp_pots"]; p.mp_pots = pl["mp_pots"]
    # attach
    state.player = p
    state.unlocked = data.get("unlocked", {})
    state.scene_name = data.get("scene", "menu")
    return True
