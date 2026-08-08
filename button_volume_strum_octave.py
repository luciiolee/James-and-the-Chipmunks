from machine import Pin, I2S, ADC
import time
import math
import array

frequencyMap = {
    1: 261,   # B1 only (e.g., C4)
    2: 293,   # B2 only (e.g., D4)
    3: 329,   # B1 + B2 (1+2=3) (e.g., E4)
    4: 349,   # B3 only (e.g., F4)
    5: 392,   # B1 + B3 (1+4=5)
    6: 440,   # B2 + B3 (2+4=6)
    7: 493,   # B1 + B2 + B3 (1+2+4=7)
    8: 523,   # B4 only (e.g., C5)
    9: 587,   # B1 + B4 (1+8=9)
    10: 659,  # B2 + B4 (2+8=10)
    11: 698,  # B1 + B2 + B4 (1+2+8=11)
    12: 783,  # B3 + B4 (4+8=12)
    13: 880,  # B1 + B3 + B4 (1+4+8=13)
    14: 987,  # B2 + B3 + B4 (2+4+8=14)
    15: 1046  # All 4 Buttons (1+2+4+8=15)
}
SCK_PIN = 13  # Bit Clock (BCLK) -> GP13
WS_PIN = 14   # Word Select (LRC)  -> GP14 (13 + 1)
SD_PIN = 15   # Serial Data (DIN)  -> GP15
SAMPLE_RATE = 11025
NOTE_DURATION = 0.7

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
# PLAY NOTE WITH VOLUME
# -----------------------------
def play_note(buffer):
    vol = get_volume()
    scaled = array.array("h", [0] * len(buffer))

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

DEADZONE = 2000
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


noteCache = {}
totalSamples = int(SAMPLE_RATE * NOTE_DURATION)

for combo, freq in frequencyMap.items():
    buffer = array.array("h", [0] * totalSamples)
    for i in range(totalSamples):
        t = i / SAMPLE_RATE
        # Rich harmonic waveform + exponential decay envelope
        wave = math.sin(2 * math.pi * freq * t) + 0.3 * math.sin(2 * math.pi * (freq * 2) * t)
        envelope = math.exp(-3.0 * t) 
        buffer[i] = int(wave * envelope * 16383)
    noteCache[combo] = buffer

print("loading done")
#_thread.start_new_thread(audioSynthThread, ())

class Button:
    def __init__(self, pinNum, name, chordVal):
        self.pin = Pin(pinNum, Pin.IN, Pin.PULL_UP)
        self.name = name
        self.pressCount = 0 #debugging
        self.chordVal = chordVal

        self.debounceConst = 20
        self.hitTime = 0
        self.prevActionTime = 0
        
        self.hitReady = False
        self.isPressed = True if self.pin.value() == 0 else False
    
        print(self.name + "initalized")
        self.pin.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self.isrHandler)

    def isrHandler(self, pin):
        currentTime = time.ticks_ms()
        currentState = pin.value()
        if currentState == 0 and not self.isPressed:
            if time.ticks_diff(currentTime, self.prevActionTime) > self.debounceConst:
                self.isPressed = True
                self.prevActionTime = currentTime
                self.hitReady = True

        elif currentState == 1 and self.isPressed:
            self.isPressed = False
            self.prevActionTime = currentTime

    def checkPress(self):
        if self.hitReady:
            self.hitReady = False
            print(self.name + " hit")
            return True
        return False

lane1 = Button(16, "lane1", 1)
lane2 = Button(17, "lane2", 2)
lane3 = Button(18, "lane3", 4)
lane4 = Button(19, "lane4", 8)

blueButton = Button(20, "lane4", 0)
RedButton = Button(21, "lane4", 0)
GreenButton = Button(22, "lane4", 0)

all_lanes = [lane1, lane2, lane3, lane4]

chordTimerRunning = False
chordStartTime = 0
chordWindowConst = 40

while True:

    ### STRUMMING ###
    x_val = x_axis.read_u16()
    y_val = y_axis.read_u16()
    sw_val = sw.value()
    
    direction = get_direction(x_val, y_val)
    

    ### BUTTON PRESS ###
    for lane in all_lanes:
        if (direction == "UP" or direction == "DOWN") and lane.checkPress():
            if not chordTimerRunning:
                chordTimerRunning = True
                chordStartTime = time.ticks_ms()
                print("Volume:", get_volume())
                print("STRUM:", direction)
    #### CHORD TIMER ###
    if chordTimerRunning:
        currentTime = time.ticks_ms()
        if time.ticks_diff(currentTime, chordStartTime) > chordWindowConst:
            comboVal = 0
            if lane1.isPressed:
                comboVal += 1
            if lane2.isPressed:
                comboVal += 2
            if lane3.isPressed:
                comboVal += 4
            if lane4.isPressed:
                comboVal += 8
            
            if comboVal in noteCache:
                returnFreq = frequencyMap[comboVal]
                print("Hit " + str(returnFreq) + " Hz")
                play_note(noteCache[comboVal])         ## changed to play_note(noteCache[comboVal]) to play the note with volume scaling    
            chordTimerRunning = False
            print(comboVal)
        