import ctypes
import subprocess
import sys
import time

import win32console
from elevate.windows import ShellExecuteInfo, SEE_MASK_NOCLOSEPROCESS, SEE_MASK_NO_CONSOLE, ShellExecuteEx

import aim_lib
from aim_lib import aimer
from aim_lib import helpers
from aim_lib import keycodes
from aim_lib.bones import bones


# from elevate.windows import ShellExecuteInfo, SEE_MASK_NOCLOSEPROCESS, SEE_MASK_NO_CONSOLE, ShellExecuteEx


def assist():
    #### CHANGE OPTIONS HERE ####

    # Field of View
    # Alter this between 0.1 and 3.0 for best results. 0.1 is very narrow, while larger numbers allow
    # for more soldiers to be targeted
    fov = 3.5

    # Distance Limit
    # Example, set to 100 to limit locking onto soldiers further than 100 meters away.
    # distance_limit = None

    # Trigger Button
    # Grab your preferred button from lib/keycodes.py
    trigger = keycodes.LALT
    # trigger = keycodes.RBUTTON

    # Aim Location Options
    # Aim Location Switching (default is the first one listed)
    # Check available bones in lib/bones.py
    aim_locations = [bones['Head'], bones['Spine'], bones['Neck'], bones['Hips']]

    # # Key to switch aim location (set to None to disable)
    # aim_switch = keycodes.END
    # # aim_switch = None

    # Normally, you won't need to change this
    # This will attempt to gather your primary screen size. If you have issues or use
    # a windowed version of BFV, you'll need to set this yourself, which probably comes with its own issues
    screensize = ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1)
    # or
    # screensize = (1280, 960)

    #### END OF CHANGE OPTIONS ####

    version = "0.5"

    # if __name__ == "__main__":
    print("xx4 aim assist Version %s" % version)
    print("Thanks to Tormund and jo2305")

    if not helpers.is_admin():
        print("- Error: This must be run with admin privileges")
        input("Press Enter to continue...")
        exit(1)

    if not helpers.is_python3():
        print("- Error: This script requires Python 3")
        raw_input("Press Enter to continue...")
        exit(1)

    arch = helpers.get_python_arch()
    if arch != 64:
        print("- Error: This version of Python is not 64-bit")
        input("Press Enter to continue...")
        exit(1)

    print("Using screensize: %s x %s" % screensize)
    aimer = aim_lib.aimer.Aimer(screensize, trigger, fov, aim_locations)
    aimer.start()


def main():
    win32console.SetConsoleTitle("Aim God")

    if not ctypes.windll.shell32.IsUserAnAdmin():
        params = ShellExecuteInfo(
            fMask=SEE_MASK_NOCLOSEPROCESS | SEE_MASK_NO_CONSOLE,
            hwnd=None,
            lpVerb=b'runas',
            lpFile=sys.executable.encode('cp1252'),
            lpParameters=subprocess.list2cmdline(sys.argv).encode('cp1252'),
            nShow=int(1))

        if not ShellExecuteEx(ctypes.byref(params)):
            raise ctypes.WinError()

    else:
        assist()

# if __name__ == "__main__":
#     win32console.SetConsoleTitle("Aim God")
#
#     if not ctypes.windll.shell32.IsUserAnAdmin():
#
#         params = ShellExecuteInfo(
#             fMask=SEE_MASK_NOCLOSEPROCESS | SEE_MASK_NO_CONSOLE,
#             hwnd=None,
#             lpVerb=b'runas',
#             lpFile=sys.executable.encode('cp1252'),
#             lpParameters=subprocess.list2cmdline(sys.argv).encode('cp1252'),
#             nShow=int(1))
#
#         if not ShellExecuteEx(ctypes.byref(params)):
#             raise ctypes.WinError()
#
#     else:
#         assist()
