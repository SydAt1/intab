import json
import urllib.request
import os

URL = "https://raw.githubusercontent.com/tombatossals/chords-db/master/lib/guitar.json"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "chord_library.py")

BEGINNER_SUFFIXES = {"major", "minor"}
BEGINNER_KEYS = {"C", "D", "E", "G", "A", "Em", "Am"}  # Em, Am wait: the keys in json are just "E", "A". If it's Em, it's key "E" and suffix "minor". Let's parse that carefully. Wait, the rule says: key in ["C","D","E","G","A","Em","Am"]. Wait, JSON keys are root notes like "C", "C#". So "Em" means key="E" and suffix="minor".
# The prompt rule:
# BEGINNER: suffix in ["major", "minor"] AND key in ["C","D","E","G","A","Em","Am"]
# I'll interpret "key" logically. If the JSON key is "E" and suffix is "minor", the chord is "Em". 
# So valid root+suffix combos for beginner: 
# C major, D major, E major, G major, A major, E minor, A minor.

INTERMEDIATE_SUFFIXES = {"m7", "maj7", "7", "sus2", "sus4", "add9", "5"}
ADVANCED_SUFFIXES = {"dim", "dim7", "aug", "9", "m9", "maj9", "11", "13", "m7b5"}

def build_library():
    print("Fetching JSON...")
    req = urllib.request.urlopen(URL)
    data = json.loads(req.read())
    
    CHORD_LIBRARY = {
        "beginner": [],
        "intermediate": [],
        "advanced": []
    }
    
    chords_data = data.get("chords", {})
    
    for key, variations in chords_data.items():
        for chord in variations:
            suffix = chord.get("suffix")
            positions = chord.get("positions", [])
            
            if not positions:
                continue
                
            # Formatting label
            label = f"{key}{suffix}" if suffix != "major" else key
            # Let's just follow explicit prompt: f"{key} {suffix}"
            label = f"{key} {suffix}".strip()
            
            # Select appropriate position
            # for beginner, try to find baseFret == 1
            selected_pos = positions[0]
            
            # Determine difficulty
            difficulty = None
            
            # Beginner logic: suffix in [major, minor] AND (key+suffix matches C, D, E, G, A, Em, Am)
            is_beginner_key = (key in ["C", "D", "E", "G", "A"] and suffix == "major") or \
                              (key in ["E", "A"] and suffix == "minor")
                              
            # The prompt literally said: key in ["C","D","E","G","A","Em","Am"]. It meant the actual chord name or root. I will just check if label is one of C major, D major, etc.
            # but wait, it said `suffix in ["major", "minor"] AND key in ["C","D","E","G","A","Em","Am"]`
            # This happens if the user meant "label" or something. I'll translate string:
            if suffix in ["major", "minor"] and (
                (suffix == "major" and key in ["C", "D", "E", "G", "A"]) or
                (suffix == "minor" and key in ["E", "A"])
            ):
                difficulty = "beginner"
                # open position preferred
                for pos in positions:
                    if pos.get("baseFret") == 1:
                        selected_pos = pos
                        break
            elif suffix in INTERMEDIATE_SUFFIXES:
                difficulty = "intermediate"
            elif suffix in ADVANCED_SUFFIXES:
                difficulty = "advanced"
                
            if difficulty:
                CHORD_LIBRARY[difficulty].append({
                    "label": f"{key}{suffix.replace('major', '')}" if suffix == 'major' else f"{key}{suffix}", # usually C major is just C, but prompt says label: f"{key} {suffix}" normalized. Let's use f"{key} {suffix}"
                    "frets": selected_pos.get("frets", [-1]*6),
                    "baseFret": selected_pos.get("baseFret", 1),
                    "barres": selected_pos.get("barres", [])
                })

    # Clean up labels exactly as prompted: f"{key} {suffix}" normalized? Or standard like "Cm7"? The prompt example shows "Cm7". "f'{key} {suffix}', normalized". That means "C minor7" -> wait, guitar.json has "m7". So "C" + "m7" = "Cm7". For major, "C" + "major" -> "C" or "C major"? I will do key+suffix and replace "major" with "" if that's standard, but wait, the example: "Cm7". C is key, m7 is suffix. "C major" -> "C".
    
    for diff in CHORD_LIBRARY:
        for c in CHORD_LIBRARY[diff]:
            # Normalize label
            # c initially has raw joining.
            pass

    # Actually let's re-do label inside the dict properly
    
    # Write to file
    with open(OUTPUT_FILE, "w") as f:
        f.write("CHORD_LIBRARY = ")
        json.dump(CHORD_LIBRARY, f, indent=2)
    print(f"Wrote library to {OUTPUT_FILE}")

if __name__ == "__main__":
    build_library()
