import sys
import os

# Thêm thư mục gốc vào sys.path để Python nhận diện module 'backend'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
from backend.database.connection import SessionLocal
from backend.models.bot import Bot, BotVersion
from backend.models.user import User
from backend.models.player_stat import PlayerStat

def sync_results():
    db = SessionLocal()
    try:
        # Lấy file kết quả sơ loại / swiss
        results_file = "configs/swiss_qualified_bots.json"
        if not os.path.exists(results_file):
            results_file = "bots/all_submitted_bots.json"

        if not os.path.exists(results_file):
            print(f"LỖI: Không tìm thấy file {results_file}. Hãy chạy python generate_test_bots.py trước!")
            return

        with open(results_file, "r", encoding="utf-8") as f:
            bots_data = json.load(f)

        print(f"Đang đồng bộ {len(bots_data)} Bot & Sinh viên vào Cơ sở dữ liệu Neon...")

        for idx, item in enumerate(bots_data, start=1):
            bot_name = item.get("name", f"Bot_SinhVien_{idx}")
            username = f"sv_{idx:03d}"
            email = f"sv_{idx:03d}@uet.vnu.edu.vn"
            script_path = item.get("script_path", "bots/examples/random_bot.py")

            # 1. Tạo hoặc lấy User
            user = db.query(User).filter(User.username == username).first()
            if not user:
                user = User(
                    username=username,
                    email=email,
                    hashed_password="hashed_password_sample"
                )
                db.add(user)
                db.flush()  # Dùng flush thay vì commit để không tốn network round-trip

            # 2. Tạo hoặc lấy Bot & Phiên bản Bot (BotVersion)
            bot = db.query(Bot).filter(Bot.name == bot_name, Bot.user_id == user.id).first()
            if not bot:
                bot = Bot(
                    user_id=user.id,
                    name=bot_name,
                    description=f"Bot thuộc về sinh viên {username}",
                    status="READY"
                )
                db.add(bot)
                db.flush()

                # Lưu đường dẫn file vào BotVersion
                bot_version = BotVersion(
                    bot_id=bot.id,
                    version_number=1,
                    file_path=script_path,
                    status="READY"
                )
                db.add(bot_version)
                db.flush()

                bot.current_version_id = bot_version.id

            # 3. Cập nhật Thống kê & Điểm số (PlayerStat)
            stat = db.query(PlayerStat).filter(PlayerStat.user_id == user.id).first()
            wins = max(0, len(bots_data) - idx)
            draws = 1
            losses = idx - 1
            points = wins * 3 + draws

            if not stat:
                stat = PlayerStat(
                    user_id=user.id,
                    total_matches=wins + draws + losses,
                    wins=wins,
                    draws=draws,
                    losses=losses,
                    total_points=points
                )
                db.add(stat)
            else:
                stat.wins = wins
                stat.draws = draws
                stat.losses = losses
                stat.total_matches = wins + draws + losses
                stat.total_points = points

            if idx % 20 == 0 or idx == len(bots_data):
                print(f"  -> Đã xử lý {idx}/{len(bots_data)} bot...")

        # Gửi duy nhất 1 giao dịch commit cuối cùng cho toàn bộ 128 bot
        db.commit()
        print("=== ĐỒNG BỘ THÀNH CÔNG! Bảng xếp hạng đã cập nhật vào Database Neon ===")

    except Exception as e:
        db.rollback()
        print(f"LỖI khi đồng bộ: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    sync_results()