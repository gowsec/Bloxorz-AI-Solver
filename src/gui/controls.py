"""Translate pygame input into Bloxorz actions."""
import pygame
from src.core.constants import Direction
from src.core.move import Action

KEY_ACTIONS = {pygame.K_UP: Direction.LEFT, pygame.K_DOWN: Direction.RIGHT,
               pygame.K_LEFT: Direction.DOWN, pygame.K_RIGHT: Direction.UP}

def action_for_key(key: int) -> Action | None:
    direction = KEY_ACTIONS.get(key)
    return Action(direction) if direction is not None else None
