import os
import json
from typing import Optional, Dict, Any
from game.rule_set import RuleSet

class TournamentRuleManager:
    """Quản lý và áp dụng luật thi đấu theo từng giai đoạn của giải đấu"""
    def __init__(self, configs_dir: Optional[str] = None):
        if configs_dir:
            self.configs_dir = configs_dir
        else:
            # Tự động tìm thư mục configs ở cả gốc dự án lẫn thư mục con
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            candidate_1 = os.path.join(base_dir, 'configs')
            candidate_2 = os.path.abspath(os.path.join(base_dir, '..', 'configs'))

            if os.path.exists(candidate_1):
                self.configs_dir = candidate_1
            elif os.path.exists(candidate_2):
                self.configs_dir = candidate_2
            else:
                self.configs_dir = candidate_1

        self.configs: Dict[str, Dict[str, Any]] = {}
        self._load_configs()

    def _load_configs(self):
        if not os.path.exists(self.configs_dir):
            return
        for file in os.listdir(self.configs_dir):
            if file.endswith('.json'):
                key = file.replace('.json', '')
                try:
                    with open(os.path.join(self.configs_dir, file), 'r', encoding='utf-8') as f:
                        self.configs[key] = json.load(f)
                except Exception:
                    pass

    def get_stage_config(self, stage: str) -> Dict[str, Any]:
        alias = {
            "round_of_32": "top32",
            "round_of_16": "top16",
            "quarterfinal": "quarterfinal",
            "semifinal": "semifinal",
            "final": "final",
            "qualification": "qualification",
            "swiss": "swiss_stage"
        }
        key = alias.get(stage, stage)
        # Nếu không tìm thấy file cấu hình stage yêu cầu, tự động lấy qualification làm mặc định
        return self.configs.get(key) or self.configs.get("qualification", {})

    def get_rule_set_for_stage(self, stage: str) -> RuleSet:
        stage_cfg = self.get_stage_config(stage)
        comp_rules = self.configs.get("competition", {}).get("game_rules", {})

        # 1. Kích thước bàn cờ (ưu tiên stage_cfg -> competition.json -> mặc định 9)
        board_size = stage_cfg.get("board_size", comp_rules.get("board_width", 9))

        # 2. Số lượt tối đa (ưu tiên stage_cfg -> competition.json -> mặc định 50)
        max_turns = stage_cfg.get("max_turns", comp_rules.get("max_turns_per_game", 50))

        # 3. Thời gian suy nghĩ mỗi nước đi (giây)
        time_limit_sec = stage_cfg.get("time_limit_per_move")
        if time_limit_sec is None:
            time_limit_ms = comp_rules.get("time_limit_per_move_ms", 2000)
            time_limit_sec = time_limit_ms / 1000.0

        # 4. Danh sách chướng ngại vật
        obstacles = stage_cfg.get("obstacles", [])

        return RuleSet({
            "board_size": board_size,
            "max_turns": max_turns,
            "move_time_limit": time_limit_sec,
            "obstacles": obstacles
        })