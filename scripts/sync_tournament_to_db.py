import json
import os
from backend.database.connection import SessionLocal
from backend.models.tournament import Tournament, TournamentParticipant, TournamentRound, TournamentMatch
from backend.models.user import User
from backend.models.bot import Bot

def sync_tournament_to_db():
    db = SessionLocal()
    try:
        # 1. Đọc file kết quả
        results_file = "configs/swiss_qualified_bots.json"
        if not os.path.exists(results_file):
            results_file = "bots/all_submitted_bots.json"

        if not os.path.exists(results_file):
            print(f"LỖI: Không tìm thấy file {results_file}. Vui lòng chạy python sync_to_db.py trước!")
            return

        with open(results_file, "r", encoding="utf-8") as f:
            bots_data = json.load(f)

        creator = db.query(User).filter(User.username == "lehieu").first() or db.query(User).first()
        if not creator:
            print("LỖI: Chưa có User trong DB. Hãy chạy python sync_to_db.py trước!")
            return

        champion_user = db.query(User).filter(User.username == "sv_001").first()

        # 2. Tạo bản ghi Giải đấu chính
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

        # 3. Tạo Danh sách Tuyển thủ (đưa vào tab Danh Sách Tuyển Thủ)
        participants = []
        for idx in range(1, min(17, len(bots_data) + 1)):  # Lấy Top 16 thi đấu
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

        # 4. Tạo Vòng đấu & Trận đấu (đưa vào tab Cây Thi Đấu Bracket)
        if len(participants) >= 4:
            # Vòng Bán kết
            round_semi = TournamentRound(
                tournament_id=tourney.id,
                round_number=1,
                round_name="Bán kết",
                status="COMPLETED"
            )
            db.add(round_semi)
            db.commit()
            db.refresh(round_semi)

            # Vòng Chung kết
            round_final = TournamentRound(
                tournament_id=tourney.id,
                round_number=2,
                round_name="Chung kết",
                status="COMPLETED"
            )
            db.add(round_final)
            db.commit()
            db.refresh(round_final)

            # Tạo Trận Bán kết 1
            m1 = TournamentMatch(
                tournament_id=tourney.id,
                round_id=round_semi.id,
                match_order=1,
                player1_id=participants[0][0].id,
                player2_id=participants[3][0].id,
                player1_bot_id=participants[0][1].id if participants[0][1] else None,
                player2_bot_id=participants[3][1].id if participants[3][1] else None,
                winner_id=participants[0][0].id,
                status="COMPLETED"
            )
            # Tạo Trận Bán kết 2
            m2 = TournamentMatch(
                tournament_id=tourney.id,
                round_id=round_semi.id,
                match_order=2,
                player1_id=participants[1][0].id,
                player2_id=participants[2][0].id,
                player1_bot_id=participants[1][1].id if participants[1][1] else None,
                player2_bot_id=participants[2][1].id if participants[2][1] else None,
                winner_id=participants[1][0].id,
                status="COMPLETED"
            )
            db.add_all([m1, m2])
            db.commit()

            # Tạo Trận Chung kết
            m_final = TournamentMatch(
                tournament_id=tourney.id,
                round_id=round_final.id,
                match_order=1,
                player1_id=participants[0][0].id,
                player2_id=participants[1][0].id,
                player1_bot_id=participants[0][1].id if participants[0][1] else None,
                player2_bot_id=participants[1][1].id if participants[1][1] else None,
                winner_id=participants[0][0].id,
                status="COMPLETED"
            )
            db.add(m_final)
            db.commit()

        print(f"=== ĐỒNG BỘ THÀNH CÔNG! Đã cập nhật Cây thi đấu & Tuyển thủ cho Giải #{tourney.id} ===")

    except Exception as e:
        db.rollback()
        print(f"LỖI: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    sync_tournament_to_db()