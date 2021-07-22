import time
from ctypes import pointer, c_ulong, windll, sizeof

import pyautogui

from aim_lib.aimer import Input_I, MouseInput, Input

time.sleep(3)
print(pyautogui.position())


def move_mouse(x, y):  # relative
    ii = Input_I()
    ii.mi = MouseInput(x, y, 0, 0x1, 0, pointer(c_ulong(0)))
    command = Input(c_ulong(0), ii)
    windll.user32.SendInput(1, pointer(command), sizeof(command))

move_mouse(100,100)
print(pyautogui.position())