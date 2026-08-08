from machine import I2S, Pin, ADC
import math
import array
import time

# I2S Pin Setup
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

# --- NEW: Slide Potentiometer Volume Control (NEEDS TO BE CONNECTED TO 3V3 NOT 5V) ---
volume_pot = ADC(28)   # GP28 = ADC2 (safe, not shared with joystick)

def get_volume():
    """Return volume between 0.0 and 1.0 based on slide pot."""
    raw = volume_pot.read_u16()      # 0–65535
    return raw / 65535               # normalize

# ------------------------------------------------

def create_piano_note(frequency, duration_secs):
    total_samples = int(SAMPLE_RATE * duration_secs)
    buffer = array.array("h", [0] * total_samples)
    
    for i in range(total_samples):
        t = i / SAMPLE_RATE
        
        wave = (
            math.sin(2 * math.pi * frequency * t)
            + 0.3 * math.sin(2 * math.pi * (frequency * 2) * t)
        )
        
        envelope = math.exp(-3.0 * t)
        
        sample_val = int(wave * envelope * 16383)
        buffer[i] = sample_val
        
    return buffer

print("Generating piano-like strike...")

c4_note = create_piano_note(261.63, 2)

# --- NEW: Apply volume from slide pot before playback ---
def play_with_volume(buffer):
    """Scale each sample by live volume and stream to I2S."""
    scaled = array.array("h", [0] * len(buffer))

    vol = get_volume()  # read pot once per note
    print("Volume:", vol)

    for i in range(len(buffer)):
        scaled[i] = int(buffer[i] * vol)

    audio_out.write(scaled)

# Play note with real-time volume control on strum

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


    if direction == "DOWN" or direction == "UP":
        play_with_volume(c4_note)

        print("Done playing.")
