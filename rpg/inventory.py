from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Literal, Optional


ItemSlot = Literal["weapon", "armor", "accessory"]


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    slot: ItemSlot
    price: int
    attack_bonus: int = 0
    hp_bonus: float = 0.0
    stamina_bonus: float = 0.0
    description: str = ""


ITEM_LIBRARY: Dict[str, Item] = {
    "training_sword": Item(
        id="training_sword",
        name="Training Sword",
        slot="weapon",
        price=0,
        attack_bonus=2,
        description="Standard issue wooden sword.",
    ),
    "steel_saber": Item(
        id="steel_saber",
        name="Steel Saber",
        slot="weapon",
        price=120,
        attack_bonus=6,
        description="Reliable steel blade favoured by low-rank hunters.",
    ),
    "shadow_dagger": Item(
        id="shadow_dagger",
        name="Shadow Dagger",
        slot="weapon",
        price=180,
        attack_bonus=9,
        stamina_bonus=6.0,
        description="Swift dagger that revitalises stamina on the move.",
    ),
    "glaive_of_light": Item(
        id="glaive_of_light",
        name="Glaive of Light",
        slot="weapon",
        price=260,
        attack_bonus=12,
        stamina_bonus=-4.0,
        description="Heavy glaive with radiant reach.",
    ),
    "leather_jacket": Item(
        id="leather_jacket",
        name="Leather Jacket",
        slot="armor",
        price=80,
        hp_bonus=12.0,
        description="Supple hide jacket for light defence.",
    ),
    "hunter_mail": Item(
        id="hunter_mail",
        name="Hunter Mail",
        slot="armor",
        price=180,
        hp_bonus=24.0,
        description="Plated mail that shrugs off glancing blows.",
    ),
    "shadow_cloak": Item(
        id="shadow_cloak",
        name="Shadow Cloak",
        slot="armor",
        price=240,
        hp_bonus=10.0,
        stamina_bonus=8.0,
        description="Cloak that pulses with latent mana.",
    ),
    "focus_ring": Item(
        id="focus_ring",
        name="Focus Ring",
        slot="accessory",
        price=140,
        stamina_bonus=14.0,
        description="Ring that steadies the mind for longer fights.",
    ),
    "assault_band": Item(
        id="assault_band",
        name="Assault Band",
        slot="accessory",
        price=200,
        attack_bonus=4,
        description="Bandolier that tightens grip on weapons.",
    ),
    "guardian_charm": Item(
        id="guardian_charm",
        name="Guardian Charm",
        slot="accessory",
        price=220,
        hp_bonus=18.0,
        description="Charm etched with protective sigils.",
    ),
}


class Inventory:
    """Collection of owned items with slot-based equipment."""

    def __init__(self) -> None:
        self._owned: set[str] = set()
        self._equipped: Dict[ItemSlot, str] = {}
        self.ensure_default()

    # ------------------------------------------------------------------
    def ensure_default(self) -> None:
        if "training_sword" not in self._owned:
            self._owned.add("training_sword")
        if self._equipped.get("weapon") not in self._owned:
            self._equipped["weapon"] = "training_sword"

    # ------------------------------------------------------------------
    def owned(self) -> List[Item]:
        return [ITEM_LIBRARY[item_id] for item_id in sorted(self._owned)]

    def equipped(self) -> Dict[ItemSlot, Item]:
        return {
            slot: ITEM_LIBRARY[item_id]
            for slot, item_id in self._equipped.items()
            if item_id in ITEM_LIBRARY
        }

    def is_owned(self, item_id: str) -> bool:
        return item_id in self._owned

    def equip(self, item_id: str) -> Optional[Item]:
        item = ITEM_LIBRARY.get(item_id)
        if not item or item_id not in self._owned:
            return None
        self._equipped[item.slot] = item_id
        return item

    def purchase(self, item_id: str, available_gold: int) -> tuple[bool, int]:
        item = ITEM_LIBRARY.get(item_id)
        if not item or item_id in self._owned:
            return False, 0
        if available_gold < item.price:
            return False, 0
        self._owned.add(item_id)
        self._equipped.setdefault(item.slot, item_id)
        return True, item.price

    def unequip_slot(self, slot: ItemSlot) -> None:
        if slot in self._equipped and self._equipped[slot] != "training_sword":
            self._equipped.pop(slot, None)
        if slot == "weapon" and "training_sword" in self._owned:
            self._equipped[slot] = "training_sword"

    def stat_bonuses(self) -> dict[str, float]:
        attack = 0
        hp = 0.0
        stamina = 0.0
        for item in self.equipped().values():
            attack += item.attack_bonus
            hp += item.hp_bonus
            stamina += item.stamina_bonus
        return {"attack": attack, "hp": hp, "stamina": stamina}

    def data(self) -> dict:
        return {"owned": sorted(self._owned), "equipped": dict(self._equipped)}

    @classmethod
    def from_data(cls, data: Optional[dict]) -> "Inventory":
        inv = cls()
        if not data:
            return inv
        owned = data.get("owned") or []
        equipped = data.get("equipped") or {}
        inv._owned.update(item_id for item_id in owned if item_id in ITEM_LIBRARY)
        for slot, item_id in equipped.items():
            if item_id in inv._owned and item_id in ITEM_LIBRARY:
                inv._equipped[slot] = item_id
        inv.ensure_default()
        return inv

    def catalogue(self) -> List[Item]:
        return sorted(ITEM_LIBRARY.values(), key=lambda item: (item.slot, item.price))


def item_by_index(index: int) -> Optional[Item]:
    catalogue = sorted(ITEM_LIBRARY.values(), key=lambda item: (item.slot, item.price))
    if 0 <= index < len(catalogue):
        return catalogue[index]
    return None
