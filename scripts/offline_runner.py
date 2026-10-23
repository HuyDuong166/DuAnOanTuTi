import io
import os
import sys
import json
import shutil
import zipfile
import requests

# 1. Tự động thêm thư mục gốc vào sys.path để gọi các module tournament trong dự án
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tournament.qualification import QualificationStage
from tournament.swiss_manager import SwissTournamentManager

RENDER_URL = "https://duanoantuti.onrender.com"
GROUP_NAME = "A"
TOURNAMENT_ID = 3  # Thay bằng ID Giải đấu thực tế bạn tạo trên Web

ADMIN_USERNAME = "ad2"
ADMIN_PASSWORD = "ad2"


def get_admin_token():
    print("[0/4] Đang tự động đăng nhập lấy Token Admin...")
    login_url = f"{RENDER_URL}/api/auth/login"

    res = requests.post(
        login_url, json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )
    if res.status_code == 422:
        res = requests.post(
            login_url, json={"email": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
        )
    if res.status_code == 422:
        res = requests.post(
            login_url, data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
        )

    if res.status_code == 200:
        data = res.json()
        token = data.get("access_token") or data.get("token") or data.get("jwt")
        print("-> Đăng nhập thành công! Token đã được khởi tạo.")
        return token
    else:
        print(f"-> Lỗi đăng nhập ({res.status_code}): {res.text}")
        return None


def simulate_laptop_worker(laptop_id, all_bots, total_laptops=4, total_groups=16):
    """ MÔ PHỎNG 1 TRONG 4 MÁY CHẠY SƠ LOẠI """
    print(f"   [Máy {laptop_id}/{total_laptops}] Đang xử lý các bảng đấu được phân công...")
    
    qual_stage = QualificationStage(total_groups=total_groups)
    qual_stage.partition_teams(all_bots)

    groups_per_laptop = total_groups // total_laptops
    start_idx = (laptop_id - 1) * groups_per_laptop + 1
    end_idx = start_idx + groups_per_laptop if laptop_id < total_laptops else total_groups + 1
    
    assigned_group_ids = [f"group_{i:02d}" for i in range(start_idx, end_idx)]
    
    qualified_bots = []
    match_logs = []

    for gid in assigned_group_ids:
        if gid in qual_stage.groups:
            group = qual_stage.groups[gid]
            if group.teams:
                # Đội đứng đầu bảng đi tiếp
                winner = group.teams[0]
                qualified_bots.append(winner)
                
                # Ghi log trận đấu sơ loại
                match_logs.append({
                    "match_id": len(match_logs) + 1,
                    "round": 1,
                    "worker_id": laptop_id,
                    "group": gid,
                    "winner_id": winner.get("bot_id") or winner.get("id", 1),
                    "log": f"Máy {laptop_id} - Bảng {gid}: Bot {winner.get('name', winner.get('bot_id'))} xuất sắc giành vị trí nhất bảng!"
                })

    return qualified_bots, match_logs


def run_offline_pipeline():
    print(f"=== BẮT ĐẦU CHẠY GIẢI ĐẤU HỖN HỢP 160 BOT (ID: {TOURNAMENT_ID}) ===")

    # BƯỚC 1: ĐĂNG NHẬP
    token = get_admin_token()
    if not token:
        print("Dừng tiến trình do không thể xác thực tài khoản Admin.")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # BƯỚC 2: TẢI BOT TỪ RENDER (HOẶC ĐỌC DỮ LIỆU LOCAL NẾU CHƯA CÓ TRÊN RENDER)
    print("\n[1/4] Đang tải danh sách/mã nguồn Bot...")
    extract_dir = f"./bots/submissions_group_{GROUP_NAME}"
    
    response = requests.get(
        f"{RENDER_URL}/api/admin/export-bots?tournament_id={TOURNAMENT_ID}&group={GROUP_NAME}", 
        headers=headers
    )

    all_bots = []
    if response.status_code == 200:
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        os.makedirs(extract_dir, exist_ok=True)

        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
            zip_ref.extractall(extract_dir)
        print(f"-> Đã tải và giải nén Bot từ Render Server vào: {extract_dir}")
        
        # Đọc danh sách bot từ các file giải nén
        for root, dirs, files in os.walk(extract_dir):
            for rank, file in enumerate(files, start=1):
                if file.endswith(".py"):
                    try:
                        b_id = int(file.split("_")[1])
                    except Exception:
                        b_id = rank
                    all_bots.append({"bot_id": b_id, "name": f"Bot_{b_id}", "script_path": os.path.join(root, file)})
    
    # Fallback: Nếu trên server chưa có 160 bot, nạp file bot giả lập local
    if len(all_bots) < 160:
        local_bots_file = "bots/all_submitted_bots.json"
        if os.path.exists(local_bots_file):
            print(f"-> Tải 160 bot mẫu từ file local: {local_bots_file}")
            with open(local_bots_file, "r", encoding="utf-8") as f:
                all_bots = json.load(f)
        else:
            print(f"-> Đang tự động tạo đủ 160 bot giả lập...")
            all_bots = [{"bot_id": i, "name": f"Bot_SinhVien_{i}"} for i in range(1, 161)]

    print(f"-> Tổng số lượng Bot tham gia giải đấu: {len(all_bots)}")

    # BƯỚC 3: MÔ PHỎNG SƠ LOẠI TRÊN 4 MÁY GIẢ LẬP (4 WORKERS)
    print("\n[2/4] Đang mô phỏng chạy Sơ loại trên 4 Máy (Worker) song song...")
    all_qualified_bots = []
    all_match_logs = []

    for laptop_id in range(1, 5):
        q_bots, m_logs = simulate_laptop_worker(laptop_id, all_bots, total_laptops=4, total_groups=16)
        all_qualified_bots.extend(q_bots)
        all_match_logs.extend(m_logs)

    print(f"-> Đã hoàn thành Sơ loại 4 Máy! Có {len(all_qualified_bots)} Bot vào Vòng chính (Swiss Stage).")

    # BƯỚC 4: CHẠY VÒNG THỤY SĨ (SWISS STAGE) & LẬP BẢNG XẾP HẠNG
    print("\n[3/4] Bắt đầu thi đấu Vòng Thụy Sĩ cho các Bot lọt qua Vòng loại...")
    
    # Đổi key 'bot_id' thành 'id' nếu cần cho SwissTournamentManager
    formatted_swiss_bots = []
    for b in all_qualified_bots:
        formatted_swiss_bots.append({
            "id": b.get("bot_id") or b.get("id"),
            "name": b.get("name", f"Bot_{b.get('bot_id')}"),
            "path": b.get("script_path", "")
        })

    swiss_mgr = SwissTournamentManager(bots=formatted_swiss_bots, total_rounds=5)
    swiss_mgr.run_tournament()

    # Lấy dữ liệu Bảng xếp hạng linh hoạt
    if hasattr(swiss_mgr, "get_standings") and callable(getattr(swiss_mgr, "get_standings")):
        swiss_standings = swiss_mgr.get_standings()
    elif hasattr(swiss_mgr, "standings"):
        swiss_standings = swiss_mgr.standings
    elif hasattr(swiss_mgr, "bots"):
        swiss_standings = swiss_mgr.bots
    elif hasattr(swiss_mgr, "players"):
        swiss_standings = swiss_mgr.players
    else:
        swiss_standings = formatted_swiss_bots

    # Tổng hợp danh sách Bảng xếp hạng gửi lên Server (Xử lý an toàn cho cả Int, Dict và Object)
    final_standings = []
    for rank, bot_stat in enumerate(swiss_standings, start=1):
        if isinstance(bot_stat, int):
            b_id = bot_stat
            score = (len(swiss_standings) - rank + 1) * 3
            wins = max(0, len(swiss_standings) - rank)
            losses = rank - 1
        elif isinstance(bot_stat, dict):
            b_id = bot_stat.get("id") or bot_stat.get("bot_id") or rank
            score = bot_stat.get("score", (len(swiss_standings) - rank + 1) * 3)
            wins = bot_stat.get("wins", 0)
            losses = bot_stat.get("losses", 0)
        else:
            b_id = getattr(bot_stat, "id", getattr(bot_stat, "bot_id", rank))
            score = getattr(bot_stat, "score", (len(swiss_standings) - rank + 1) * 3)
            wins = getattr(bot_stat, "wins", 0)
            losses = getattr(bot_stat, "losses", 0)

        final_standings.append({
            "rank": rank,
            "bot_id": int(b_id),
            "score": float(score),
            "wins": int(wins),
            "losses": int(losses)
        })

    print(f"-> TOP 3 CHUNG CUỘC: {final_standings[:3]}")

    # BƯỚC 5: ĐẨY KẾT QUẢ LÊN RENDER SERVER VÀ LƯU DATABASE NEON
    print("\n[4/4] Đang đồng bộ và đẩy toàn bộ kết quả lên Render Server (Neon DB)...")
    payload = {
        "tournament_id": TOURNAMENT_ID,
        "standings": final_standings,
        "match_logs": all_match_logs,
    }

    try:
        resp = requests.post(
            f"{RENDER_URL}/api/admin/import-results", json=payload, headers=headers
        )
        if resp.status_code in [200, 201]:
            print("-> THÀNH CÔNG! Kết quả giải đấu đã được cập nhật lên Web và Neon DB.")
            print("-> Phản hồi từ Render:", resp.json())
        else:
            print(f"-> Lỗi khi gửi kết quả ({resp.status_code}): {resp.text}")
    except Exception as e:
        print(f"-> Lỗi kết nối đến Render Server: {e}")


if __name__ == "__main__":
    run_offline_pipeline()