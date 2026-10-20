import json
import os
import random
from backend.database.connection import SessionLocal
from backend.models.tournament import Tournament, TournamentParticipant, TournamentRound, TournamentMatch
from backend.models.match import Match
from backend.models.user import User
from backend.models.bot import Bot

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

        # Lấy Admin / User đầu tiên làm người tạo giải
        creator = db.query(User).filter(User.is_admin == True).first() or db.query(User).first()
        if not creator:
            print("LỖI: Chưa có User trong DB. Hãy chạy python -m scripts.sync_to_db trước!")
            return

        champion_user = db.query(User).filter(User.username == "sv_001").first()

        # Tạo giải đấu
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

        # Tạo tuyển thủ
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

        # Hàm bổ trợ sinh dữ liệu replay bàn cờ giả lập
        def create_replay_match(red_id, blue_id, winner_id, red_bot_id, blue_bot_id):
            # Tạo bàn cờ 9x9 rỗng với chướng ngại vật
            board = [[0]*9 for _ in range(9)]
            board[0][0] = 1  # Rock Red
            board[8][8] = 4  # Rock Blue
            board[4][4] = -1 # Obstacle
            
            moves = [
                {"turn": 1, "team": "RED", "player": "red", "from": [0,0], "to": [0,1], "board_after": board},
                {"turn": 2, "team": "BLUE", "player": "blue", "from": [8,8], "to": [8,7], "board_after": board}
            ]
            
            match_rec = Match(
                match_type="TOURNAMENT",
                red_user_id=red_id,
                blue_user_id=blue_id,
                winner_user_id=winner_id,
                red_bot_id=red_bot_id,
                blue_bot_id=blue_bot_id,
                is_draw=False,
                status="COMPLETED",
                termination_reason="Trận đấu kết thúc bình thường",
                moves_json=json.dumps(moves),
                initial_board_json=json.dumps(board),
                total_turns=len(moves)
            )
            db.add(match_rec)
            db.flush()
            return match_rec.id

        if len(participants) >= 4:
            round_semi = TournamentRound(tournament_id=tourney.id, round_number=1, round_name="Bán kết", status="COMPLETED")
            round_final = TournamentRound(tournament_id=tourney.id, round_number=2, round_name="Chung kết", status="COMPLETED")
            db.add_all([round_semi, round_final])
            db.commit()

            # Trận Bán kết 1
            m1_id = create_replay_match(participants[0][0].id, participants[3][0].id, participants[0][0].id, 
                                        participants[0][1].id if participants[0][1] else None, participants[3][1].id if participants[3][1] else None)
            m1 = TournamentMatch(
                tournament_id=tourney.id, round_id=round_semi.id, match_order=1,
                player1_id=participants[0][0].id, player2_id=participants[3][0].id,
                player1_bot_id=participants[0][1].id if participants[0][1] else None,
                player2_bot_id=participants[3][1].id if participants[3][1] else None,
                winner_id=participants[0][0].id, status="COMPLETED", match_id=m1_id
            )

            # Trận Bán kết 2
            m2_id = create_replay_match(participants[1][0].id, participants[2][0].id, participants[1][0].id,
                                        participants[1][1].id if participants[1][1] else None, participants[2][1].id if participants[2][1] else None)
            m2 = TournamentMatch(
                tournament_id=tourney.id, round_id=round_semi.id, match_order=2,
                player1_id=participants[1][0].id, player2_id=participants[2][0].id,
                player1_bot_id=participants[1][1].id if participants[1][1] else None,
                player2_bot_id=participants[2][1].id if participants[2][1] else None,
                winner_id=participants[1][0].id, status="COMPLETED", match_id=m2_id
            )
            db.add_all([m1, m2])
            db.commit()

            # Trận Chung kết
            mf_id = create_replay_match(participants[0][0].id, participants[1][0].id, participants[0][0].id,
                                        participants[0][1].id if participants[0][1] else None, participants[1][1].id if participants[1][1] else None)
            m_final = TournamentMatch(
                tournament_id=tourney.id, round_id=round_final.id, match_order=1,
                player1_id=participants[0][0].id, player2_id=participants[1][0].id,
                player1_bot_id=participants[0][1].id if participants[0][1] else None,
                player2_bot_id=participants[1][1].id if participants[1][1] else None,
                winner_id=participants[0][0].id, status="COMPLETED", match_id=mf_id
            )
            db.add(m_final)
            db.commit()

        print(f"=== ĐỒNG BỘ THÀNH CÔNG! Đã cập nhật Replay & Cây thi đấu cho Giải #{tourney.id} ===")

    except Exception as e:
        db.rollback()
        print(f"LỖI: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    sync_tournament_to_db()