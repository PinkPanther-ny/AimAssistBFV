import copy
import math
import os
import random
import time
from ctypes import *
from tkinter import *
from tkinter import font

import win32con
import win32gui
from PIL import ImageTk, Image

from aim_lib import BFV, settings
from aim_lib.BFV import GameSoldierData, DebugDrawMatrix, DebugDrawVec3
from aim_lib.bones import bones
from aim_lib.keycodes import *
from aim_lib.settings import *


def is_down(button):
    return cdll.user32.GetAsyncKeyState(button) & 0x8000


def is_clicked(button, minimal_click_interval=0.3):
    if is_down(button) and time.time() - clicked[button] > minimal_click_interval:
        clicked[button] = time.time()
        return True
    else:
        return False


def get_enemy_position(Soldier):
    return int(Soldier.aim[0]), int(Soldier.aim[1]), int(Soldier.aim[2])


def set_click_through(title):
    hwnd = win32gui.FindWindow(None, title)  # Getting window handle
    print(hwnd)
    # hwnd = root.winfo_id() getting hwnd with Tkinter windows
    # hwnd = root.GetHandle() getting hwnd with wx windows
    lExStyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    lExStyle |= win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
    # win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, lExStyle)

    extendedStyleSettings = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                           extendedStyleSettings | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)


def switch_aim_line_style():
    global current_times, center_line_color, center_line_on
    current_times += 1

    if current_times == n_times_back_to_origin:
        current_times = 0
        center_line_color[0] = default_line_color
        return
    if current_times == 1:
        center_line_on = False
    else:
        center_line_on = True

    color_hex_string = "0123456789ABCDEF"
    ret_color = "#"
    for i in range(6):
        ret_color += color_hex_string[random.randint(0, 15)]
    center_line_color = [ret_color, "#FF0F0F"]


def DebugPrintVec4(Vec4):
    print("[%.3f %.3f %.3f %.3f ]\n" % (Vec4[0], Vec4[1], Vec4[2], Vec4[3]))


def accelDistance(distance):
    leftMin = 0
    rightMin = 0.5
    leftSpan = 100 - 0
    rightSpan = 1.2 - 0.5

    # Convert the left range into a 0-1 range (float)
    valueScaled = float(distance - leftMin) / float(leftSpan)

    # Convert the 0-1 range into a value in the right range.
    return rightMin + (valueScaled * rightSpan)
    # return 0.0 + (distance - 0) / 20 * 100


def FindDistance(d_x, d_y, d_z, l_x, l_y, l_z):
    distance = math.sqrt((d_x - l_x) ** 2 + (d_y - l_y) ** 2 + (d_z - l_z) ** 2)
    return distance


class Aimer:
    tick = 0
    closestDistance = 9999
    closestSoldier = None
    closestSoldierMovementX = 0
    closestSoldierMovementY = 0
    lastSoldier = 0
    screensize = (0, 0)
    blackList = []

    def __init__(self, screensize, trigger, fov, aim_locations):
        self.screensize = screensize
        self.trigger = trigger
        self.fov = fov

        self.aim_locations = aim_locations

        self.lastSoldierObject = None

        self.closestDistance = 9999
        self.closestSoldier = None
        self.closestSoldierMovementX = 0
        self.closestSoldierMovementY = 0

        self.blackList = []

        # Create tkinter GUI
        self.root = None
        self.my_canvas = None
        ###################################################################
        root = Tk()
        title = "ALVIN'S AIM GOD"
        root.title(title)
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
        root.wm_attributes("-topmost", True)
        # Turn off the window shadow
        root['bg'] = "#000000"
        root.wm_attributes("-transparentcolor", "#000000")
        root.wm_attributes("-alpha", 0.6)

        root.state('zoomed')
        my_canvas = Canvas(root, width=root.winfo_screenwidth(), height=root.winfo_screenheight(), bg="#000000")

        my_canvas.pack()
        set_click_through(title)
        ####################
        self.root = root
        self.my_canvas = my_canvas

    def move_mouse(self, x, y):  # relative
        ii = Input_I()
        ii.mi = MouseInput(x, y, 0, 0x1, 0, pointer(c_ulong(0)))
        command = Input(c_ulong(0), ii)
        windll.user32.SendInput(1, pointer(command), sizeof(command))

    def UpdateBlackList(self):
        self.blackList = []
        with open('blackList', 'r') as file1:
            for name in file1.readlines():
                self.blackList.append(name.strip())
                # print(name.strip())

    # return if the enemy is behind the player and not occluded
    # indicate if the enemy is within dangerous range
    def draw_body(self, canvas, Soldier, data):
        ad_x, ad_y, ret_aim_info = None, None, None
        try:
            if settings.advanced_aim_on:
                ret_aim_info = self.calcAim_advanced(data, Soldier)
                ad_x, ad_y = ret_aim_info[-2], ret_aim_info[-1]
        except:
            pass

        # w is "vector" version of distance, have +/- sign
        x, y, w = self.World2Screen(data.myviewmatrix, Soldier.aim[0], Soldier.aim[1], Soldier.aim[2])

        distance = FindDistance(Soldier.transform[3][0], Soldier.transform[3][1], Soldier.transform[3][2],
                                data.mytransform[3][0], data.mytransform[3][1], data.mytransform[3][2])

        # Make sure it's not upside down
        if w >= 0:

            body = self.get_bones(Soldier, data.myviewmatrix)
            occluded = Soldier.occluded

            isMainBody = True
            head_top = body[0][-1]

            font_size = font_min_size if distance >= font_min_dist else font_min_size + int(
                (font_min_dist - distance) / x_meter_per_one_font_size)

            if settings.DEBUG:
                # position = get_enemy_position(Soldier)
                # text = f"{int(distance)}m, {int(Soldier.aim[0]), int(Soldier.aim[1]), int(Soldier.aim[2])}"
                # text = "[%.3f %.3f %.3f ]\n" % ((Soldier.accel[0]), (Soldier.accel[1]), (Soldier.accel[2]))
                text = f"{int(distance)}m, dfc: {int(ret_aim_info[-3])}, dw: {int(ret_aim_info[0])}"
            else:
                text = f"{int(distance)}m"

            if settings.draw_soldier_name:
                name = Soldier.name + ': ' if len(Soldier.name) != 0 else ''
                if not settings.blackList_On:
                    text = name + text
                else:
                    for i in self.blackList:
                        if i in name:
                            text = name + text
                            break

            # Draw centre aim line
            if (not 0 < x < self.screensize[0]) or (not 0 < y < self.screensize[1]):
                if center_line_on:
                    canvas.create_line(self.screensize[0] / 2, 0, head_top[0], head_top[1],
                                       fill=center_line_color[0], width=1)
                # Early return for performance
                if int(distance) <= settings.radar_detect_critical_range:
                    return 1
                else:
                    return 0

            if Soldier.occluded:

                canvas.create_text(head_top[0], head_top[1], fill="white", font=("Times 20 italic bold", font_size),
                                   text=text)

                if center_line_on:
                    canvas.create_line(self.screensize[0] / 2, 0, head_top[0], head_top[1],
                                       fill=center_line_color[0], width=1)
            else:
                canvas.create_text(head_top[0], head_top[1], fill="#CC0000",
                                   font=("Times 20 italic bold", int(font_size * 1.35)),
                                   text=text)

                if center_line_on:
                    canvas.create_line(self.screensize[0] / 2, 0, head_top[0], head_top[1],
                                       fill=center_line_color[1], width=1.4)

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

    def search_new_target(self, data):
        for Soldier in data.soldiers:
            try:
                dw, distance, delta_x, delta_y, Soldier.ptr, dfc, x, y = self.calcAim_advanced(
                    data, Soldier)

                if dw > self.fov:
                    continue
                if Soldier.occluded and (not settings.engage_occluded_target):
                    continue

                if dfc < self.closestDistance:  # is actually comparing dfc, not distance
                    if is_down(self.trigger):
                        self.closestDistance = dfc
                        self.closestSoldier = Soldier
                        self.closestSoldierMovementX = delta_x
                        self.closestSoldierMovementY = delta_y
                        self.lastSoldier = Soldier.ptr
                        self.lastSoldierObject = Soldier

            except:
                # print("Exception", sys.exc_info()[0])
                continue

    def validate_last_target(self, data):
        found = False

        for Soldier in data.soldiers:
            if self.lastSoldier == Soldier.ptr:
                found = True
                if Soldier.occluded and (not settings.engage_occluded_target):
                    self.clear_target()
                    continue

                try:
                    dw, distance, delta_x, delta_y, Soldier.ptr, dfc, x, y = self.calcAim_advanced(
                        data, Soldier)

                    self.closestDistance = dfc
                    self.closestSoldier = Soldier

                    self.closestSoldierMovementX = delta_x
                    self.closestSoldierMovementY = delta_y
                except Exception as e:
                    self.clear_target(message=("Disengaging: soldier no longer meets criteria: %s" % e))

        if not found:
            self.clear_target(message="Disengaging: soldier no longer found")

    def aim_to_target(self):

        if self.closestSoldierMovementX > self.screensize[0] / 2 or \
                self.closestSoldierMovementY > self.screensize[1] / 2:
            return False
        else:
            if abs(self.closestSoldierMovementX) > self.screensize[0] or \
                    abs(self.closestSoldierMovementY) > self.screensize[1]:
                return False
            if self.closestSoldierMovementX == 0 and self.closestSoldierMovementY == 0:
                return False

        self.move_mouse(int(self.closestSoldierMovementX), int(self.closestSoldierMovementY))
        return True

    def handle_clicks(self):

        if is_clicked(MBUTTON):
            settings.DEBUG = not settings.DEBUG

        if is_clicked(ADD, increment_interval):
            settings.radar_detect_critical_range += increment_detect

        if is_clicked(SUBTRACT, increment_interval):
            if settings.radar_detect_critical_range > increment_detect:
                settings.radar_detect_critical_range -= increment_detect
            else:
                settings.radar_detect_critical_range = 0

        if is_clicked(MULTIPLY, 0.2):
            switch_aim_line_style()

        if is_clicked(DIVIDE):
            settings.draw_soldier_name = not settings.draw_soldier_name

        if is_clicked(ENTER):
            settings.advanced_aim_on = not settings.advanced_aim_on

        if is_clicked(BACKSPACE):
            settings.blackList_On = not settings.blackList_On

    def clear_target(self, message=""):
        self.lastSoldier = 0
        self.closestSoldier = None
        print(message)

    def start(self):
        print("[+] Searching for BFV.exe")
        phandle = BFV.get_handle()
        if phandle:
            time.sleep(1)
        else:
            print("[-] Error: Cannot find BFV.exe")
            exit(1)

        print("[+] BFV.exe found, Handle 0x%x" % phandle)

        aim_location_names = []
        for location in self.aim_locations:
            for key in bones:
                if bones[key] == location:
                    aim_location_names.append(key)

        ###############################################

        while True:

            t0 = time.time()

            BFV.process(phandle, self.aim_locations[0])
            data = BFV.gamedata

            self.closestDistance = 9999
            self.closestSoldier = None
            self.closestSoldierMovementX = 0
            self.closestSoldierMovementY = 0

            # WIP

            # for Soldier in data.soldiers:
            #     ret_aim_info = self.calcAim_advanced(data, Soldier)
            #     if not Soldier.occluded and ret_aim_info[0] < self.fov:
            #
            #         settings.engage_occluded_target = True
            #         break

            if self.lastSoldier != 0:
                if is_down(self.trigger):
                    self.validate_last_target(data)
                else:
                    self.clear_target(message="Disengaging: key released")
            else:
                self.search_new_target(data)

            if self.closestSoldier is not None:
                if is_down(self.trigger):
                    self.aim_to_target()

            ############################################################################################################
            self.my_canvas.delete("all")

            count_close_enemy = 0
            count_all = 0
            for Soldier in data.soldiers:
                count_all += 1
                try:
                    count_close_enemy += self.draw_body(self.my_canvas, Soldier, data)
                except:
                    # print(f"Exception when draw enemy")
                    pass

            self.my_canvas.create_text(self.screensize[0] / 2, 40, fill="lavender",
                                       font=("Times 20 italic bold", 18),
                                       text=f"{count_close_enemy}/{count_all} enemies around you\n"
                                            f"   (search {settings.radar_detect_critical_range} m)")

            if settings.DEBUG:
                width_rect = 585
                height_rect = 520
                offset_x = -8
                offset_y = 453

                self.my_canvas.create_rectangle(offset_x + 15, offset_y + 100,
                                                offset_x + 15 + width_rect, offset_y + 100 + height_rect,
                                                fill='gray50', outline='gray70', width=8)
                self.my_canvas.create_text(offset_x + 22, offset_y + 475, fill="Blue3", anchor='nw',
                                           font=(font.BOLD, 14),
                                           text="Instruction: \n"
                                                "Hold LALT for aimbot\n"
                                                "Press ENTER to engage/disengage occluded targets\n"
                                                "Press +/- to change radar search range\n"
                                                "Press mouse MIDDLE button to enable/disable details\n"
                                                "Press * to change aim line render style\n"
                                                "Press / to show/hide enemy names")

                DebugDrawMatrix(self.my_canvas, data.myviewmatrix, offset_x + 20, offset_y + 120, title="Viewmatrix")
                DebugDrawMatrix(self.my_canvas, data.mytransform, offset_x + 20, offset_y + 240, title="Transform")

                DebugDrawVec3(self.my_canvas, data.myaccel, offset_x + 20, offset_y + 360, title="My acceleration")
                DebugDrawVec3(self.my_canvas, data.myinitialspeed, offset_x + 20, offset_y + 420,
                              title="Weapon Initial speed",
                              color='red')

            self.my_canvas.create_text(1795, 15, fill="gray80", anchor='nw',
                                       font=(font.NORMAL, 12),
                                       text=f"Aimgod FPS: {settings.fps_count if settings.fps_count <= max_fps else max_fps}\n")

            self.handle_clicks()
            self.root.update()

            t1 = time.time()
            if t1 - settings.blackList_last_update > blackList_update_interval:
                self.UpdateBlackList()

            try:
                cur_fps = int(1 / (t1 - t0))
            except ZeroDivisionError:
                cur_fps = 60

            if t1 - settings.fps_value_last_update_time >= settings.fps_value_update_rate:
                settings.fps_count = cur_fps
                settings.fps_value_last_update_time = t1

            if cur_fps > max_fps:
                time.sleep(1 / max_fps - 1 / cur_fps)

    def calcAim_advanced(self, data, Soldier):
        try:
            if settings.advanced_aim_on:
                transform = copy.deepcopy(Soldier.aim)

                distance = FindDistance(Soldier.transform[3][0], Soldier.transform[3][1], Soldier.transform[3][2],
                                        data.mytransform[3][0], data.mytransform[3][1], data.mytransform[3][2])

                time_to_hit = 0 + distance / data.myinitialspeed[2] if data.myinitialspeed[2] > 5 \
                    else settings.default_ini_speed
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
            else:
                return self.calcAim(data, Soldier)
        except:
            return self.calcAim(data, Soldier)

    def calcAim(self, data, Soldier):
        transform = Soldier.aim

        x, y, w = self.World2Screen(data.myviewmatrix, transform[0], transform[1], transform[2])

        distance = FindDistance(Soldier.transform[3][0], Soldier.transform[3][1], Soldier.transform[3][2],
                                data.mytransform[3][0], data.mytransform[3][1], data.mytransform[3][2])

        dw = distance - w

        delta_x = (self.screensize[0] / 2 - x) * -1
        delta_y = (self.screensize[1] / 2 - y) * -1

        dfc = math.sqrt(delta_x ** 2 + delta_y ** 2)

        return dw, distance, delta_x / 2, delta_y / 2, Soldier.ptr, dfc, x, y

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

    # def current_mouse_position(self):
    #     cursor = POINT()
    #     windll.user32.GetCursorPos(byref(cursor))
    #     return cursor.x, cursor.y


PUL = POINTER(c_ulong)


class KeyBdInput(Structure):
    _fields_ = [("wVk", c_ushort),
                ("wScan", c_ushort),
                ("dwFlags", c_ulong),
                ("time", c_ulong),
                ("dwExtraInfo", PUL)]


class HardwareInput(Structure):
    _fields_ = [("uMsg", c_ulong),
                ("wParamL", c_short),
                ("wParamH", c_ushort)]


class MouseInput(Structure):
    _fields_ = [("dx", c_long),
                ("dy", c_long),
                ("mouseData", c_ulong),
                ("dwFlags", c_ulong),
                ("time", c_ulong),
                ("dwExtraInfo", PUL)]


class POINT(Structure):
    _fields_ = [("x", c_long),
                ("y", c_long)]


class Input_I(Union):
    _fields_ = [("ki", KeyBdInput),
                ("mi", MouseInput),
                ("hi", HardwareInput)]


class Input(Structure):
    _fields_ = [("type", c_ulong),
                ("ii", Input_I)]
