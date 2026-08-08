from machine import Pin, I2S
import time
import math
import array
import random
import _thread
import json

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

#instrument setting
currentInstrument = 1
            
SCK_PIN = 14  # Bit Clock (BCLK) -> GP14
WS_PIN = 15   # Word Select (LRC)  -> GP15 (14 + 1)
SD_PIN = 13   # Serial Data (DIN)  -> GP13
SAMPLE_RATE = 11025
NOTE_DURATION = 0.2

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
            # Return the exact hardware timestamp instead of just 'True'
            return self.prevActionTime 
        return None
    
    def checkPressSafe(self):
        if self.hitReady:
            self.hitReady = False
            print(self.name + " hit")
            return True
        return False

lane1 = Button(16, "lane1", 1)
lane2 = Button(17, "lane2", 2)
lane3 = Button(18, "lane3", 4)
lane4 = Button(19, "lane4", 8)

blueButton = Button(20, "bluebutton", 0)
redButton = Button(21, "redbutton", 0)
greenButton = Button(22, "greenbutton", 0)

all_lanes = [lane1, lane2, lane3, lane4]

chordTimerRunning = False
chordStartTime = 0
chordWindowConst = 40

while True:
    #instrument change
    if blueButton.checkPress() is not None:
        currentInstrument = 1
        print(json.dumps({"type": "instrument", "value": 1, "name": "guitar"}))
    elif redButton.checkPress() is not None:
        currentInstrument = 2
        print(json.dumps({"type": "instrument", "value": 2, "name": "piano"}))
    elif greenButton.checkPress() is not None:
        currentInstrument = 3
        print(json.dumps({"type": "instrument", "value": 3, "name": "8bit"}))

    for lane in all_lanes:
        hit_time = lane.checkPress()
        
        if hit_time is not None:
            # --- NEW: SEND BUTTON DATA INSTANTLY ---
            data_packet = {
                "type": "button_hit",
                "button": lane.name,
                "lane_value": lane.chordVal,
                "timestamp": hit_time
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
                audio_out.write(instrument_bank[currentInstrument][comboVal])            
            chordTimerRunning = False
