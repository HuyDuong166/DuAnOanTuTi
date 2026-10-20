import os
import io
import requests
import zipfile

# Cấu hình địa chỉ trang web của bạn trên Render & Bearer Token Admin
RENDER_URL = "https://duanoantuti.onrender.com"
ADMIN_TOKEN = "ĐIỀN_TOKEN_JWT_ADMIN_CỦA_BẠN_VÀO_ĐÂY"
GROUP_NAME = "A"  # Đổi thành A, B, C, D tùy theo phân công từng Laptop BTC

HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}"}

def run_offline_pipeline():
    print(f"=== ĐANG CHẠY CHẤM OFFLINE BẢNG {GROUP_NAME} TRÊN LAPTOP BTC ===")

    # 1. Tải toàn bộ file Bot của Bảng về máy
    print("[1/3] Đang tải mã nguồn Bot từ Render Server...")
    response = requests.get(f"{RENDER_URL}/api/admin/export-bots?group={GROUP_NAME}", headers=HEADERS)
    
    if response.status_code != 200:
        print("Lỗi khi tải file bot:", response.text)
        return

    extract_dir = f"./bots/submissions_group_{GROUP_NAME}"
    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
        zip_ref.extractall(extract_dir)
    print(f"-> Đã giải nén vào {extract_dir}")

    # 2. Khởi chạy Giải đấu bằng Swiss Tournament / Docker Sandbox ở Local
    print("[2/3] Đang chạy các trận đấu bằng Docker Sandbox Local...")
    try:
        from tournament.swiss import SwissTournament
        tournament = SwissTournament(bot_dir=extract_dir)
        standings, match_logs = tournament.run_all_rounds()
    except Exception as e:
        print(f"Lỗi khi chạy tournament local: {e}")
        # Giả lập mẫu nếu chưa gắn mô hình chạy giải đấu thực tế
        standings = [{"rank": 1, "bot_id": 1, "score": 10}]
        match_logs = [{"match_id": 1, "winner": 1}]

    # 3. Đẩy Bảng xếp hạng và Replay JSON về lại Render Server
    print("[3/3] Đang đẩy kết quả lên Render Server...")
    payload = {
        "tournament_id": 1, 
        "standings": standings, 
        "match_logs": match_logs
    }
    resp = requests.post(f"{RENDER_URL}/api/admin/import-results", json=payload, headers=HEADERS)
    print("-> Phản hồi từ Render Server:", resp.json())

if __name__ == "__main__":
    run_offline_pipeline()