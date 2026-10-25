"""Playable game loop with solver actions, replay, and result statistics."""
from pathlib import Path

import pygame

from src.core.constants import Outcome
from src.core.engine import Engine
from src.core.move import Action
from src.core.state import SplitPose
from src.gui.animation import RollAnimation
from src.gui.controls import action_for_key
from src.gui.renderer import Renderer
from src.gui.ui import UI
from src.solvers.astar import AStarSolver
from src.solvers.bfs import BFSSolver
from src.solvers.dfs import DFSSolver
from src.solvers.ucs import UCSSolver
from src.utils.json_loader import load_level

SOLVERS = {
    "Solve BFS": BFSSolver,
    "Solve DFS": DFSSolver,
    "Solve UCS": UCSSolver,
    "Solve A*": AStarSolver,
}


class Game:
    def __init__(self, level=None):
        self.level = level

    @staticmethod
    def levels():
        level_dir = Path(__file__).resolve().parents[2] / "levels"
        return [load_level(path) for path in sorted(level_dir.glob("level*.json"))]

    def run(self):
        pygame.init()
        try:
            screen = pygame.display.set_mode((1000, 760), pygame.RESIZABLE)
            pygame.display.set_caption("Bloxorz")
            clock = pygame.time.Clock()
            renderer, ui, animation = Renderer(), UI(), RollAnimation()
            level = self.level or ui.choose_level(screen, self.levels())
            if level is None:
                return

            engine = Engine(level)
            state = engine.initial_state()
            result = None
            solution = []
            replay_index = 0
            replaying = False
            selected_cube = 0
            game_over = False
            message = ""

            def reset(chosen_level=None):
                nonlocal level, engine, state, result, solution, replay_index
                nonlocal replaying, selected_cube, game_over, message
                if chosen_level is not None:
                    level = chosen_level
                    engine = Engine(level)
                state = engine.initial_state()
                animation.reset()
                result = None
                solution = []
                replay_index = 0
                replaying = False
                selected_cube = 0
                game_over = False
                message = ""

            def solve(algorithm):
                nonlocal state, result, solution, replay_index, replaying
                nonlocal selected_cube, game_over, message
                state = engine.initial_state()
                animation.reset()
                solver = SOLVERS[algorithm](engine)
                result = solver.solve(start=state)
                solution = list(result.path)
                selected_cube = 0
                game_over = False
                if result.status == "solved":
                    replay_index = 0
                    replaying = True
                    message = f"{result.algorithm.upper()} found a solution: {result.solution_length} moves"
                else:
                    replaying = False
                    message = f"{result.algorithm.upper()}: {result.status.replace('_', ' ')}"

            def start_replay():
                nonlocal state, replay_index, replaying, selected_cube, game_over, message
                if result is None or result.status != "solved":
                    message = "Solve a level first to create a replay."
                    return
                state = engine.initial_state()
                animation.reset()
                replay_index = 0
                selected_cube = 0
                replaying = True
                game_over = False
                message = f"Replaying {result.algorithm.upper()} solution"

            running = True
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        clicked = ui.clicked(event.pos)
                        if clicked in SOLVERS:
                            solve(clicked)
                        elif clicked == "Replay":
                            start_replay()
                        elif clicked == "Restart":
                            reset()
                        elif clicked == "New Game":
                            chosen = ui.choose_level(screen, self.levels())
                            if chosen:
                                reset(chosen)
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            running = False
                        elif event.key == pygame.K_r:
                            reset()
                        elif event.key == pygame.K_n:
                            chosen = ui.choose_level(screen, self.levels())
                            if chosen:
                                reset(chosen)
                        elif event.key == pygame.K_b:
                            solve("Solve BFS")
                        elif event.key == pygame.K_d:
                            start_replay()
                        elif event.key == pygame.K_SPACE and isinstance(state.pose, SplitPose) and not replaying:
                            selected_cube = 1 - selected_cube
                        elif not replaying and not game_over:
                            action = action_for_key(event.key)
                            if action:
                                if isinstance(state.pose, SplitPose):
                                    action = Action(action.direction, selected_cube)
                                next_state, outcome = engine.try_step(state, action)
                                if outcome == Outcome.OK:
                                    animation.begin(state.pose, next_state.pose, action.cube)
                                    state = next_state
                                    if not isinstance(state.pose, SplitPose):
                                        selected_cube = 0
                                    if engine.is_goal(state):
                                        game_over = True
                                        message = "You win!"
                                else:
                                    game_over = True
                                    message = "You fell! Press R to restart."

                if replaying and not animation.active:
                    if replay_index < len(solution):
                        action = solution[replay_index]
                        next_state, outcome = engine.try_step(state, action)
                        if outcome != Outcome.OK:
                            replaying = False
                            game_over = True
                            message = "Replay stopped: invalid solver action."
                        else:
                            animation.begin(state.pose, next_state.pose, action.cube)
                            state = next_state
                            selected_cube = action.cube or 0
                            replay_index += 1
                    else:
                        replaying = False
                        game_over = True
                        message = "You win! Replay complete."

                renderer.draw(
                    screen, level, state, animation.offset(), message,
                    selected_cube, animation.cube_offsets(),
                )
                ui.draw(screen, result, selected_cube, replaying)
                pygame.display.flip()
                clock.tick(60)
        finally:
            pygame.quit()


