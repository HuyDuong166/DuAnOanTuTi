import sys
import os

# Thêm thư mục gốc vào sys.path để Python nhận diện module 'backend' và 'game'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import random
from backend.database.connection import SessionLocal
from backend.models.tournament import Tournament, TournamentParticipant, TournamentRound, TournamentMatch
from backend.models.match import Match
from backend.models.user import User
from backend.models.bot import Bot
from game.game_engine import GameEngine
from game.piece import Team
from tournament.rule_manager import TournamentRuleManager

def sync_tournament_to_db():
    db = SessionLocal()
    try:
        results_file = "configs/swiss_qualified_bots.json"
        if not os.path.exists(results_file):
            results_file = "bots/all_submitted_bots.json"

        if not os.path.exists(results_file):
            print(f"LỖI: Không tìm thấy file {results_file}. Vui lòng chạy python generate_test_bots.py trước!")
            return

        with open(results_file, "r", encoding="utf-8") as f:
            bots_data = json.load(f)

        creator = db.query(User).filter(User.is_admin == True).first() or db.query(User).first()
        if not creator:
            print("LỖI: Chưa có User trong DB. Hãy chạy python -m scripts.sync_to_db trước!")
            return

        champion_user = db.query(User).filter(User.username == "sv_001").first()

        tourney = Tournament(
            name="UET Hybrid Battle 2026 (4000 SV)",
            description="Giải đấu Phối hợp (Sơ loại 128 bảng + Top 128 Swiss Stage)",
            creator_id=creator.id,
            min_participants=4,
            max_participants=len(bots_data),
            status="COMPLETED",
            champion_id=champion_user.id if champion_user else creator.id
        )
        db.add(tourney)
        db.commit()
        db.refresh(tourney)

        participants = []
        for idx in range(1, min(17, len(bots_data) + 1)):
            username = f"sv_{idx:03d}"
            user = db.query(User).filter(User.username == username).first()
            if user:
                bot = db.query(Bot).filter(Bot.user_id == user.id).first()
                participant = TournamentParticipant(
                    tournament_id=tourney.id,
                    user_id=user.id,
                    bot_id=bot.id if bot else None,
                    status="ACCEPTED",
                    seed=idx
                )
                db.add(participant)
                participants.append((user, bot))
        db.commit()

        # Hàm mô phỏng trận đấu thực tế bằng GameEngine
        def run_real_simulated_match(red_id, blue_id, red_bot_id, blue_bot_id):
            rule_mgr = TournamentRuleManager()
            rule_set = rule_mgr.get_rule_set_for_stage("final")
            engine = GameEngine(rule_set)

            initial_board = engine.state.to_dict()["board"]
            moves_log = []
            winner_user_id = None
            reason = "Trận đấu loại trực tiếp kết thúc thành công"

            for _ in range(40):
                winner_res = engine.check_winner(engine.state)
                if winner_res and winner_res.winner:
                    winner_user_id = red_id if winner_res.winner == Team.RED else blue_id
                    reason = winner_res.reason
                    break

                curr_team = engine.state.current_team
                legal_moves = engine.state.get_legal_moves()
                if not legal_moves:
                    winner_user_id = blue_id if curr_team == Team.RED else red_id
                    reason = f"Bot {'Đỏ' if curr_team == Team.RED else 'Xanh'} hết nước đi hợp lệ"
                    break

                mv = random.choice(legal_moves)
                engine.apply_move(engine.state, mv)
                moves_log.append({
                    "turn": engine.state.turn,
                    "team": curr_team.value,
                    "player": curr_team.value.lower(),
                    "from": list(mv.from_pos),
                    "to": list(mv.to_pos),
                    "board_after": engine.state.to_dict()["board"]
                })

            if not winner_user_id:
                winner_user_id = red_id
                reason = "Phân định thắng cuộc sau số lượt tối đa"

            match_rec = Match(
                match_type="TOURNAMENT",
                red_user_id=red_id,
                blue_user_id=blue_id,
                winner_user_id=winner_user_id,
                red_bot_id=red_bot_id,
                blue_bot_id=blue_bot_id,
                is_draw=False,
                status="COMPLETED",
                termination_reason=reason,
                moves_json=json.dumps(moves_log),
                initial_board_json=json.dumps(initial_board),
                total_turns=len(moves_log)
            )
            db.add(match_rec)
            db.flush()
            return match_rec.id, winner_user_id

        if len(participants) >= 4:
            round_semi = TournamentRound(tournament_id=tourney.id, round_number=1, round_name="Bán kết", status="COMPLETED")
            round_final = TournamentRound(tournament_id=tourney.id, round_number=2, round_name="Chung kết", status="COMPLETED")
            db.add_all([round_semi, round_final])
            db.commit()

            # Bán kết 1
            m1_id, w1 = run_real_simulated_match(
                participants[0][0].id, participants[3][0].id,
                participants[0][1].id if participants[0][1] else None, participants[3][1].id if participants[3][1] else None
            )
            m1 = TournamentMatch(
                tournament_id=tourney.id, round_id=round_semi.id, match_order=1,
                player1_id=participants[0][0].id, player2_id=participants[3][0].id,
                winner_id=w1, status="COMPLETED", match_id=m1_id
            )

            # Bán kết 2
            m2_id, w2 = run_real_simulated_match(
                participants[1][0].id, participants[2][0].id,
                participants[1][1].id if participants[1][1] else None, participants[2][1].id if participants[2][1] else None
            )
            m2 = TournamentMatch(
                tournament_id=tourney.id, round_id=round_semi.id, match_order=2,
                player1_id=participants[1][0].id, player2_id=participants[2][0].id,
                winner_id=w2, status="COMPLETED", match_id=m2_id
            )
            db.add_all([m1, m2])
            db.commit()

            # Chung kết
            mf_id, wf = run_real_simulated_match(
                w1, w2,
                participants[0][1].id if participants[0][1] else None, participants[1][1].id if participants[1][1] else None
            )
            m_final = TournamentMatch(
                tournament_id=tourney.id, round_id=round_final.id, match_order=1,
                player1_id=w1, player2_id=w2,
                winner_id=wf, status="COMPLETED", match_id=mf_id
            )
            db.add(m_final)
            tourney.champion_id = wf
            db.commit()

        print(f"=== ĐỒNG BỘ THÀNH CÔNG! Đã tự động tạo Replay cờ chuẩn cho Giải #{tourney.id} ===")

    except Exception as e:
        db.rollback()
        print(f"LỖI: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    sync_tournament_to_db()