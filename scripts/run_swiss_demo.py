from tournament.swiss_manager import SwissTournamentManager

if __name__ == "__main__":
    sample_bots = [
        {"id": 1, "name": "RandomBot", "path": "bots/examples/random_bot.py"},
        {"id": 2, "name": "GreedyBot", "path": "bots/examples/greedy_bot.py"},
        {"id": 3, "name": "AggressiveBot", "path": "bots/examples/aggressive_bot.py"},
        {"id": 4, "name": "TacticalBot", "path": "bots/examples/tactical_bot.py"}
    ]

    tournament = SwissTournamentManager(bots=sample_bots, total_rounds=3)
    tournament.run_tournament()