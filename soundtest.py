from machine import I2S, Pin
import math
import array
import time

# I2S Pin Setup
SCK_PIN = 13  # Bit Clock (BCLK) -> GP13
WS_PIN = 14   # Word Select (LRC)  -> GP14 (13 + 1)
SD_PIN = 15   # Serial Data (DIN)  -> GP15

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

def create_piano_note(frequency, duration_secs):
    total_samples = int(SAMPLE_RATE * duration_secs)
    buffer = array.array("h", [0] * total_samples)
    
    period = SAMPLE_RATE / frequency
    
    for i in range(total_samples):
        t = i / SAMPLE_RATE
        
        # 1. Waveform synthesis: Combine fundamental frequency + softer octave harmonic for a richer timber
        wave = math.sin(2 * math.pi * frequency * t) + 0.3 * math.sin(2 * math.pi * (frequency * 2) * t)
        
        # 2. Exponential Decay Envelope (Simulates a struck piano string fading out)
        # Fast drop-off initially, lingering quiet tail
        envelope = math.exp(-3.0 * t) 
        
        # Combine and scale to 16-bit signed audio range
        sample_val = int(wave * envelope * 16383) # Max 16383 to prevent clipping/distortion
        buffer[i] = sample_val
        
    return buffer

print("Generating piano-like strike...")

# Generate Middle C (261.63 Hz) that lasts for 1.5 seconds
c4_note = create_piano_note(261.63, 2)

# Play the sound cleanly through the MAX98357A
audio_out.write(c4_note)

print("Done playing.")