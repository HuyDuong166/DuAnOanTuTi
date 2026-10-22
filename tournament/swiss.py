from typing import List, Dict, Tuple, Set

class SwissSystem:
    def __init__(self, player_ids: List[int]):
        self.player_ids = player_ids
        self.scores: Dict[int, float] = {p_id: 0.0 for p_id in player_ids}
        self.match_history: Set[Tuple[int, int]] = set()

    def record_match_result(self, p1_id: int, p2_id: int, winner_id: int = None, is_draw: bool = False):
        """Cập nhật điểm số và ghi nhận cặp đấu đã từng gặp nhau"""
        pair = (min(p1_id, p2_id), max(p1_id, p2_id))
        self.match_history.add(pair)

        if is_draw:
            self.scores[p1_id] += 1.0
            self.scores[p2_id] += 1.0
        elif winner_id == p1_id:
            self.scores[p1_id] += 3.0
        elif winner_id == p2_id:
            self.scores[p2_id] += 3.0

    def generate_pairings(self) -> List[Tuple[int, int]]:
        """
        Ghép cặp thi đấu cho vòng tiếp theo:
        - Sắp xếp người chơi theo điểm giảm dần.
        - Ưu tiên ghép 2 người chưa từng gặp nhau trong quá khứ.
        """
        sorted_players = sorted(self.player_ids, key=lambda pid: self.scores[pid], reverse=True)
        unpaired = sorted_players.copy()
        pairings: List[Tuple[int, int]] = []

        while len(unpaired) >= 2:
            p1 = unpaired.pop(0)
            matched_idx = None

            for idx, p2 in enumerate(unpaired):
                pair = (min(p1, p2), max(p1, p2))
                if pair not in self.match_history:
                    matched_idx = idx
                    break

            if matched_idx is None:
                matched_idx = 0

            p2 = unpaired.pop(matched_idx)
            pairings.append((p1, p2))

        return pairings