"""Clickable game controls, solver controls, and a compact result table."""
import pygame

PANEL = (24, 34, 50)
TEXT = (230, 237, 247)
MUTED = (151, 168, 192)


class UI:
    def __init__(self):
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 21)
        self.buttons: dict[str, pygame.Rect] = {}

    def draw(self, surface, result=None, selected_cube: int = 0, replaying: bool = False):
        self.buttons = {}
        h, w = surface.get_height(), surface.get_width()
        labels = ("Solve BFS", "Solve DFS", "Solve UCS", "Solve A*", "Replay", "Restart", "New Game")
        x = 18
        y = h - 82
        for label in labels:
            width = max(75, self.font.size(label)[0] + 20)
            if x + width > w - 16:
                x = 18
                y += 36
            rect = pygame.Rect(x, y, width, 30)
            self.buttons[label] = rect
            pygame.draw.rect(surface, (43, 58, 78), rect, border_radius=5)
            pygame.draw.rect(surface, (70, 218, 174) if label == "Replay" and replaying else (110, 135, 162), rect, 1, border_radius=5)
            text = self.font.render(label, True, TEXT)
            surface.blit(text, text.get_rect(center=rect.center))
            x += width + 8

        status = "B: Solve BFS   D: Replay   Space: Switch block"
        surface.blit(self.small_font.render(status, True, MUTED), (18, h - 48))
        if result is not None:
            self._draw_stats(surface, result)

    def _draw_stats(self, surface, result):
        rows = [
            ("Algorithm", result.algorithm.upper()),
            ("Status", result.status.replace("_", " ").title()),
            ("Moves", str(result.solution_length)),
            ("Cost", f"{result.total_cost:.2f}" if result.total_cost != float("inf") else "N/A"),
            ("Search time", f"{result.search_time * 1000:.2f} ms"),
            ("Expanded", str(result.expanded_nodes)),
            ("Generated", str(result.generated_nodes)),
            ("Max frontier", str(result.max_frontier)),
            ("Peak memory", f"{result.peak_memory / 1024:.1f} KiB"),
        ]
        x, y, width = max(12, surface.get_width() - 222), 18, 210
        height = 30 + len(rows) * 21
        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        panel.fill((*PANEL, 225))
        surface.blit(panel, (x, y))
        surface.blit(self.font.render("Solver statistics", True, TEXT), (x + 10, y + 7))
        for index, (label, value) in enumerate(rows):
            text = f"{label}: {value}"
            surface.blit(self.small_font.render(text, True, MUTED), (x + 10, y + 32 + index * 21))

    def clicked(self, position):
        return next((label for label, rect in self.buttons.items() if rect.collidepoint(position)), None)

    def choose_level(self, screen, levels):
        if not levels:
            return None
        clock = pygame.time.Clock()
        selected = 0
        title = self.font.render('Select a level (Up/Down, Enter; Esc to return)', True, TEXT)
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return None
                    if event.key in (pygame.K_UP, pygame.K_DOWN):
                        step = 1 if event.key == pygame.K_DOWN else -1
                        selected = (selected + step) % len(levels)
                    if event.key == pygame.K_RETURN:
                        return levels[selected]
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for index in range(len(levels)):
                        if pygame.Rect(50, 85 + index * 38, screen.get_width() - 100, 34).collidepoint(event.pos):
                            return levels[index]
            screen.fill((17, 24, 39))
            screen.blit(title, (36, 32))
            for index, level in enumerate(levels):
                color = (70, 218, 174) if index == selected else MUTED
                screen.blit(self.font.render(level.name, True, color), (60, 100 + index * 38))
            pygame.display.flip()
            clock.tick(30)


