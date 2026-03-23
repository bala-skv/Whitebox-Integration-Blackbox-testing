"""
Entry point for the MoneyPoly board game application.
This module handles user input for player names and initializes the game loop.
"""
from moneypoly.game import Game


def get_player_names():
    """
    Prompt the user to enter player names via the console.
    
    Returns:
        list: A list of cleaned strings representing player names.
    """
    print("Enter player names separated by commas (minimum 2 players):")
    raw = input("> ").strip()
    names = [n.strip() for n in raw.split(",") if n.strip()]
    return names


def main():
    """
    The main execution function that sets up and runs the MoneyPoly game.
    Handles keyboard interrupts and setup errors gracefully.
    """
    names = get_player_names()
    try:
        game = Game(names)
        game.run()
    except KeyboardInterrupt:
        print("\n\n  Game interrupted. Goodbye!")
    except ValueError as exc:
        print(f"Setup error: {exc}")


if __name__ == "__main__":
    main()
