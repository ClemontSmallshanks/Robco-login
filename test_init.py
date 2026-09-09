import sys
import traceback
from app.game.game_state import GameState, GamePhase

def test_game_state():
    try:
        game = GameState()
        print(f"Initial Phase: {game.phase}")
        print(f"Initial Attempts: {game.attempts_remaining}")
        
        game.advance_to_menu()
        print(f"Menu Phase: {game.phase}")
        
        game.start_game()
        print(f"Playing Phase: {game.phase}")
        print(f"Attempts After Start: {game.attempts_remaining}")
        
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    test_game_state()
