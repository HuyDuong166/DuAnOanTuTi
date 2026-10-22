from typing import List, Tuple, Any

def generate_knockout_bracket(seeded_teams: list) -> list:
    """
    Tạo bracket cho vòng Knockout linh hoạt cho N đội.
    Ghép cặp hạt giống: Seed 1 vs Seed N, Seed 2 vs Seed N-1,...
    """
    n = len(seeded_teams)
    if n < 2:
        raise ValueError("Vòng loại trực tiếp yêu cầu tối thiểu 2 đội.")
    
    # Nếu số đội lẻ, bổ sung None (BYE) vào cuối để đủ cặp
    teams = list(seeded_teams)
    if n % 2 != 0:
        teams.append(None)
        n += 1

    matches = []
    half = n // 2
    for i in range(half):
        match = (teams[i], teams[n - 1 - i])
        matches.append(match)
        
    return matches

class KnockoutStage:
    """Quản lý các vòng đấu loại trực tiếp"""
    
    @staticmethod
    def pair_next_round(winners: list) -> list:
        """Ghép cặp cho vòng kế tiếp từ danh sách các đội thắng"""
        matches = []
        n = len(winners)
        for i in range(0, n, 2):
            if i + 1 < n:
                matches.append((winners[i], winners[i+1]))
            else:
                matches.append((winners[i], None))  # Hạt giống lẻ được BYE
        return matches

    @staticmethod
    def get_match_format(stage: str) -> str:
        formats = {
            "round_of_32": "BO3",
            "round_of_16": "BO3",
            "quarterfinal": "BO5",
            "semifinal": "BO5",
            "final": "BO7"
        }
        return formats.get(stage, "BO3")
