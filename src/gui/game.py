"""Application loop. Movement and search will be added in later milestones."""

import pygame

from src.core.board import Level
from src.gui.renderer import Renderer


class Game:
    def __init__(self, level: Level) -> None:
        self.level = level

    def run(self) -> None:
        pygame.display.init()
        pygame.font.init()
        try:
            screen = pygame.display.set_mode((1000, 760), pygame.RESIZABLE)
            pygame.display.set_caption("Bloxorz AI Solver | Isometric preview")
            clock = pygame.time.Clock()
            renderer = Renderer()
            running = True
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        running = False
                renderer.draw(screen, self.level)
                pygame.display.flip()
                clock.tick(60)
        finally:
            pygame.quit()
