import itertools
from PySide6.QtWidgets import QLabel
import time

MARGIN = 3
DEFAULT_WIDTH = 80

PACMAN = ["<span style='color: yellow; font-weight: bold;'>C</span>", "<span style='color: yellow; font-weight: bold;'>c</span>"]
CANDY = ["0 ", "0 ", "0 "]


class Pacman:
    """PacMan Progress Bar"""

    def __init__(self, label_widget, start=0, end=100, width=-1, step=0, text='', candy_count=30):
        self.label_widget = label_widget
        self.start = start
        self.end = end
        self.percentage = 0
        self.step = step
        self.text = '{0}: '.format(text) if text != '' else ''
        self.len = self.end - self.start
        self.candy_count = candy_count

        if (width - MARGIN) in range(0, DEFAULT_WIDTH):
            self.width = width - MARGIN
        else:
            self.width = DEFAULT_WIDTH

        self.bar = "--"
        self.pacman = itertools.cycle(PACMAN)
        self.candy = itertools.cycle(CANDY)
        self.candybar = [" 0 "] * self.candy_count

        self.update_display()

    def update_display(self):
        self.label_widget.setText("0% [" + "".join(self.candybar) + "]")

    def _set_percentage(self):
        step = float(self.step)
        end = float(self.end)
        self.percentage = format((100 * step / end), '.1f')

    def _draw(self):
        self._set_percentage()
        porc = self.text + str(self.percentage) + "%["
        pos = int(((self.step / (self.end - self.start)) * (self.candy_count - 1)))
        bar_progress = porc + "".join([self.bar for _ in range(pos)]) + next(self.pacman) + "".join(self.candybar[pos + 1:]) + "]"
        self.label_widget.setText(bar_progress)

    def update(self, value=1):
        self.step += float(value)
        if self.step > self.len:
            self.step = self.len
        self._draw()


    def progress(self, value):
        self.step = float(value)
        if self.step > self.len:
            self.step = self.len
        self._draw()
