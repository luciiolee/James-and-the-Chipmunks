from machine import ADC, Pin
import time

x_axis = ADC(26)   # VRx
y_axis = ADC(27)   # VRy
sw = Pin(22, Pin.IN, Pin.PULL_UP)


center_x = x_axis.read_u16()
center_y = y_axis.read_u16()
print("Calibrated center → X:", center_x, "Y:", center_y)

DEADZONE = 4000    # adjust if needed
prev_dir = None
prev_sw = sw.value()

def get_direction(x, y):
    dx = x - center_x
    dy = y - center_y

    if abs(dx) < DEADZONE and abs(dy) < DEADZONE:
        return "CENTER"
    if abs(dx) > abs(dy):
        if dx < -DEADZONE:
            return "UP"
        elif dx > DEADZONE:
            return "DOWN"
    #else:
    #    if dy < -DEADZONE:
    #        return "UP"
    #    elif dy > DEADZONE:
    #        return "DOWN"
    return "CENTER"

while True:
    x_val = x_axis.read_u16()
    y_val = y_axis.read_u16()
    sw_val = sw.value()

    direction = get_direction(x_val, y_val)

    if direction != "CENTER":
        print(direction)
        prev_dir = direction
        time.sleep(.35)

    if sw_val != prev_sw:
        if sw_val == 0:
            print("PRESS")
        else:
            print("RELEASE")
        prev_sw = sw_val

    #time.sleep(0.05)
