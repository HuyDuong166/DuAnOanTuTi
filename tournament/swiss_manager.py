import os
import json
from typing import List, Dict
from .swiss import SwissSystem
from game.game_engine import GameEngine
from game.rule_set import RuleSet
from game.move import Move
from game.piece import Team
from judge.match_runner import DockerBotWrapper

class SwissTournamentManager:
    def __init__(self, bots: List[Dict[str, str]], total_rounds: int = 3, config_path: str = "configs/swiss_stage.json"):
        self.bots = {bot['id']: bot for bot in bots}
        self.total_rounds = total_rounds
        self.swiss = SwissSystem(player_ids=list(self.bots.keys()))

        # Đọc cấu hình giai đoạn Swiss
        self.config = {}
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        self.rule_set = RuleSet(self.config)

    def _run_single_match(self, bot1_path: str, bot2_path: str) -> int:
        bot_a = DockerBotWrapper(bot_dir=os.path.abspath(bot1_path), team_name="RED")
        bot_b = DockerBotWrapper(bot_dir=os.path.abspath(bot2_path), team_name="BLUE")
        engine = GameEngine(self.rule_set)
        
        winner_team = None
        try:
            for _ in range(self.rule_set.max_turns):
                winner = engine.check_winner(engine.state)
                if winner:
                    winner_team = winner.winner
                    break
                
                current_bot = bot_a if engine.state.current_team == Team.RED else bot_b
                try:
                    move_dict = current_bot.get_move(engine.state.to_dict())
                    move = Move.from_dict(move_dict)
                except Exception:
                    losing_team = engine.state.current_team
                    winner_team = Team.BLUE if losing_team == Team.RED else Team.RED
                    break

                if not engine.is_valid_move(engine.state, move):
                    losing_team = engine.state.current_team
                    winner_team = Team.BLUE if losing_team == Team.RED else Team.RED
                    break

                engine.apply_move(engine.state, move)
        finally:
            bot_a.close()
            bot_b.close()

        if winner_team == Team.RED:
            return 1
        elif winner_team == Team.BLUE:
            return 2
        return 0

    def run_tournament(self):
        print(f"=== BẮT ĐẦU GIẢI ĐẤU SWISS SYSTEM ({len(self.bots)} BOTS - {self.total_rounds} VÒNG) ===")

        for round_num in range(1, self.total_rounds + 1):
            print(f"\n--- THI ĐẤU VÒNG {round_num}/{self.total_rounds} ---")
            pairings = self.swiss.generate_pairings()

            for p1_id, p2_id in pairings:
                bot1 = self.bots[p1_id]
                bot2 = self.bots[p2_id]
                print(f"  [Trận đấu] {bot1['name']} (Điểm: {self.swiss.scores[p1_id]}) vs {bot2['name']} (Điểm: {self.swiss.scores[p2_id]})")

                winner = self._run_single_match(bot1['path'], bot2['path'])

                if winner == 1:
                    print(f"   -> Kết quả: {bot1['name']} THẮNG!")
                    self.swiss.record_match_result(p1_id, p2_id, winner_id=p1_id)
                elif winner == 2:
                    print(f"   -> Kết quả: {bot2['name']} THẮNG!")
                    self.swiss.record_match_result(p1_id, p2_id, winner_id=p2_id)
                else:
                    print(f"   -> Kết quả: HÒA!")
                    self.swiss.record_match_result(p1_id, p2_id, is_draw=True)

        self.display_rankings()

    def display_rankings(self):
        print("\n================ BẢNG XẾP HẠNG CHUNG CUỘC (SWISS) ================")
        ranked = sorted(self.swiss.scores.items(), key=lambda x: x[1], reverse=True)
        for rank, (p_id, score) in enumerate(ranked, 1):
            bot_name = self.bots[p_id]['name']
            print(f" Hạng {rank}: {bot_name:<18} | Điểm số: {score}")