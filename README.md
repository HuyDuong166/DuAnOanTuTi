# UET Algorithm Battle Platform ⚔️🤖

**UET Algorithm Battle Platform** (Dự án BT03) là hệ thống chấm điểm và tự động tổ chức giải đấu đối kháng dành cho các thuật toán AI/Bot. Hệ thống cho phép sinh viên/lập trình viên lập trình Bot, nộp mã nguồn, thi đấu đối kháng trực tiếp trong môi trường cách ly an toàn (Docker Sandbox), theo dõi trực tiếp kết quả và xem lại diễn biến trận đấu qua giao diện Web trực quan.

🌐 **Demo trực tuyến (Live App)**: <https://duanoantuti.onrender.com>

---

## 📜 1. Luật chơi Chi tiết (Game Rules & Mechanics)

### 1.1. Bàn cờ & Quân cờ
* **Bàn cờ**: Bàn cờ dạng ma trận $M \times M$ (mặc định $9 \times 9$).
* **Quản lý quân cờ (`piece.py`)**:
  * Mỗi quân cờ thuộc về một người chơi cụ thể (Player 1 hoặc Player 2) và mang thuộc tính loại quân (Kéo, Búa, Bao hoặc các loại quân chiến thuật).
  * Quy tắc tương tác quân cờ dựa trên mối quan hệ khắc chế:
    $$\text{Búa} \succ \text{Kéo} \succ \text{Bao} \succ \text{Búa}$$
  * Khi quân cờ di chuyển vào ô có quân đối phương:
    * Nếu quân của bạn khắc quân đối phương $\rightarrow$ Quân đối phương bị tiêu diệt và quân bạn chiếm giữ ô đó.
    * Nếu quân bạn bị đối phương khắc $\rightarrow$ Quân bạn bị tiêu diệt.
    * Nếu cùng loại quân $\rightarrow$ Xảy ra hòa tại ô (cả hai quân bị loại bỏ hoặc theo quy định của bộ luật `rule_set.py`).

### 1.2. Nước đi hợp lệ (`move.py`)
* Mỗi lượt, một người chơi được thực hiện duy nhất **1 nước đi hợp lệ**.
* Nước đi hợp lệ gồm vị trí xuất phát $(x_1, y_1)$ và vị trí đích $(x_2, y_2)$ thỏa mãn:
  1. Có quân cờ của người chơi ở ô xuất phát $(x_1, y_1)$.
  2. Vị trí đích nằm trong khoảng giới hạn bàn cờ.
  3. Quãng đường di chuyển tuân thủ khoảng cách cho phép (thường là 1 ô lân cận theo chiều ngang, dọc hoặc chéo).
  4. Không di chuyển vào ô đang chứa quân đồng minh.

### 1.3. Điều kiện Thắng / Thua / Hòa (`game_result.py`)
Một trận đấu kết thúc và phân định kết quả trong các trường hợp:
1. **Thắng tuyệt đối (Checkmate / Total Elimination)**: Một người chơi tiêu diệt toàn bộ quân cờ của đối phương hoặc ăn được quân Chỉ huy (King/Leader) của đối thủ.
2. **Hết số lượt tối đa (Max Turns Reached)**: Nếu trận đấu vượt quá số lượt quy định (vd: 100 lượt) mà chưa phân thắng bại, điểm số sẽ tính dựa trên:
   * Tổng số quân còn lại trên bàn cờ.
   * Tổng điểm giá trị quân cờ còn sống.
3. **Thắng do Đối thủ Vi phạm (Disqualification)**: Đối thủ bị xử thua ngay lập tức nếu vi phạm một trong các lỗi kỹ thuật (xem mục 1.4).

### 1.4. Xử phạt & Lỗi kỹ thuật (Penalties & Disqualifications)
* **Timeout (Quá thời gian)**: Mỗi nước đi có giới hạn thời gian phản hồi $t_{\text{step}} \le 1.0\text{s}$ và tổng thời gian quỹ $T_{\text{total}} \le 30.0\text{s}$. Nếu Bot vượt quá giới hạn này, hệ thống chấm thua (Forfeit) ngay lập tức.
* **Invalid Move (Nước đi không hợp lệ)**: Trả về tọa độ ngoài bàn cờ, di chuyển quân của đối thủ hoặc nước đi bị cấm bởi `rule_set.py`.
* **Runtime Error / Crash**: Bot bị ngoại lệ (Exception), tràn bộ nhớ hoặc dừng đột ngột trong quá trình tính toán.

---

## 🤖 2. Hướng dẫn Viết Bot (Bot Development Guide)

### 2.1. Nguyên lý Hoạt động của Bot
Bot tương tác với hệ thống thông qua giao diện Standard Input/Output (STDIN/STDOUT) hoặc qua bộ Wrapper SDK `bots/api/base_bot.py`. Hệ thống sẽ truyền trạng thái bàn cờ hiện tại `GameState`, Bot xử lý và xuất ra nước đi `Move` tương ứng.

### 2.2. Cấu trúc Dữ liệu Cốt lõi

#### A. Trạng thái Trận đấu (`GameState`)
```python
class GameState:
    board: Board                # Ma trận bàn cờ hiện tại
    current_player: int         # ID người chơi đến lượt (1 hoặc 2)
    turn_count: int             # Số thứ tự lượt hiện tại
    history: List[Move]         # Lịch sử các nước đi trước đó
    
    def get_valid_moves(self, player_id: int) -> List[Move]:
        """Trả về danh sách tất cả các nước đi hợp lệ của player_id"""
        pass
```

#### B. Nước đi (`Move`)
```python
class Move:
    from_pos: Tuple[int, int]   # Tọa độ xuất phát (row, col)
    to_pos: Tuple[int, int]     # Tọa độ đích (row, col)
```

### 2.3. Mã Nguồn Mẫu Viết Bot (Bot SDK Example)

Dưới đây là ví dụ triển khai một Bot chiến thuật hoàn chỉnh sử dụng lớp `BaseBot`:

```python
import sys
import random
from typing import List, Optional
from bots.api.base_bot import BaseBot
from game.move import Move
from game.game_state import GameState

class TacticalSmartBot(BaseBot):
    def __init__(self):
        super().__init__(name="TacticalSmartBot")

    def make_move(self, game_state: GameState) -> Optional[Move]:
        """
        Hàm chính được hệ thống gọi ở mỗi lượt chơi.
        """
        # 1. Lấy danh sách nước đi hợp lệ
        valid_moves: List[Move] = game_state.get_valid_moves(self.player_id)
        
        if not valid_moves:
            return None

        # 2. Đánh giá và chọn nước đi tối ưu nhất
        best_move = None
        best_score = -float('inf')

        for move in valid_moves:
            score = self.evaluate_move(move, game_state)
            if score > best_score:
                best_score = score
                best_move = move

        # 3. Trả về nước đi được chọn
        return best_move if best_move else random.choice(valid_moves)

    def evaluate_move(self, move: Move, game_state: GameState) -> float:
        """
        Hàm đánh giá điểm số cho một nước đi cụ thể.
        """
        score = 0.0
        target_piece = game_state.board.get_piece(move.to_pos)
        my_piece = game_state.board.get_piece(move.from_pos)

        # Ưu tiên 1: Ăn quân đối phương
        if target_piece is not None and target_piece.player_id != self.player_id:
            # Nếu quân mình khắc quân địch -> Điểm cộng lớn
            if my_piece.beats(target_piece):
                score += 50.0
            # Nếu bằng cờ -> Điểm cộng vừa
            elif my_piece.type == target_piece.type:
                score += 10.0
            else:
                score -= 30.0 # Bị ăn ngược

        # Ưu tiên 2: Di chuyển về phía trung tâm bàn cờ
        center_row, center_col = 3.5, 3.5
        dist_to_center = abs(move.to_pos[0] - center_row) + abs(move.to_pos[1] - center_col)
        score += (8 - dist_to_center) * 2.0

        return score

if __name__ == "__main__":
    # Khởi chạy Bot
    bot = TacticalSmartBot()
    bot.run()
```

### 2.4. Quy tắc & Lời khuyên cho Lập trình viên
1. **Không sử dụng thư viện cấm**: Tránh dùng các thư viện can thiệp hệ thống (`os.system`, `subprocess`, `socket`) gây lỗi bảo mật trong Sandbox.
2. **Tối ưu hóa thuật toán**: Đảm bảo thời gian tính toán của thuật toán (Minimax, Alpha-Beta Pruning, Heuristic) $\le 0.5\text{s}$ cho mỗi nước đi để tránh phạt Timeout.
3. **Xử lý Ngoại lệ (Exception Handling)**: Bọc logic chính trong khối `try-except` để Bot không bị crash bất ngờ.

---

## 🏆 3. Chi tiết các Thể thức Thi đấu (Tournament Formats)

Hệ thống cung cấp linh hoạt nhiều thể thức giải đấu tự động (`tournament/`):

```
                        ┌──────────────────────────────┐
                        │  Vòng Sơ Loại (Qualification) │
                        └──────────────┬───────────────┘
                                       │ (Top Bots)
                                       ▼
                        ┌──────────────────────────────┐
                        │  Vòng Hệ Thụy Sĩ (Swiss) /   │
                        │  Vòng Tròn (Round-Robin)     │
                        └──────────────┬───────────────┘
                                       │ (Top 16 / Top 8)
                                       ▼
                        ┌──────────────────────────────┐
                        │ Vòng Loại Trực Tiếp Knockout │
                        │ (Top 16 -> Tứ kết -> Chung kết)│
                        └──────────────────────────────┘
```

### 3.1. Vòng Sơ loại (Qualification Stage)
* **Mục đích**: Kiểm tra tính ổn định của Bot, lọc bỏ các Bot bị lỗi cú pháp, crash liên tục hoặc ngắt kết nối.
* **Thể thức**: Mỗi Bot đấu kiểm thử từ 2 - 3 trận với các Bot mẫu (`random_bot`, `greedy_bot`). Bot vượt qua số điểm tối thiểu sẽ bước vào giải đấu chính thức.

### 3.2. Vòng thi đấu Hệ Thụy Sĩ (Swiss System Stage - `swiss.py`)
* **Đặc điểm**: Số lượng vòng đấu cố định (thường từ 5 đến 7 vòng) mà không loại Bot nào sớm.
* **Quy tắc xếp cặp**:
  * Ở vòng 1, ghép cặp ngẫu nhiên hoặc theo hạt giống.
  * Từ vòng 2 trở đi, các Bot có cùng (hoặc xấp xỉ) điểm số tổng sẽ được xếp cặp thi đấu với nhau.
  * Hai Bot **không bao giờ gặp nhau quá 1 lần** trong suốt giai đoạn Swiss.
* **Ưu điểm**: Phản ánh chính xác thực lực của từng Bot mà không phụ thuộc vào may mắn bốc thăm.

### 3.3. Vòng Tròn Tính Điểm (Round-Robin Stage - `round_robin.py`)
* **Quy tắc**: Mỗi Bot thi đấu với tất cả các Bot còn lại trong bảng đấu (1 hoặc 2 lượt đấu đi/về).
* **Cách tính điểm**:
  * **Thắng**: $+3$ điểm.
  * **Hòa**: $+1$ điểm.
  * **Thua**: $0$ điểm.

### 3.4. Vòng Loại Trực Tiếp (Knockout Stage - `knockout.py`)
* **Áp dụng**: Dành cho Top 16, Top 8 hoặc Top 4 xuất sắc nhất từ vòng Swiss/Vòng bảng.
* **Cấu trúc**: Sơ đồ nhánh thi đấu (Bracket) theo tiêu chuẩn:
  * **Vòng 1/16** $\rightarrow$ **Tứ kết (Quarterfinal)** $\rightarrow$ **Bán kết (Semifinal)** $\rightarrow$ **Chung kết (Final)**.
* **Phân hạt giống (Seeding)**: Bot đứng đầu vòng Swiss/Vòng bảng sẽ gặp Bot đứng thứ hạng thấp nhất (vd: Hạt giống #1 gặp Hạt giống #16).

### 3.5. Tiêu chí Phân định Thứ hạng & Tie-breakers
Khi hai hoặc nhiều Bot có cùng tổng số điểm, thứ hạng được ưu tiên phân định theo thứ tự:
1. **Chỉ số Buchholz / Sonneborn-Berger**: Tổng điểm của tất cả các đối thủ mà Bot đó đã thi đấu cùng.
2. **Trận đối đầu trực tiếp (Head-to-Head)**: Kết quả trận đấu giữa 2 Bot bằng điểm.
3. **Hiệu số thắng/thua (Win/Loss Ratio)**.
4. **Tổng thời gian tính toán**: Bot nào có tổng thời gian suy nghĩ ít hơn sẽ xếp trên.

---

## ⚙️ 4. Kiến trúc & Hệ thống Thi đấu (System Architecture)

### 4.1. Sơ đồ Tổng quan Môi trường Vận hành

```
 [Frontend Web] <---> [FastAPI Backend] <---> [SQLite Database]
                             │
                             ▼
                    [Tournament Manager]
                             │
                             ▼
                    [Match Scheduler]
                             │
                             ▼
                    [Match Worker Process]
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   [Docker Sandbox - Bot 1]  <--->  [Docker Sandbox - Bot 2]
            │                                 │
            └───────────────┬─────────────────┘
                            ▼
                    [Match Runner / Judge]
                            │
                            ▼
                    [Match Logs (JSON)]
```

### 4.2. Các Thành phần Hệ thống chính

1. **Game Engine (`game/`)**: Lõi tính toán trạng thái, kiểm tra nước đi hợp lệ, thực thi thay đổi bàn cờ và xác định thắng/thua.
2. **Docker Sandbox Judge (`judge/`)**:
   * Chạy từng Bot trong một Docker Container riêng biệt.
   * Giới hạn tài nguyên nghiêm ngặt: CPU (chỉ định 1 core), RAM (tối đa 256MB), tắt kết nối mạng ngoài (`--net none`).
3. **Tournament Manager (`tournament/`)**: Tự động hóa quá trình chia bảng, tính điểm, lập lịch và tiến hành các vòng đấu theo cấu hình JSON (`configs/`).
4. **RESTful API Backend (`backend/`)**: FastAPI phục vụ việc đăng ký người dùng, nộp bài, xem danh sách giải đấu và gọi Worker execution.
5. **Match Worker (`scripts/run_laptop_worker.py`)**: Tiến trình nền liên tục lấy các trận đấu chưa đấu trong hàng chờ, gọi `MatchRunner` để thi đấu và ghi lại kết quả.
6. **Replay Visualizer (`frontend/replay.js`)**: Đọc file nhật ký trận đấu (JSON log) và tái hiện lại từng nước đi dưới dạng hoạt họa (Animation) trực quan trên trình duyệt.

---

## 🛠️ Công nghệ sử dụng

* **Backend**: Python 3.9+, FastAPI, SQLAlchemy, Pydantic, Uvicorn, Pytest.
* **Database**: SQLite (`uet_algorithm_battle.db`).
* **Sandbox/Judge**: Docker Containerization, Subprocess.
* **Frontend**: HTML5, CSS3, JavaScript (ES6+), Replay Visualizer JS.
* **Deployment**: Render Cloud Platform (<https://duanoantuti.onrender.com>).

---

## 📁 Cấu trúc Thư mục Dự án

```
BT03-main/
├── backend/                  # RESTful API Backend (FastAPI)
│   ├── database/             # Schema CSDL & Cấu hình DB
│   ├── models/               # SQLAlchemy ORM Models
│   ├── routers/              # API Endpoints (Auth, Bots, Rooms, Tournaments...)
│   ├── schemas/              # Pydantic Schemas cho Validation
│   ├── services/             # Logic nghiệp vụ Backend
│   └── main.py               # Entrypoint khởi chạy FastAPI App
├── game/                     # Logic Động cơ Trò chơi (Game Engine)
│   ├── board.py              # Bàn cờ
│   ├── piece.py              # Quân cờ
│   ├── move.py               # Nước đi
│   ├── game_state.py         # Trạng thái trận đấu
│   ├── game_engine.py        # Luồng thực thi trò chơi
│   └── rule_set.py           # Bộ luật trò chơi
├── judge/                    # Hệ thống Chấm điểm & Docker Sandbox
│   ├── Dockerfile            # Cấu hình Môi trường Sandbox
│   ├── match_runner.py       # Điều khiển trận đấu giữa 2 Bot
│   ├── validator.py          # Thẩm định tính hợp lệ nước đi
│   └── result.py             # Đóng gói kết quả trận đấu
├── tournament/               # Động cơ Quản lý Giải đấu
│   ├── swiss.py / swiss_manager.py # Thể thức Thụy Sĩ
│   ├── knockout.py           # Thể thức Loại trực tiếp
│   ├── round_robin.py        # Thể thức Vòng tròn
│   ├── qualification.py      # Vòng Sơ loại
│   └── match_scheduler.py    # Lập lịch thi đấu
├── bots/                     # Mã nguồn & Lượt nộp bài Bot
│   ├── api/                  # Bot SDK / Standard Interface
│   ├── random_bot/           # Bot đánh ngẫu nhiên
│   ├── greedy_bot/           # Bot tham ăn
│   ├── aggressive_bot/       # Bot tấn công
│   ├── tactical_bot/         # Bot chiến thuật
│   └── user_1...user_6/      # Các bản nộp bài của sinh viên/người dùng
├── configs/                  # Cấu hình các giai đoạn giải đấu (JSON)
│   ├── qualification.json
│   ├── swiss_stage.json
│   ├── top16.json
│   ├── quarterfinal.json
│   ├── semifinal.json
│   └── final.json
├── match_logs/               # Nhật ký ghi lại các trận đấu đã diễn ra (JSON)
├── frontend/                 # Giao diện Web Client
│   ├── index.html            # Trang chủ
│   ├── replay.js             # Bộ xem lại diễn biến trận đấu
│   └── ...                   # Các trang tính năng
├── scripts/                  # Kịch bản vận hành & Đồng bộ CSDL
│   ├── run_laptop_worker.py  # Worker thực thi trận đấu
│   ├── sync_to_db.py         # Đồng bộ dữ liệu tổng quát
│   └── sync_tournament_to_db.py # Đồng bộ giải đấu vào CSDL
├── tests/                    # Bộ kiểm thử tự động (Pytest)
└── uet_algorithm_battle.db   # File CSDL SQLite chính
```

---

## 🚀 Hướng dẫn Cài đặt & Khởi chạy Cục bộ (Local)

### 1. Yêu cầu Tiền đề
* **Python**: Version $\ge 3.9$
* **Docker**: Đã cài đặt và daemon Docker đang chạy (bắt buộc cho môi trường chấm điểm cách ly).

### 2. Cài đặt Môi trường
```bash
# Clone/Giải nén dự án
cd BT03-main

# Tạo môi trường ảo Python
python -m venv venv

# Kích hoạt môi trường ảo
# Trên Linux/macOS:
source venv/bin/activate
# Trên Windows:
# venv\Scripts\activate

# Cài đặt các thư viện phụ thuộc
pip install -r requirements.txt
```

### 3. Build Docker Image cho Sandbox
Để hệ thống chấm điểm thực thi các Bot an toàn:
```bash
docker build -t bot_sandbox:latest ./judge
```

### 4. Khởi chạy Backend Server
```bash
# Chạy FastAPI Server với Uvicorn tại http://localhost:8000
uvicorn backend.main:app --reload
```
* **Tài liệu Swagger API**: Truy cập `http://localhost:8000/docs` sau khi server hoạt động.

### 5. Khởi chạy Frontend Cục bộ
```bash
python -m http.server 8080 --directory frontend
```
Truy cập giao diện Web tại `http://localhost:8080` (hoặc truy cập bản Production tại <https://duanoantuti.onrender.com>).

---

## 🔄 Vận hành Giải đấu & Match Worker

1. **Khởi chạy Match Worker xử lý hàng chờ trận đấu**:
   ```bash
   python scripts/run_laptop_worker.py
   ```
2. **Đồng bộ dữ liệu trận đấu và bảng xếp hạng vào CSDL**:
   ```bash
   python scripts/sync_tournament_to_db.py
   ```

---

## 🧪 Kiểm thử Tự động (Testing)

Dự án sử dụng `pytest` để kiểm thử tự động:
```bash
# Chạy tất cả bài kiểm thử
pytest

# Kiểm thử Động cơ game & Giải đấu
pytest tests/test_game.py
pytest tests/test_tournament.py

# Kiểm thử Judge & Backend APIs
pytest tests/test_judge.py
pytest tests/test_backend.py
```

---

## 📜 Giấy phép & Tác giả

Dự án được xây dựng và phát triển phục vụ môn học / bài tập lớn tại **Trường Đại học Công nghệ - Đại học Quốc gia Hà Nội (UET - VNU)**.