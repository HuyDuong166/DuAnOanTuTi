import sys
import os

# Thêm thư mục gốc của dự án vào sys.path để Python nhận diện thư mục 'tournament'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
from tournament.qualification import QualificationStage

def run_worker(laptop_id, total_laptops=4):
    print(f"=== LAPTOP {laptop_id}/{total_laptops} STARTING QUALIFICATION ===")
    
    # 1. Đọc cấu hình vòng sơ loại
    config_path = "configs/qualification.json"
    if not os.path.exists(config_path):
        print(f"LỖI: Không tìm thấy file {config_path}")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    total_groups = config.get("num_groups", 16)
    
    # 2. Khởi tạo QualificationStage từ dự án
    qual_stage = QualificationStage(total_groups=total_groups)
    
    # 3. Đọc danh sách bot nộp bài
    bots_path = "bots/all_submitted_bots.json"
    if not os.path.exists(bots_path):
        print(f"LỖI: Không tìm thấy file {bots_path}. Hãy chạy python generate_test_bots.py trước!")
        return

    with open(bots_path, "r", encoding="utf-8") as f:
        all_bots = json.load(f)
        
    # Phân bổ bot vào các bảng đấu
    qual_stage.partition_teams(all_bots)
    
    # 4. Tính toán dải bảng đấu cho laptop này
    groups_per_laptop = total_groups // total_laptops
    start_idx = (laptop_id - 1) * groups_per_laptop + 1
    end_idx = start_idx + groups_per_laptop if laptop_id < total_laptops else total_groups + 1
    
    assigned_group_ids = [f"group_{i:02d}" for i in range(start_idx, end_idx)]
    print(f"Laptop {laptop_id} phụ trách các bảng: {assigned_group_ids}")
    
    # 5. Lấy đại diện đứng đầu từ các bảng được phân công
    qualified_bots = []
    for gid in assigned_group_ids:
        if gid in qual_stage.groups:
            group = qual_stage.groups[gid]
            if group.teams:
                # Lấy đội đứng đầu trong bảng
                qualified_bots.append(group.teams[0])
    
    # 6. Xuất kết quả của laptop ra file JSON
    output_file = f"qualification_result_laptop_{laptop_id}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(qualified_bots, f, indent=2, ensure_ascii=False)
        
    print(f"=== LAPTOP {laptop_id} HOÀN THÀNH! Đã lưu {len(qualified_bots)} bot vào {output_file} ===")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Hướng dẫn sử dụng: python run_laptop_worker.py <laptop_id (1-4)>")
        sys.exit(1)
        
    laptop_id = int(sys.argv[1])
    run_worker(laptop_id)