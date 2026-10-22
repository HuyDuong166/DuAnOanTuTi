from typing import List, Dict, Any, Optional
from .qualification import QualificationStage
from .knockout import KnockoutStage, generate_knockout_bracket
from .rule_manager import TournamentRuleManager
from .match_scheduler import MatchScheduler

class Competition:
    """Bộ điều phối toàn diện cho giải đấu UET Algorithm Battle"""
    def __init__(self, name: str = "UET Algorithm Battle 2026"):
        self.name = name
        self.current_phase = "REGISTRATION"
        self.rule_manager = TournamentRuleManager()
        self.scheduler = MatchScheduler()
        self.qualification = QualificationStage(total_groups=10)
        self.playoffs_bracket: Dict[str, Any] = {}
        self.teams: List[Dict[str, Any]] = []
        self.champion: Optional[Dict[str, Any]] = None

    def register_teams(self, teams: List[Dict[str, Any]]):
        self.teams = teams

    def start_qualification(self):
        self.current_phase = "QUALIFICATION"
        self.qualification.partition_teams(self.teams)

    # Tệp: tournament/competition.py

    def start_playoffs(self):
        self.current_phase = "PLAYOFFS"
        advancing_teams = self.qualification.get_top_32_advancing()
        playoff_pairings = generate_knockout_bracket(advancing_teams)
        self.playoffs_bracket["round_1"] = playoff_pairings
        return self.playoffs_bracket

    def get_summary(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "phase": self.current_phase,
            "total_teams": len(self.teams),
            "champion": self.champion
        }
