import copy
import ctypes
import math
import os
import sys
import time
from tkinter import Tk, Canvas, font

import win32con
import win32gui
from PIL import ImageTk, Image

import aim_lib.settings as settings
from aim_lib.BFV import GameSoldierData
from aim_lib.keycodes import MBUTTON, ADD, SUBTRACT, MULTIPLY, DIVIDE, ENTER


class AimerUI:
    def __init__(self):
        self.window = None
        self.canvas = None

        self.title = "ALVIN'S AIM GOD"
        self.screensize = ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1)

        root = Tk()
        root.title(self.title)
        root.geometry("{0}x{1}+0+0".format(root.winfo_screenwidth(), root.winfo_screenheight()))

        def resource_path(relative_path):
            """ Get absolute path to resource, works for dev and for PyInstaller """
            try:
                # PyInstaller creates a temp folder and stores path in _MEIPASS
                base_path = sys._MEIPASS
            except Exception:
                base_path = os.path.abspath(".")

            return os.path.join(base_path, relative_path)

        ico = resource_path('ico.ico')

        img = ImageTk.PhotoImage(Image.open(ico))
        root.iconphoto(False, img)

        # Hide the root window drag bar and close button
        root.overrideredirect(1)

        # Make the root window always on top
        #root.wm_attributes("-topmost", True)
        # Turn off the window shadow
        root['bg'] = "#000000"
        root.wm_attributes("-transparentcolor", "#000000")
        root.wm_attributes("-alpha", 0.6)

        #root.state('zoomed')
        my_canvas = Canvas(root, width=root.winfo_screenwidth(), height=root.winfo_screenheight(), bg="#000000")
        my_canvas.pack()

        self.window = root
        self.canvas = my_canvas
        self.set_click_through()

    def set_click_through(self):
        # hwnd = win32gui.FindWindow(None, title)  # Getting window handle
        #  getting hwnd with Tkinter windows
        hwnd = self.window.winfo_id()
        print(f"Set tkinter window {hwnd} click through.")
        lExStyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        lExStyle |= win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
        # win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, lExStyle)

        extendedStyleSettings = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                               extendedStyleSettings | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)

    def FindDistance(self, d_x, d_y, d_z, l_x, l_y, l_z):
        distance = math.sqrt((d_x - l_x) ** 2 + (d_y - l_y) ** 2 + (d_z - l_z) ** 2)
        return distance

    def get_bones(self, Soldier: GameSoldierData, my_view_matrix):

        body = Soldier.joint[0]
        r_arm = Soldier.joint[1]
        l_arm = Soldier.joint[2]
        body_xy = []
        r_arm_xy = []
        l_arm_xy = []

        for i in body:
            x, y, w = self.World2Screen(my_view_matrix, i[0], i[1], i[2])
            body_xy.append((x, y))
        for i in r_arm:
            x, y, w = self.World2Screen(my_view_matrix, i[0], i[1], i[2])
            r_arm_xy.append((x, y))
        for i in l_arm:
            x, y, w = self.World2Screen(my_view_matrix, i[0], i[1], i[2])
            l_arm_xy.append((x, y))
        return [body_xy, r_arm_xy, l_arm_xy]

    # return if the enemy is behind the player and not occluded
    # indicate if the enemy is within dangerous range
    def draw_body(self, canvas, Soldier, data):
        ad_x, ad_y = None, None
        try:
            if settings.advanced_aim_on:
                ret_aim_info = self.calcAim_advanced(data, Soldier)
                ad_x, ad_y = ret_aim_info[-2], ret_aim_info[-1]
        except:
            pass

        # w is "vector" version of distance, have +/- sign
        x, y, w = self.World2Screen(data.myviewmatrix, Soldier.aim[0], Soldier.aim[1], Soldier.aim[2])

        distance = self.FindDistance(Soldier.transform[3][0], Soldier.transform[3][1], Soldier.transform[3][2],
                                     data.mytransform[3][0], data.mytransform[3][1], data.mytransform[3][2])

        # Make sure it's not upside down
        if w >= 0:

            body = self.get_bones(Soldier, data.myviewmatrix)
            occluded = Soldier.occluded

            isMainBody = True
            head_top = body[0][-1]

            font_size = settings.font_min_size if distance >= settings.font_min_dist else settings.font_min_size + int(
                (settings.font_min_dist - distance) / settings.x_meter_per_one_font_size)

            if settings.DEBUG:
                # position = get_enemy_position(Soldier, data)
                # text = f"{int(distance)}m, {int(Soldier.aim[0]), int(Soldier.aim[1]), int(Soldier.aim[2])}"
                # text = "[%.3f %.3f %.3f ]\n" % ((Soldier.accel[0]), (Soldier.accel[1]), (Soldier.accel[2]))
                text = f"{int(distance)}m, {ret_aim_info[-3]}"
            else:
                text = f"{int(distance)}m"

            if settings.draw_soldier_name:
                name = Soldier.name + ': ' if len(Soldier.name) != 0 else ''
                text = name + text

            # Draw centre aim line
            if (not 0 < x < self.screensize[0]) or (not 0 < y < self.screensize[1]):
                if settings.center_line_on:
                    canvas.create_line(self.screensize[0] / 2, 0, head_top[0], head_top[1],
                                       fill=settings.center_line_color[0], width=1)
                # Early return for performance
                if int(distance) <= settings.radar_detect_critical_range:
                    return 1
                else:
                    return 0

            if Soldier.occluded:

                canvas.create_text(head_top[0], head_top[1], fill="white", font=("Times 20 italic bold", font_size),
                                   text=text)

                if settings.center_line_on:
                    canvas.create_line(self.screensize[0] / 2, 0, head_top[0], head_top[1],
                                       fill=settings.center_line_color[0], width=1)
            else:
                canvas.create_text(head_top[0], head_top[1], fill="#CC0000",
                                   font=("Times 20 italic bold", int(font_size * 1.35)),
                                   text=text)

                if settings.center_line_on:
                    canvas.create_line(self.screensize[0] / 2, 0, head_top[0], head_top[1],
                                       fill=settings.center_line_color[1], width=1.4)

            # Draw soldier body
            for part in body:
                if isMainBody:
                    isMainBody = False

                    for point_index in range(0, 6):
                        canvas.create_line(part[point_index][0], part[point_index][1],
                                           part[point_index + 1][0], part[point_index + 1][1],
                                           fill="blue", width=2.5)

                    for point_index in range(6, len(part) - 1):
                        canvas.create_line(part[point_index][0], part[point_index][1],
                                           part[point_index + 1][0], part[point_index + 1][1],
                                           fill="red", width=3)

                    if ad_x is not None and ad_y is not None:
                        canvas.create_line(ad_x, ad_y,
                                           part[-2][0], part[-2][1],
                                           fill="white", width=1)

                    continue

                for point_index in range(len(part) - 1):
                    if occluded:
                        canvas.create_line(part[point_index][0], part[point_index][1],
                                           part[point_index + 1][0], part[point_index + 1][1],
                                           fill="green", width=3)
                    else:
                        canvas.create_line(part[point_index][0], part[point_index][1],
                                           part[point_index + 1][0], part[point_index + 1][1],
                                           fill="red", width=3)

        if int(distance) <= settings.radar_detect_critical_range:
            return 1
        else:
            return 0

    def World2Screen(self, MyViewMatrix, posX, posY, posZ):

        w = float(
            MyViewMatrix[0][3] * posX + MyViewMatrix[1][3] * posY + MyViewMatrix[2][3] * posZ + MyViewMatrix[3][3])

        x = float(
            MyViewMatrix[0][0] * posX + MyViewMatrix[1][0] * posY + MyViewMatrix[2][0] * posZ + MyViewMatrix[3][0])

        y = float(
            MyViewMatrix[0][1] * posX + MyViewMatrix[1][1] * posY + MyViewMatrix[2][1] * posZ + MyViewMatrix[3][1])

        mX = float(self.screensize[0] / 2)
        mY = float(self.screensize[1] / 2)

        x = float(mX + mX * x / w)
        y = float(mY - mY * y / w)

        return x, y, w

    def calcAim_advanced(self, data, Soldier):
        try:
            if settings.advanced_aim_on:
                transform = copy.deepcopy(Soldier.aim)

                distance = self.FindDistance(Soldier.transform[3][0], Soldier.transform[3][1], Soldier.transform[3][2],
                                             data.mytransform[3][0], data.mytransform[3][1], data.mytransform[3][2])

                time_to_hit = 0 + distance / data.myinitialspeed[2] if data.myinitialspeed[2] > 10 else 0
                enemy_velocity = [settings.fps_count * Soldier.accel[0], settings.fps_count * Soldier.accel[1],
                                  settings.fps_count * Soldier.accel[2]]
                transform[0] = transform[0] + time_to_hit * enemy_velocity[0]
                transform[1] = transform[1] + time_to_hit * enemy_velocity[1] + 0.5 * 12 * (time_to_hit ** 2)
                transform[2] = transform[2] + time_to_hit * enemy_velocity[2]

                x, y, w = self.World2Screen(data.myviewmatrix, transform[0], transform[1], transform[2])
                ###########
                ###########
                dw = distance - w

                delta_x = (self.screensize[0] / 2 - x) * -1
                delta_y = (self.screensize[1] / 2 - y) * -1

                dfc = math.sqrt(delta_x ** 2 + delta_y ** 2)

                return dw, distance, delta_x / 2, delta_y / 2, Soldier.ptr, dfc, x, y
        except:
            return

    def update_aimUI(self, data):
        self.canvas.delete("all")

        count_close_enemy = 0
        count_all = 0
        for Soldier in data.soldiers:
            count_all += 1
            try:
                count_close_enemy += self.draw_body(self.canvas, Soldier, data)
            except:
                # print(f"Exception when draw enemy")
                pass
        self.window.update()

        # self.canvas.create_text(self.screensize[0] / 2, 40, fill="lavender",
        #                         font=("Times 20 italic bold", 18),
        #                         text=f"{count_close_enemy}/{count_all} enemies around you\n"
        #                              f"   (search {settings.radar_detect_critical_range} m)")

        # if settings.DEBUG:
        #     width_rect = 585
        #     height_rect = 520
        #     offset_x = -8
        #     offset_y = 453
        #
        #     self.canvas.create_rectangle(offset_x + 15, offset_y + 100,
        #                                  offset_x + 15 + width_rect, offset_y + 100 + height_rect,
        #                                  fill='gray50', outline='gray70', width=8)
        #     self.canvas.create_text(offset_x + 22, offset_y + 475, fill="Blue3", anchor='nw',
        #                             font=(font.BOLD, 14),
        #                             text="Instruction: \n"
        #                                  "Hold LALT for aimbot\n"
        #                                  "Press ENTER to engage/disengage occluded targets\n"
        #                                  "Press +/- to change radar search range\n"
        #                                  "Press mouse MIDDLE button to enable/disable details\n"
        #                                  "Press * to change aim line render style\n"
        #                                  "Press / to show/hide enemy names")
        #
        #     DebugDrawMatrix(self.canvas, data.myviewmatrix, offset_x + 20, offset_y + 120, title="Viewmatrix")
        #     DebugDrawMatrix(self.canvas, data.mytransform, offset_x + 20, offset_y + 240, title="Transform")
        #
        #     DebugDrawVec3(self.canvas, data.myaccel, offset_x + 20, offset_y + 360, title="My acceleration")
        #     DebugDrawVec3(self.canvas, data.myinitialspeed, offset_x + 20, offset_y + 420,
        #                   title="Weapon Initial speed",
        #                   color='red')

        # self.canvas.create_text(1795, 15, fill="gray80", anchor='nw',
        #                         font=(font.NORMAL, 12),
        #                         text=f"Aimgod FPS: {settings.fps_count if settings.fps_count <= settings.max_fps else settings.max_fps}\n")

        # self.handle_clicks()

        # t1 = time.time()
        # try:
        #     cur_fps = int(1 / (t1 - t0))
        # except ZeroDivisionError:
        #     cur_fps = 60

        # if t1 - settings.fps_value_last_update_time >= settings.fps_value_update_rate:
        #     fps_count = cur_fps
        #     fps_value_last_update_time = t1
        #
        # if cur_fps > settings.max_fps:
        #     time.sleep(1 / settings.max_fps - 1 / cur_fps)

    # def handle_clicks(self):
    #
    #     if is_clicked(MBUTTON):
    #         DEBUG = not settings.DEBUG
    #
    #     if is_clicked(ADD, settings.increment_interval):
    #         settings.radar_detect_critical_range += settings.increment_detect
    #
    #     if is_clicked(SUBTRACT, settings.increment_interval):
    #         if settings.radar_detect_critical_range > settings.increment_detect:
    #             settings.radar_detect_critical_range -= settings.increment_detect
    #         else:
    #             radar_detect_critical_range = 0
    #
    #     if is_clicked(MULTIPLY, 0.2):
    #         switch_aim_line_style()
    #
    #     if is_clicked(DIVIDE):
    #         draw_soldier_name = not settings.draw_soldier_name
    #
    #     if is_clicked(ENTER):
    #         advanced_aim_on = not settings.advanced_aim_on
