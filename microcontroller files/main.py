from machine import Pin, I2S, ADC
import time
import math
import array
import random
import json

# ---- CONSTANTS ----

frequencyMap = {
    1: 261.63,   # B1                  | C4 (Middle C)
    2: 277.18,   # B2                  | C#4 / Db4
    3: 293.66,   # B1 + B2             | D4
    4: 311.13,   # B3                  | D#4 / Eb4
    5: 329.63,   # B1 + B3             | E4
    6: 349.23,   # B2 + B3             | F4
    7: 369.99,   # B1 + B2 + B3        | F#4 / Gb4
    8: 392.00,   # B4                  | G4
    9: 415.30,   # B1 + B4             | G#4 / Ab4
    10: 440.00,  # B2 + B4             | A4
    11: 466.16,  # B1 + B2 + B4        | A#4 / Bb4
    12: 493.88,  # B3 + B4             | B4
    13: 523.25,  # B1 + B3 + B4        | C5 
    14: 554.37,  # B2 + B3 + B4        | C#5 / Db5
    15: 587.33   # B1 + B2 + B3 + B4   | D5
}

#Instrument Const
currentInstrument = 1

# Pins
WS_PIN = 2   # Word Select (LRC)  -> GP15 
SCK_PIN = 1  # Bit Clock (BCLK) -> GP14
SD_PIN = 0   # Serial Data (DIN)  -> GP13
VOL_PIN = 28 # Slide Potetiometer -> GP28
X_PIN_GYRO = 26
Y_PIN_GYRO = 27
LANE1_PIN = 16
LANE2_PIN = 17
LANE3_PIN = 18
LANE4_PIN = 19
BLUE_BUTTON_PIN = 20
RED_BUTTON_PIN = 21
GREEN_BUTTON_PIN = 22
LED_GUITAR = Pin(15, Pin.OUT)
LED_PIANO = Pin(14, Pin.OUT)
LED_8BIT = Pin(13, Pin.OUT) 

SAMPLE_RATE = 11025
NOTE_DURATION = 0.2

audio_out = I2S(
    0, #id for hardware
    sck=Pin(SCK_PIN), #serial clock pin
    ws=Pin(WS_PIN), # word select pin 
    sd=Pin(SD_PIN), #serial data pin
    mode=I2S.TX, # sets mode to transmit
    bits=16, # every audio sample 16 bits long, the square of bits is num of possible volume steps
    format=I2S.MONO, # mono means one channel
    rate=SAMPLE_RATE, # higher rate, more data but better sounding. aliasing happens here
    ibuf=20000 # how much meemory to set aside for sound in bytes
)

# --- VOLUME ----


volume_pot = ADC(VOL_PIN)

def get_volume(): #return volume as 0-1 value
    raw = volume_pot.read_u16()
    return raw / 65535 #1

def play_note(buffer): #scales note based on volume
    scaled = array.array("h", [0] * len(buffer))

    for i in range(len(buffer)):
        scaled[i] = int(buffer[i] * vol)

    audio_out.write(scaled)


# --- STRUMMING ----

x_axis = ADC(X_PIN_GYRO)   # VRx
y_axis = ADC(Y_PIN_GYRO)   # VRy
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
# -----------------------------

# LEDS 

def update_instrument_leds(instrument_num):
    # Turns the correct LED ON (1) and the others OFF (0)
    LED_GUITAR.value(1 if instrument_num == 1 else 0)
    LED_PIANO.value(1 if instrument_num == 2 else 0)
    LED_8BIT.value(1 if instrument_num == 3 else 0)

# Set the starting LED (Instrument 1)
update_instrument_leds(currentInstrument)

totalSamples = int(SAMPLE_RATE * NOTE_DURATION)

instrument_bank = {
    1: {}, # guitar
    2: {}, # piano
    3: {}  # 8bit
}

print(json.dumps({"log": "Generating instruments..."}))

for combo, freq in frequencyMap.items():
    buff_guitar = array.array("h", [0] * totalSamples)
    buff_piano = array.array("h", [0] * totalSamples)
    buff_8bit = array.array("h", [0] * totalSamples)
    
    # --- GUITAR SETUP (Karplus-Strong String Pluck) ---
    # We figure out how long the string needs to be based on the frequency
    string_length = max(1, int(SAMPLE_RATE / freq))
    
    # Fill the string with random noise (the pick striking the string)
    delay_line = [random.uniform(-1.0, 1.0) for _ in range(string_length)]
    ptr = 0
    
    for i in range(totalSamples):
        t = i / SAMPLE_RATE
        
        # 1. GUITAR MATH
        g_val = delay_line[ptr]
        next_ptr = (ptr + 1) % string_length
        delay_line[ptr] = (g_val + delay_line[next_ptr]) * 0.5 * 0.995 #type: ignore
        buff_guitar[i] = int(g_val * 4000)
        ptr = next_ptr
        
        # 2. 8-BIT MATH (Square Wave)
        s_val = math.sin(2 * math.pi * freq * t)
        sq_wave = 1.0 if s_val > 0 else -1.0
        sq_env = math.exp(-2.5 * t) 
        buff_8bit[i] = int(sq_wave * sq_env * 2000) 
        
        # 3. CLASSIC SYNTH MATH (Sine Wave)
        wave = math.sin(2 * math.pi * freq * t) + 0.3 * math.sin(2 * math.pi * (freq * 2) * t)
        synth_env = math.exp(-4.0 * t)
        buff_piano[i] = int(wave * synth_env * 4000)
        
    instrument_bank[1][combo] = buff_guitar
    instrument_bank[2][combo] = buff_piano
    instrument_bank[3][combo] = buff_8bit


print(json.dumps({"log": "Loading done"}))

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
            return self.prevActionTime 
        return None
    
    def checkPressSafe(self):
        if self.hitReady:
            self.hitReady = False
            print(self.name + " hit")
            return True
        return False

lane1 = Button(LANE1_PIN, "lane1", 1)
lane2 = Button(LANE2_PIN, "lane2", 2)
lane3 = Button(LANE3_PIN, "lane3", 4)
lane4 = Button(LANE4_PIN, "lane4", 8)

blueButton = Button(BLUE_BUTTON_PIN, "bluebutton", 0)
redButton = Button(RED_BUTTON_PIN, "redbutton", 0)
greenButton = Button(GREEN_BUTTON_PIN, "greenbutton", 0)

all_lanes = [lane1, lane2, lane3, lane4]

chordTimerRunning = False
chordStartTime = 0
chordWindowConst = 40

while True:
    vol = get_volume()  # inside the loop for real-time control

 ### STRUMMING ###
    x_val = x_axis.read_u16()
    y_val = y_axis.read_u16()
    sw_val = sw.value()
    
    direction = get_direction(x_val, y_val)


    #instrument change
    if blueButton.checkPress() is not None:
        currentInstrument = 1
        update_instrument_leds(currentInstrument)
        print(json.dumps({"type": "instrument", "value": 1, "name": "guitar"}))
    elif redButton.checkPress() is not None:
        currentInstrument = 2
        update_instrument_leds(currentInstrument)
        print(json.dumps({"type": "instrument", "value": 2, "name": "piano"}))
    elif greenButton.checkPress() is not None:
        currentInstrument = 3
        update_instrument_leds(currentInstrument)
        print(json.dumps({"type": "instrument", "value": 3, "name": "8bit"}))

    for lane in all_lanes:
        hit_time = lane.checkPress()

        ###strum detection
        strum = (direction == "UP" or direction == "DOWN") #True

        ###changed conditions for strum and hit_time to be separate, so that we can send button hit data instantly without waiting for strum
        if hit_time is not None:
            if strum == True:
            # --- NEW: SEND BUTTON DATA INSTANTLY ---
                data_packet = {
                    "type": "button_hit",
                    "button": lane.name,
                    "lane_value": lane.chordVal,
                    "timestamp": hit_time,
                    "volume": vol,           ### added volume to the data packet
                    "strum": strum            ### added strum to the data packet
            }
                print(json.dumps(data_packet))
            
            # (Still start the timer so the Pico knows to play local audio later)
                if not chordTimerRunning:
                    chordTimerRunning = True
                    chordStartTime = hit_time
    
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
            
            if comboVal in frequencyMap:
                returnFreq = frequencyMap[comboVal]
                hz_log = {
                    "type": "log",
                    "message": f"Hit {returnFreq} Hz (Combo {comboVal})",
                    "frequency": returnFreq
                }
                print(json.dumps(hz_log))
                play_note(instrument_bank[currentInstrument][comboVal]) ###CHANGED TO PLAY NOTE WITH VOLUME SCALING            
            chordTimerRunning = False
