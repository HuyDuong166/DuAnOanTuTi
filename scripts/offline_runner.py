import io
import os
import shutil
import zipfile
import requests

RENDER_URL = "https://duanoantuti.onrender.com"
GROUP_NAME = "A"
TOURNAMENT_ID = 9  # ID GIẢI ĐẤU CỦA BẠN TRÊN WEB

ADMIN_USERNAME = "ad2"
ADMIN_PASSWORD = "ad2"


def get_admin_token():
    print("[0/3] Đang tự động đăng nhập lấy Token...")
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
        print("-> Đăng nhập thành công! Token mới đã được cập nhật.")
        return token
    else:
        print(f"-> Lỗi đăng nhập ({res.status_code}): {res.text}")
        return None


def run_offline_pipeline():
    print(f"=== BẮT ĐẦU CHẠY THỬ GIẢI ĐẤU BẢNG {GROUP_NAME} (ID: {TOURNAMENT_ID}) ===")

    token = get_admin_token()
    if not token:
        print("Dừng tiến trình do không thể xác thực tài khoản Admin.")
        return

    headers = {"Authorization": f"Bearer {token}"}

    print("\n[1/3] Đang tải mã nguồn Bot từ Render Server...")
    response = requests.get(
        f"{RENDER_URL}/api/admin/export-bots?tournament_id={TOURNAMENT_ID}&group={GROUP_NAME}", 
        headers=headers
    )

    if response.status_code != 200:
        print("Lỗi khi tải file bot:", response.text)
        return

    extract_dir = f"./bots/submissions_group_{GROUP_NAME}"
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    os.makedirs(extract_dir, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
        zip_ref.extractall(extract_dir)
    print(f"-> Đã tải và giải nén thành công toàn bộ mã nguồn vào: {extract_dir}")

    print("\n[2/3] Đang tiến hành ghép cặp thi đấu ở Local...")
    bot_files = []
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.endswith(".py"):
                bot_files.append(file)

    print(f"-> Tìm thấy {len(bot_files)} tệp Bot: {bot_files}")

    parsed_bots = []
    for rank, file_name in enumerate(bot_files, start=1):
        try:
            bot_id = int(file_name.split("_")[1])
        except Exception:
            bot_id = rank
        parsed_bots.append({"bot_id": bot_id, "file_name": file_name})

    standings = []
    match_logs = []

    # Giả lập Cây thi đấu Knockout 4 người chuẩn
    if len(parsed_bots) >= 4:
        b1, b2, b3, b4 = parsed_bots[0]["bot_id"], parsed_bots[1]["bot_id"], parsed_bots[2]["bot_id"], parsed_bots[3]["bot_id"]
        
        # Round 1: Bán kết
        match_logs.append({
            "match_id": 1, "round": 1, "bot1_id": b1, "bot2_id": b2, "winner_id": b1,
            "log": f"Bán kết 1: Bot {b1} thắng Bot {b2}"
        })
        match_logs.append({
            "match_id": 2, "round": 1, "bot1_id": b3, "bot2_id": b4, "winner_id": b3,
            "log": f"Bán kết 2: Bot {b3} thắng Bot {b4}"
        })
        # Round 2: Chung kết
        match_logs.append({
            "match_id": 3, "round": 2, "bot1_id": b1, "bot2_id": b3, "winner_id": b1,
            "log": f"Chung kết: Bot {b1} thắng Bot {b3} và Vô địch!"
        })

        standings = [
            {"rank": 1, "bot_id": b1, "score": 10},
            {"rank": 2, "bot_id": b3, "score": 7},
            {"rank": 3, "bot_id": b2, "score": 4},
            {"rank": 4, "bot_id": b4, "score": 1},
        ]
    else:
        for rank, b in enumerate(parsed_bots, start=1):
            standings.append({"rank": rank, "bot_id": b["bot_id"], "score": (len(parsed_bots) - rank + 1) * 3})

    print(f"-> Kết quả BXH dự kiến: {standings}")

    print("\n[3/3] Đang đẩy kết quả Giải đấu lên Render Server...")
    payload = {
        "tournament_id": TOURNAMENT_ID,
        "standings": standings,
        "match_logs": match_logs,
    }
    resp = requests.post(
        f"{RENDER_URL}/api/admin/import-results", json=payload, headers=headers
    )
    print("-> Phản hồi từ Render Server:", resp.json())


if __name__ == "__main__":
    run_offline_pipeline()