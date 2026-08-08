from machine import I2S, Pin, ADC
import math
import array
import time

# -----------------------------
# I2S AUDIO SETUP
# -----------------------------
SCK_PIN = 13
WS_PIN  = 14
SD_PIN  = 15

SAMPLE_RATE = 22050

audio_out = I2S(
    0,
    sck=Pin(SCK_PIN),
    ws=Pin(WS_PIN),
    sd=Pin(SD_PIN),
    mode=I2S.TX,
    bits=16,
    format=I2S.MONO,
    rate=SAMPLE_RATE,
    ibuf=20000
)

# -----------------------------
# VOLUME POT (use ADC28 instead of ADC27)
# -----------------------------
volume_pot = ADC(28)   # GP28 = ADC (safe, not shared with joystick)

def get_volume():
    raw = volume_pot.read_u16()
    return raw / 65535


# -----------------------------
# PRECOMPUTE NOTE (ONLY ONCE)
# -----------------------------
def create_piano_note(freq, duration):
    total = int(SAMPLE_RATE * duration)
    buf = array.array("h", [0] * total)

    for i in range(total):
        t = i / SAMPLE_RATE
        wave = (
            math.sin(2 * math.pi * freq * t)
            + 0.3 * math.sin(2 * math.pi * freq * 2 * t)
        )
        env = math.exp(-3.0 * t)
        buf[i] = int(wave * env * 16383)

    return buf

c4_note = create_piano_note(261.63, 2)

# Reusable scaled buffer (NO MORE MEMORY ERRORS)
scaled = array.array("h", [0] * len(c4_note))


# -----------------------------
# PLAY NOTE WITH VOLUME
# -----------------------------
def play_note(buffer):
    vol = get_volume()

    for i in range(len(buffer)):
        scaled[i] = int(buffer[i] * vol)

    audio_out.write(scaled)


# -----------------------------
# JOYSTICK SETUP
# -----------------------------
x_axis = ADC(26)   # VRx
y_axis = ADC(27)   # VRy
sw = Pin(22, Pin.IN, Pin.PULL_UP)

center_x = x_axis.read_u16()
center_y = y_axis.read_u16()

DEADZONE = 4000
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

    return "CENTER"


# -----------------------------
# MAIN LOOP
# -----------------------------
while True:
    x_val = x_axis.read_u16()
    y_val = y_axis.read_u16()
    sw_val = sw.value()

    direction = get_direction(x_val, y_val)

    # STRUM UP or DOWN
    if direction == "UP" or direction == "DOWN":
        print("Volume:", get_volume())
        print("STRUM:", direction)
        play_note(c4_note)
        time.sleep(0.25)   # debounce so it doesn't spam

    # BUTTON PRESS
    if sw_val != prev_sw:
        if sw_val == 0:
            print("PRESS")
        else:
            print("RELEASE")
        prev_sw = sw_val

    time.sleep(0.01)
