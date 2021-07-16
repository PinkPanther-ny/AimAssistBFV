from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext

ext_modules = [
    Extension("assist",  ["assist.py"]),
    Extension("aim_lib.aimer",  ["./aim_lib/aimer.py"]),
    Extension("aim_lib.BFV",  ["./aim_lib/BFV.py"]),
    Extension("aim_lib.bones",  ["./aim_lib/bones.py"]),
    Extension("aim_lib.helpers",  ["./aim_lib/helpers.py"]),
    Extension("aim_lib.keycodes",  ["./aim_lib/keycodes.py"]),
    Extension("aim_lib.MemAccess",  ["./aim_lib/MemAccess.py"]),
    Extension("aim_lib.offsets",  ["./aim_lib/offsets.py"]),
    Extension("aim_lib.PointerManager",  ["./aim_lib/PointerManager.py"]),
]

setup(
    name = 'MyProgram',
    cmdclass = {'build_ext': build_ext},
    ext_modules = ext_modules
)