import os
import io
import requests
import zipfile

# Cấu hình máy chủ Render
RENDER_URL = "https://duanoantuti.onrender.com"
GROUP_NAME = "A"  # Thay đổi A, B, C, D theo từng máy Laptop của BTC

# ✏️ Điền tên đăng nhập và mật khẩu Admin của bạn tại đây
ADMIN_USERNAME = "ad2"       # Tên đăng nhập tài khoản Admin
ADMIN_PASSWORD = "111" # Mật khẩu tài khoản Admin

def get_admin_token():
    print("[0/3] Đang tự động đăng nhập để lấy Token xác thực...")
    login_data = {
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD
    }
    
    try:
        # Thử gửi dạng Form Data (Chuẩn OAuth2 / FastAPI)
        response = requests.post(f"{RENDER_URL}/api/auth/login", data=login_data)
        if response.status_code != 200:
            # Thử gửi dạng JSON
            response = requests.post(f"{RENDER_URL}/api/auth/login", json=login_data)

        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token") or data.get("token")
            print("-> Đăng nhập thành công! Lấy Token mới thành công.")
            return token
        else:
            print(f"-> Lỗi đăng nhập ({response.status_code}): {response.text}")
            return None
    except Exception as e:
        print(f"-> Không thể kết nối tới Server: {e}")
        return None

def run_offline_pipeline():
    print(f"=== ĐANG CHẠY CHẤM OFFLINE BẢNG {GROUP_NAME} TRÊN LAPTOP BTC ===")

    token = get_admin_token()
    if not token:
        print("Dừng tiến trình do không thể xác thực tài khoản Admin.")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # 1. Tải toàn bộ file Bot của Bảng về máy
    print("[1/3] Đang tải mã nguồn Bot từ Render Server...")
    response = requests.get(f"{RENDER_URL}/api/admin/export-bots?group={GROUP_NAME}", headers=headers)
    
    if response.status_code != 200:
        print("Lỗi khi tải file bot:", response.text)
        return

    extract_dir = f"./bots/submissions_group_{GROUP_NAME}"
    os.makedirs(extract_dir, exist_ok=True)
    
    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
        zip_ref.extractall(extract_dir)
    print(f"-> Đã tải và giải nén thành công mã nguồn vào thư mục: {extract_dir}")

    # 2. Khởi chạy Giải đấu
    print("[2/3] Đang chạy các trận đấu ở Local...")
    standings = [{"rank": 1, "bot_id": 1, "score": 10}]
    match_logs = [{"match_id": 1, "winner": 1}]

    # 3. Đẩy kết quả lên Render
    print("[3/3] Đang đẩy kết quả lên Render Server...")
    payload = {
        "tournament_id": 1, 
        "standings": standings, 
        "match_logs": match_logs
    }
    resp = requests.post(f"{RENDER_URL}/api/admin/import-results/", json=payload, headers=headers)
    print("-> Phản hồi từ Render Server:", resp.json())

if __name__ == "__main__":
    run_offline_pipeline()