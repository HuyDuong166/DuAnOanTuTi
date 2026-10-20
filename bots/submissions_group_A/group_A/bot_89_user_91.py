import random

class Bot:
    """
    RandomBot: Chọn ngẫu nhiên một nước đi hợp lệ.
    Tận dụng trực tiếp danh sách 'legal_moves' do hệ thống cung cấp sẵn.
    """
    def get_move(self, state_dict: dict) -> dict:
        legal_moves = state_dict.get("legal_moves")
        if legal_moves:
            return random.choice(legal_moves)
        
        raise Exception("No valid moves available")