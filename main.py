"""Run the first milestone: a hand-written Bloxorz board."""

from src.gui.game import Game
from src.gui.sample_level import DEMO_LEVEL


if __name__ == "__main__":
    Game(DEMO_LEVEL).run()
