import sys
from app.config.settings import load_config

def main():
    config = load_config()
    print("=== CONFIG DUMP ===")
    print(f"initial_attempts: {config.game.initial_attempts}")
    print(f"max_attempts: {config.game.max_attempts}")
    print("===================")

if __name__ == "__main__":
    main()
