import copy
import math
import os
import random
import time
from ctypes import *
from tkinter import *
from collections import defaultdict

import win32con
import win32gui

import aim_lib
from aim_lib import BFV
from aim_lib.BFV import GameSoldierData, DebugDrawMatrix, DebugDrawVec3
from aim_lib.bones import bones
from aim_lib.keycodes import *

DEBUG = True

aim_location_index = 0
aim_switch_pressed = False

draw_soldier_name = True

# Color switch time
center_line_on = True
n_times_back_to_origin = 8
current_times = 0
default_line_color = "#2D2D2D"
center_line_color = [default_line_color, "#FF0F0F"]

# Dangerous enemy around you inside the range
radar_detect_critical_range = 60

increment_detect = 5
increment_interval = 0.16

# 30 is max horizontal fov, 36 is diagonal, given game FOV setting to 90
max_dw = 36

# simulate on click
clicked = defaultdict(float)

# Range font size settings
font_min_size = 12
font_min_dist = 70
font_max_size = 20
x_meter_per_one_font_size = font_min_dist / (font_max_size - font_min_size)


def is_clicked(button, minimal_click_interval=0.3):

    if (cdll.user32.GetAsyncKeyState(button) & 0x8000) and time.time() - clicked[button] > minimal_click_interval:
        clicked[button] = time.time()
        return True
    else:
        return False


def get_enemy_position(Soldier, data):
    transform = copy.copy(Soldier.aim)
    transform[0] = transform[0] + Soldier.accel[0] - data.myaccel[0]
    transform[1] = transform[1] + Soldier.accel[1] - data.myaccel[1]
    transform[2] = transform[2] + Soldier.accel[2] - data.myaccel[2]
    return int(transform[0]), int(transform[1]), int(transform[2])


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


class Aimer:
    tick = 0
    closestDistance = 9999
    closestSoldier = None
    closestSoldierMovementX = 0
    closestSoldierMovementY = 0
    lastSoldier = 0
    screensize = (0, 0)

    def __init__(self, screensize, trigger, distance_limit, fov, aim_locations, aim_switch):
        self.screensize = screensize
        self.trigger = trigger
        self.distance_limit = distance_limit
        self.fov = fov

        self.aim_locations = aim_locations
        self.aim_switch = aim_switch

    def DebugPrintVec4(self, Vec4):
        print("[%.3f %.3f %.3f %.3f ]\n" % (Vec4[0], Vec4[1], Vec4[2], Vec4[3]))

    def accelDistance(self, distance):
        leftMin = 0
        rightMin = 0.5
        leftSpan = 100 - 0
        rightSpan = 1.2 - 0.5

        # Convert the left range into a 0-1 range (float)
        valueScaled = float(distance - leftMin) / float(leftSpan)

        # Convert the 0-1 range into a value in the right range.
        return rightMin + (valueScaled * rightSpan)
        # return 0.0 + (distance - 0) / 20 * 100


    # return if the enemy is behind the player and not occluded
    # return a tuple, first indicate if the enemy is within dangerous range,
    # second is if the enemy is already drawn on the screen
    def draw_body(self, canvas, Soldier, data):
        dw, distance, delta_x, delta_y, Soldier.ptr, dfc, x, y = self.calcAim(data, Soldier)

        # w is "vector" version of distance, have +/- sign
        w = distance - dw

        # Make sure it's not upside down
        if w >= 0:

            body = self.get_bones(Soldier, data.myviewmatrix)
            occluded = Soldier.occluded
            occluded = Soldier.occluded

            isMainBody = True
            head_top = body[0][-1]

            font_size = font_min_size if distance >= font_min_dist else font_min_size + int(
                (font_min_dist - distance) / x_meter_per_one_font_size)

            if DEBUG:
                position = get_enemy_position(Soldier, data)
                text = f"{int(distance)}m, {position}"
            else:
                text = f"{int(distance)}m"

            if draw_soldier_name:
                name = Soldier.name + ': ' if len(Soldier.name) != 0 else ''
                text = name + text

            if (not 0 < x < self.screensize[0]) or (not 0 < y < self.screensize[1]):
                if center_line_on:
                    canvas.create_line(self.screensize[0] / 2, 0, head_top[0], head_top[1],
                                       fill=center_line_color[0], width=1)
                if int(distance) <= radar_detect_critical_range:
                    return 1
                else:
                    return 0
            # Draw centre aim line
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
                                           fill="blue", width=3)
                    for point_index in range(6, len(part) - 1):
                        canvas.create_line(part[point_index][0], part[point_index][1],
                                           part[point_index + 1][0], part[point_index + 1][1],
                                           fill="white", width=3)
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

        if int(distance) <= radar_detect_critical_range:
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

    def start(self):
        print("[+] Searching for BFV.exe")
        phandle = BFV.get_handle()
        if phandle:
            time.sleep(1)
        else:
            print("[-] Error: Cannot find BFV.exe")
            exit(1)

        print("[+] BFV.exe found, Handle 0x%x" % phandle)
        cnt = 0
        # mouse = Controller()
        self.lastSoldier = 0
        self.lastX = 0
        self.lastY = 0
        aim_location_index = 0
        aim_location_max = len(self.aim_locations) - 1
        aim_switch_pressed = False

        aim_location_names = []
        for location in self.aim_locations:
            for key in bones:
                if bones[key] == location:
                    aim_location_names.append(key)

        ###################################################################
        root = Tk()
        title = "ALVIN'S AIM GOD"
        root.title(title)
        root.geometry("{0}x{1}+0+0".format(root.winfo_screenwidth(), root.winfo_screenheight()))

        from PIL import ImageTk, Image
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
        ###############################################
        set_click_through(title)
        LOOP_ACTIVE = True

        global DEBUG, radar_detect_critical_range, draw_soldier_name
        st = time.time()
        while LOOP_ACTIVE:

            t0 = time.time()
            if t0 - st > 20:
                return 0
            # change aim location index if key is pressed
            if self.aim_switch is not None:
                if cdll.user32.GetAsyncKeyState(self.aim_switch) & 0x8000:
                    aim_switch_pressed = True
                elif aim_switch_pressed:
                    aim_switch_pressed = False
                    aim_location_index = aim_location_index + 1
                    if aim_location_index > aim_location_max:
                        aim_location_index = 0

            BFV.process(phandle, cnt, self.aim_locations[aim_location_index])
            cnt += 1

            data = BFV.gamedata

            self.closestDistance = 9999
            self.closestSoldier = None
            self.closestSoldierMovementX = 0
            self.closestSoldierMovementY = 0

            if self.lastSoldier != 0:
                if cdll.user32.GetAsyncKeyState(self.trigger) & 0x8000:
                    found = False
                    for Soldier in data.soldiers:
                        if self.lastSoldier == Soldier.ptr:
                            found = True
                            if Soldier.occluded:
                                self.lastSoldier = 0
                                self.closestSoldier = None
                                self.lastX = 0
                                self.lastY = 0
                                continue
                            try:
                                dw, distance, delta_x, delta_y, Soldier.ptr, dfc, x, y = self.calcAim(data, Soldier)
                                self.closestDistance = dfc
                                self.closestSoldier = Soldier

                                # accel = 0  # this is WIP
                                self.closestSoldierMovementX = delta_x  # + (self.lastX * accel)
                                self.closestSoldierMovementY = delta_y  # + (self.lastY * accel)
                                self.lastX = delta_x
                                self.lastY = delta_y
                            except Exception as e:
                                self.lastSoldier = 0
                                self.closestSoldier = None
                                print("Disengaging: soldier no longer meets criteria: %s" % e)
                    if not found:
                        self.lastSoldier = 0
                        self.closestSoldier = None
                        self.lastX = 0
                        self.lastY = 0
                        print("Disengaging: soldier no longer found")
                else:
                    self.lastSoldier = 0
                    self.closestSoldier = None
                    self.lastX = 0
                    self.lastY = 0
                    print("Disengaging: key released")
            else:

                for Soldier in data.soldiers:

                    try:
                        dw, distance, delta_x, delta_y, Soldier.ptr, dfc, x, y = self.calcAim(data, Soldier)

                        if dw > self.fov:
                            continue
                        if Soldier.occluded:
                            continue

                        if self.distance_limit is not None and distance > self.distance_limit:
                            continue

                        if dfc < self.closestDistance:  # is actually comparing dfc, not distance
                            if cdll.user32.GetAsyncKeyState(self.trigger) & 0x8000:
                                self.closestDistance = dfc
                                self.closestSoldier = Soldier
                                self.closestSoldierMovementX = delta_x
                                self.closestSoldierMovementY = delta_y
                                self.lastSoldier = Soldier.ptr
                                self.lastSoldierObject = Soldier
                                self.lastX = delta_x
                                self.lastY = delta_y

                    except:
                        # print("Exception", sys.exc_info()[0])
                        continue
                status = "[%s] " % aim_location_names[aim_location_index]
                if self.lastSoldier != 0:
                    if self.lastSoldierObject.name != "":
                        name = self.lastSoldierObject.name
                        if self.lastSoldierObject.clan != "":
                            name = "[%s]%s" % (self.lastSoldierObject.clan, name)
                    else:
                        name = "0x%x" % self.lastSoldier
                    status = status + "locked onto %s" % name
                else:
                    status = status + "idle"
            if self.closestSoldier is not None:
                if cdll.user32.GetAsyncKeyState(self.trigger) & 0x8000:
                    if self.closestSoldierMovementX > self.screensize[0] / 2 or self.closestSoldierMovementY > \
                            self.screensize[1] / 2:
                        continue
                    else:
                        if abs(self.closestSoldierMovementX) > self.screensize[0]:
                            continue
                        if abs(self.closestSoldierMovementY) > self.screensize[1]:
                            continue
                        if self.closestSoldierMovementX == 0 and self.closestSoldierMovementY == 0:
                            continue

                        self.move_mouse(int(self.closestSoldierMovementX), int(self.closestSoldierMovementY))

            #########################
            my_canvas.delete("all")

            count_close_enemy = 0
            count_all = 0
            for Soldier in data.soldiers:
                count_all += 1
                try:
                    count_close_enemy += self.draw_body(my_canvas, Soldier, data)
                    # dw, distance, delta_x, delta_y, Soldier.ptr, dfc, x, y = self.calcAim(data, Soldier)
                    # Wprint(f"{count_all} at :{(x,y)}")
                except:
                    # print(f"Exception when draw enemy")
                    pass
            my_canvas.create_text(self.screensize[0] / 2, 40, fill="lavender",
                                  font=("Times 20 italic bold", 18),
                                  text=f"{count_close_enemy}/{count_all} enemies around you\n"
                                       f"   (search {radar_detect_critical_range} m)")

            if DEBUG:
                try:
                    DebugDrawMatrix(my_canvas, data.myviewmatrix, 20, 60, title="Viewmatrix")
                    DebugDrawMatrix(my_canvas, data.mytransform, 20, 240, title="Transform")

                    DebugDrawVec3(my_canvas, data.myaccel, 20, 360, title="My acceleration")
                    DebugDrawVec3(my_canvas, data.myinitialspeed, 20, 415, title="Weapon Initial speed", color='red')

                    my_canvas.create_text(20, 485, fill="RoyalBlue1", anchor='nw',
                                          font=("Times 20 italic bold", 16),
                                          text="Instruction: \n"
                                               "Hold LALT for aimbot\n"
                                               "Press +/- to change radar search range\n"
                                               "Press mouse MIDDLE button to enable/disable details\n"
                                               "Press * to change aim line render style\n"
                                               "Press / to show/hide enemy names")
                except AttributeError:
                    pass

            if is_clicked(MBUTTON):
                DEBUG = not DEBUG

            if is_clicked(ADD, increment_interval):
                radar_detect_critical_range += increment_detect

            if is_clicked(SUBTRACT, increment_interval):
                if radar_detect_critical_range > increment_detect:
                    radar_detect_critical_range -= increment_detect
                else:
                    radar_detect_critical_range = 0

            if is_clicked(MULTIPLY, 0.2):
                switch_aim_line_style()

            if is_clicked(DIVIDE):
                draw_soldier_name = not draw_soldier_name



            my_canvas.create_text(1650, 20, fill="RoyalBlue1", anchor='nw',
                                  font=("Times 20 italic bold", 16),
                                  text=f"Aimgod FPS: {int(1 / (time.time() - t0))}\n")
            root.update()

    def calDW(self, data, Soldier):
        transform = copy.copy(Soldier.aim)

        transform[0] = transform[0] + Soldier.accel[0] - data.myaccel[0]
        transform[1] = transform[1] + Soldier.accel[1] - data.myaccel[1]
        transform[2] = transform[2] + Soldier.accel[2] - data.myaccel[2]

        x, y, w = self.World2Screen(data.myviewmatrix, transform[0], transform[1], transform[2])
        distance = self.FindDistance(Soldier.transform[3][0], Soldier.transform[3][1], Soldier.transform[3][2],
                                     data.mytransform[3][0], data.mytransform[3][1], data.mytransform[3][2])

        return distance - w

    def calcAim(self, data, Soldier):

        transform = copy.deepcopy(Soldier.aim)

        transform[0] = transform[0] + Soldier.accel[0] - data.myaccel[0]
        transform[1] = transform[1] + Soldier.accel[1] - data.myaccel[1]
        transform[2] = transform[2] + Soldier.accel[2] - data.myaccel[2]

        x, y, w = self.World2Screen(data.myviewmatrix, transform[0], transform[1], transform[2])

        distance = self.FindDistance(Soldier.transform[3][0], Soldier.transform[3][1], Soldier.transform[3][2],
                                     data.mytransform[3][0], data.mytransform[3][1], data.mytransform[3][2])

        dw = distance - w

        delta_x = (self.screensize[0] / 2 - x) * -1
        delta_y = (self.screensize[1] / 2 - y) * -1

        dfc = math.sqrt(delta_x ** 2 + delta_y ** 2)

        return dw, distance, delta_x / 2, delta_y / 2, Soldier.ptr, dfc, x, y

    def FindDistance(self, d_x, d_y, d_z, l_x, l_y, l_z):
        distance = math.sqrt((d_x - l_x) ** 2 + (d_y - l_y) ** 2 + (d_z - l_z) ** 2)
        return distance

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

    def move_mouse(self, x, y):  # relative
        ii = Input_I()
        ii.mi = MouseInput(x, y, 0, 0x1, 0, pointer(c_ulong(0)))
        command = Input(c_ulong(0), ii)
        windll.user32.SendInput(1, pointer(command), sizeof(command))


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
