class RuleSet:
    def __init__(self, config: dict):
        self.board_size = config.get("board_size", 9)
        # Giảm số nước đi tối đa từ 200 xuống 50 nước
        self.max_turns = config.get("max_turns", 50)
        # Giảm thời gian suy nghĩ 1 nước đi từ 2 giây xuống 1 giây
        self.move_time_limit = config.get("move_time_limit", 1)
        self.special_cells = config.get("special_cells", False)
        self.fog_of_war = config.get("fog_of_war", False)
        self.display_delay = config.get("display_delay", 1)
        self.obstacles = [tuple(obs) for obs in config.get("obstacles", [])]

    @classmethod
    def default(cls):
        return cls({
            "board_size": 9,
            "max_turns": 50,          # Sửa thành 50 nước đi
            "move_time_limit": 1,     # Sửa thành 1 giây
            "special_cells": False,
            "fog_of_war": False,
            "display_delay": 1,
            "obstacles": []
        })