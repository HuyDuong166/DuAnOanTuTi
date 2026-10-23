import json

bots = []
example_bots = [
    "bots/examples/random_bot.py",
    "bots/examples/greedy_bot.py",
    "bots/examples/aggressive_bot.py",
    "bots/examples/tactical_bot.py"
]

for i in range(1, 161):
    bots.append({
        "bot_id": i,
        "name": f"Bot_SinhVien_{i}",
        "script_path": example_bots[i % len(example_bots)]
    })

with open("bots/all_submitted_bots.json", "w") as f:
    json.dump(bots, f, indent=2)

print("Đã tạo xong 160 bot giả lập!")