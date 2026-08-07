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

# --- NEW: Slide Potentiometer Volume Control ---
volume_pot = ADC(26)   # GP26 = ADC0

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

# Play note with real-time volume control
play_with_volume(c4_note)

print("Done playing.")
