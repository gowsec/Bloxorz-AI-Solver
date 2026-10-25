"""Translate pygame input into Bloxorz actions."""
import pygame
from src.core.constants import Direction
from src.core.move import Action

KEY_ACTIONS = {pygame.K_UP: Direction.UP, pygame.K_DOWN: Direction.DOWN,
               pygame.K_LEFT: Direction.LEFT, pygame.K_RIGHT: Direction.RIGHT}

def action_for_key(key: int) -> Action | None:
    direction = KEY_ACTIONS.get(key)
    return Action(direction) if direction is not None else None
