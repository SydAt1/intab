import random

# We import the generated CHORD_LIBRARY
try:
    from .chord_library import CHORD_LIBRARY
except ImportError:
    CHORD_LIBRARY = {"beginner": [], "intermediate": [], "advanced": []}

def get_question(difficulty: str) -> dict:
    # returns { chord, options }
    tier_chords = CHORD_LIBRARY.get(difficulty, [])
    if not tier_chords:
        # Fallback if library empty
        return {"chord": {}, "options": []}

    target = random.choice(tier_chords)
    
    # Generate 3 distractor labels
    # ensure no duplicates
    options_set = {target["label"]}
    while len(options_set) < 4:
        cand = random.choice(tier_chords)["label"]
        options_set.add(cand)
        
    options = list(options_set)
    random.shuffle(options)
    
    return {
        "chord": target,
        "options": options
    }

def evaluate_answer(answer: str, correct_label: str) -> bool:
    return answer.strip().lower() == correct_label.strip().lower()

def next_difficulty(current: str, correct: bool, streak: int) -> str:
    if correct:
        if current == "intermediate" and streak >= 6:
            return "advanced"
        elif current == "beginner" and streak >= 3:
            return "intermediate"
    else:
        if current == "advanced":
            return "intermediate"
        elif current == "intermediate":
            return "beginner"
    
    return current

def score_delta(difficulty: str, correct: bool) -> int:
    if not correct:
        return 0
    
    points = {"beginner": 5, "intermediate": 10, "advanced": 20}
    return points.get(difficulty, 0)
