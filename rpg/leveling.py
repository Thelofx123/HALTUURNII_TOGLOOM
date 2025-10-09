class Leveling:
    def __init__(self):
        self.level = 1
        self.xp = 0
        self.xp_to_next = 100
        self.stat_points = 0
        self.skill_points = 0

    def gain_xp(self, amt: int) -> bool:
        self.xp += amt
        leveled = False
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            self.stat_points += 5
            self.skill_points += 1
            self.xp_to_next = int(self.xp_to_next * 1.25)
            leveled = True
        return leveled
