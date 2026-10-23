import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tournament.swiss_manager import SwissTournamentManager

if __name__ == "__main__":
    qualified_file = "configs/swiss_qualified_bots.json"

    # 1. Tự động kiểm tra nguồn dữ liệu bot
    if os.path.exists(qualified_file):
        print(f"=== Đã tìm thấy dữ liệu Vòng Loại: {qualified_file} ===")
        with open(qualified_file, "r", encoding="utf-8") as f:
            bots = json.load(f)
        total_rounds = 5  # Số vòng Thụy Sĩ cho giải đấu chính thức
    else:
        print("=== Không tìm thấy dữ liệu Vòng Loại. Chạy chế độ Demo với 4 Bot mẫu ===")
        bots = [
            {"id": 1, "name": "RandomBot", "path": "bots/examples/random_bot.py"},
            {"id": 2, "name": "GreedyBot", "path": "bots/examples/greedy_bot.py"},
            {"id": 3, "name": "AggressiveBot", "path": "bots/examples/aggressive_bot.py"},
            {"id": 4, "name": "TacticalBot", "path": "bots/examples/tactical_bot.py"}
        ]
        total_rounds = 3

    # Chuẩn hóa key 'bot_id' thành 'id' để tương thích với SwissTournamentManager
    formatted_bots = []
    for idx, b in enumerate(bots, start=1):
        formatted_bots.append({
            "id": b.get("id") or b.get("bot_id") or idx,
            "name": b.get("name", f"Bot_{idx}"),
            "path": b.get("path") or b.get("script_path", "")
        })

    print(f"Bắt đầu Vòng Thụy Sĩ với {len(formatted_bots)} bot ({total_rounds} vòng đấu)...")

    # 2. Khởi tạo và chạy Vòng Thụy Sĩ
    tournament = SwissTournamentManager(bots=formatted_bots, total_rounds=total_rounds)
    tournament.run_tournament()

    # 3. Xuất kết quả xếp hạng sau Vòng Thụy Sĩ (Xử lý an toàn phương thức get_standings)
    if hasattr(tournament, "get_standings") and callable(getattr(tournament, "get_standings")):
        standings = tournament.get_standings()
    else:
        standings = getattr(tournament, "standings", getattr(tournament, "bots", formatted_bots))

    output_standings = "configs/swiss_final_standings.json"
    with open(output_standings, "w", encoding="utf-8") as f:
        json.dump(standings, f, indent=2, ensure_ascii=False)

    print(f"=== TẤT CẢ VÒNG ĐẤU HOÀN TẤT! Kết quả đã lưu tại {output_standings} ===")