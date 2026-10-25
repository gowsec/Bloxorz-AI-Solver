"""Clickable Restart and New Game controls."""
import pygame

class UI:
    def __init__(self):
        self.font = pygame.font.Font(None, 26)
        self.buttons = {}

    def draw(self, surface):
        self.buttons = {}
        for label, x in (("Restart", 32), ("New Game", 132)):
            rect = pygame.Rect(x, surface.get_height()-76, 88 if label == "Restart" else 112, 30)
            self.buttons[label] = rect
            pygame.draw.rect(surface, (43,58,78), rect, border_radius=5)
            pygame.draw.rect(surface, (110,135,162), rect, 1, border_radius=5)
            text = self.font.render(label, True, (230,237,247))
            surface.blit(text, text.get_rect(center=rect.center))

    def clicked(self, position):
        return next((label for label, rect in self.buttons.items() if rect.collidepoint(position)), None)

    def choose_level(self, screen, levels):
        clock = pygame.time.Clock()
        selected = 0
        title = self.font.render('Select a level (Up/Down, Enter; Esc to return)', True, (230,237,247))
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: return None
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE: return None
                    if event.key in (pygame.K_UP, pygame.K_DOWN):
                        selected = (selected + (1 if event.key == pygame.K_DOWN else -1)) % len(levels)
                    if event.key == pygame.K_RETURN: return levels[selected]
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i in range(len(levels)):
                        if pygame.Rect(50, 85+i*38, screen.get_width()-100, 34).collidepoint(event.pos):
                            return levels[i]
            screen.fill((17,24,39)); screen.blit(title,(36,32))
            for i, level in enumerate(levels):
                color=(70,218,174) if i==selected else (151,168,192)
                screen.blit(self.font.render(level.name,True,color),(60,100+i*38))
            pygame.display.flip(); clock.tick(30)


