from collections import defaultdict

DEBUG = True
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

# FPS
fps_count = 60
max_fps = 60
fps_value_last_update_time = 0
# In seconds
fps_value_update_rate = 0.5

# For advanced aim assist
advanced_aim_on = True
engage_occluded_target = False

draw_soldier_name = True
