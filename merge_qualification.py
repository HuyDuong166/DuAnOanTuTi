import json
import os

def merge_results():
    merged_qualified_bots = []
    for laptop_id in range(1, 5):
        file_name = f"qualification_result_laptop_{laptop_id}.json"
        if os.path.exists(file_name):
            with open(file_name, "r") as f:
                bots = json.load(f)
                merged_qualified_bots.extend(bots)
                print(f"Da gop {len(bots)} bot tu {file_name}")
        else:
            print(f"CANH BAO: Thieu file {file_name}")
            
    print(f"Tong so bot vao Vong Swiss: {len(merged_qualified_bots)}")
    
    # Luu danh sach 128 bot sang file dau vao cho Vong Swiss
    with open("configs/swiss_qualified_bots.json", "w") as f:
        json.dump(merged_qualified_bots, f, indent=2)

if __name__ == "__main__":
    merge_results()