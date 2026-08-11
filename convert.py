import mido
import json
import os

# 1. SET YOUR MIDI FILE NAME HERE
midi_filename = "bad-apple.mid"

# 2. ACCURACY & PACING SETTINGS
IGNORE_DRUMS = True
IGNORE_BASS = True   
BASS_CUTOFF = 48     
MAX_PAUSE_MS = 2000  # ⏱️ Any silence longer than 2 seconds (2000ms) will be compressed!

try:
    mid = mido.MidiFile(midi_filename)
except FileNotFoundError:
    print(f"❌ Could not find '{midi_filename}'. Make sure it's in this folder!")
    exit()

raw_notes = []
tempo = 500000  
ticks_per_beat = mid.ticks_per_beat

def normalize_pitch(pitch):
    if IGNORE_BASS and pitch < BASS_CUTOFF:
        return -1
        
    while pitch < 60:
        pitch += 12
    while pitch > 74:
        pitch -= 12
    return pitch

def get_lanes_from_combo(combo_val):
    lanes = []
    if combo_val & 1: lanes.append("green")   
    if combo_val & 2: lanes.append("red")     
    if combo_val & 4: lanes.append("yellow")  
    if combo_val & 8: lanes.append("blue")    
    return lanes

print("🎧 Parsing MIDI data...")

for track in mid.tracks:
    track_time_ms = 0.0
    for msg in track:
        delta_ms = mido.tick2second(msg.time, ticks_per_beat, tempo) * 1000.0
        track_time_ms += delta_ms
        
        if msg.type == 'set_tempo':
            tempo = msg.tempo
            
        elif msg.type == 'note_on' and msg.velocity > 0:
            if IGNORE_DRUMS and hasattr(msg, 'channel') and msg.channel == 9:
                continue
                
            folded_pitch = normalize_pitch(msg.note)
            if folded_pitch == -1:
                continue 
                
            combo_val = folded_pitch - 59
            target_lanes = get_lanes_from_combo(combo_val)
            
            for lane in target_lanes:
                raw_notes.append({
                    "time": int(track_time_ms + 2000), 
                    "lane": lane
                })

# 3. DE-DUPLICATION PASS
print("🧹 Cleaning up overlapping notes...")
unique_notes = []
seen = set()

for n in raw_notes:
    time_bucket = round(n['time'] / 50.0) * 50
    identifier = f"{time_bucket}-{n['lane']}"
    
    if identifier not in seen:
        seen.add(identifier)
        unique_notes.append(n)

unique_notes.sort(key=lambda x: x['time'])

# 4. ✂️ TIME COMPRESSION PASS (Squash long pauses)
print(f"⏱️ Compressing pauses longer than {MAX_PAUSE_MS}ms...")
compressed_notes = []
time_shift = 0.0

if len(unique_notes) > 0:
    # Keep the very first note exactly where it is
    compressed_notes.append(unique_notes[0])
    last_original_time = unique_notes[0]['time']
    
    for i in range(1, len(unique_notes)):
        current_original_time = unique_notes[i]['time']
        
        # Calculate the true gap between this note and the previous note
        gap = current_original_time - last_original_time
        
        if gap > MAX_PAUSE_MS:
            # If the gap is 5000ms, and max is 2000ms, we need to shift the future back by 3000ms
            time_shift += (gap - MAX_PAUSE_MS)
            
        # Apply the cumulative shift to the current note
        new_time = current_original_time - time_shift
        
        compressed_notes.append({
            "time": int(new_time),
            "lane": unique_notes[i]['lane']
        })
        
        last_original_time = current_original_time

chart_data = {
    "id": midi_filename.replace(".mid", "").lower().replace(" ", "-"),
    "title": midi_filename.replace(".mid", ""),
    "notes": compressed_notes
}

output_path = f"src/charts/{chart_data['id']}.json"
os.makedirs("src/charts", exist_ok=True)

with open(output_path, "w") as f:
    json.dump(chart_data, f, indent=2)

print(f"✅ Success! Chart saved to {output_path} (Cut {int(time_shift)}ms of dead air)")