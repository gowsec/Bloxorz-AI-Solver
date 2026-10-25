"""Pygame game loop backed by the real level loader and engine."""
from pathlib import Path
import pygame
from src.core.engine import Engine
from src.core.constants import Outcome
from src.gui.animation import RollAnimation
from src.gui.controls import action_for_key
from src.gui.renderer import Renderer
from src.gui.ui import UI
from src.utils.json_loader import load_level

class Game:
    def __init__(self, level=None):
        self.level = level

    @staticmethod
    def levels():
        return [load_level(path) for path in sorted((Path(__file__).resolve().parents[2] / 'levels').glob('level*.json'))]

    def run(self):
        pygame.init()
        try:
            screen=pygame.display.set_mode((1000,760),pygame.RESIZABLE)
            pygame.display.set_caption('Bloxorz')
            clock=pygame.time.Clock(); renderer=Renderer(); ui=UI(); animation=RollAnimation()
            level=self.level or ui.choose_level(screen,self.levels())
            if level is None: return
            engine=Engine(level); state=engine.initial_state(); message=''
            running=True
            while running:
                for event in pygame.event.get():
                    if event.type==pygame.QUIT: running=False
                    elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                        clicked=ui.clicked(event.pos)
                        if clicked=='Restart': state=engine.initial_state(); message=''
                        elif clicked=='New Game':
                            chosen=ui.choose_level(screen,self.levels())
                            if chosen: level=chosen; engine=Engine(level); state=engine.initial_state(); message=''
                    elif event.type==pygame.KEYDOWN:
                        if event.key==pygame.K_ESCAPE: running=False
                        elif event.key==pygame.K_r: state=engine.initial_state(); message=''
                        elif event.key==pygame.K_n:
                            chosen=ui.choose_level(screen,self.levels())
                            if chosen:
                                level=chosen; engine=Engine(level); state=engine.initial_state(); message=''
                        elif not message:
                            action=action_for_key(event.key)
                            if action:
                                next_state,outcome=engine.try_step(state,action)
                                if outcome==Outcome.OK:
                                    animation.begin(state.pose,next_state.pose); state=next_state
                                    if engine.is_goal(state): message='You win!'
                                else: message='You fell! Press R to restart.'
                renderer.draw(screen,level,state,animation.offset(),message)
                ui.draw(screen)
                pygame.display.flip(); clock.tick(60)
        finally: pygame.quit()



