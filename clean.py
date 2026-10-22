# clean.py
import os
import shutil

def clean_project():
    print("🧹 Đang dọn dẹp dự án...")

    # 1. Xóa các thư mục __pycache__
    count_cache = 0
    for root, dirs, files in os.walk("."):
        for d in dirs:
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d))
                count_cache += 1
    print(f"✅ Đã xóa {count_cache} thư mục __pycache__")

    # 2. Xóa rác trong match_logs
    if os.path.exists("match_logs"):
        for item in os.listdir("match_logs"):
            item_path = os.path.join("match_logs", item)
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        print("✅ Đã làm sạch thư mục match_logs/")

    # 3. Xóa bot rác trong bots/submitted
    if os.path.exists("bots/submitted"):
        for item in os.listdir("bots/submitted"):
            item_path = os.path.join("bots/submitted", item)
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        print("✅ Đã dọn dẹp bot rác trong bots/submitted/")

    print("🎉 Dự án đã sạch sẽ, sẵn sàng để commit và push lên GitHub!")

if __name__ == "__main__":
    clean_project()