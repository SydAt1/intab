#!/usr/bin/env python3
"""
chord_recognizer.py

Analyzes an audio file and outputs chord timestamps as JSON.
Uses librosa for audio analysis — works with Python 3.10+.

Usage:
    python chord_recognizer.py <audio_file> [--output chords.json]

Output JSON format:
    {
        "file": "song.mp3",
        "duration": 210.5,
        "chords": [
            {"start": 0.0, "end": 1.6, "chord": "F:maj", "root": "F", "quality": "maj", "display": "F"},
            ...
        ]
    }
"""

import sys
import json
import argparse
import numpy as np
import librosa
from scipy.ndimage import uniform_filter1d

# Chord templates

NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

CHORD_TYPES = {
    "maj":  [0, 4, 7],
    "min":  [0, 3, 7],
    "7":    [0, 4, 7, 10],
    "maj7": [0, 4, 7, 11],
    "min7": [0, 3, 7, 10],
    "dim":  [0, 3, 6],
    "sus4": [0, 5, 7],
}

def _build_templates():
    templates, roots, qualities = [], [], []
    for root_idx, root in enumerate(NOTES):
        for quality, intervals in CHORD_TYPES.items():
            t = np.zeros(12)
            for iv in intervals:
                t[(root_idx + iv) % 12] = 1.0
            t /= t.sum()
            templates.append(t)
            roots.append(root)
            qualities.append(quality)
    return np.array(templates).T, roots, qualities

TMPL_MATRIX, TMPL_ROOTS, TMPL_QUALS = _build_templates()

QUALITY_DISPLAY = {
    "maj": "", "min": "m", "7": "7",
    "maj7": "maj7", "min7": "m7",
    "dim": "dim", "sus4": "sus4",
}

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def recognize_chords(filepath: str, segment_seconds: float = 0.5, hop_length: int = 4096):
    print(f"[*] Loading audio...", file=sys.stderr)
    y, sr = librosa.load(filepath, sr=None, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)
    print(f"[*] Duration: {duration:.2f}s | SR: {sr}Hz", file=sys.stderr)

    print("[*] Harmonic separation...", file=sys.stderr)
    y_harm = librosa.effects.harmonic(y, margin=4)

    print("[*] Computing chroma...", file=sys.stderr)
    chroma = librosa.feature.chroma_cqt(y=y_harm, sr=sr, hop_length=hop_length, bins_per_octave=36)

    # Smooth to reduce flickering
    frames_per_seg = max(1, int(segment_seconds * sr / hop_length))
    chroma_smooth = uniform_filter1d(chroma, size=frames_per_seg, axis=1)

    norms = chroma_smooth.sum(axis=0, keepdims=True)
    norms[norms == 0] = 1
    chroma_norm = chroma_smooth / norms

    scores = TMPL_MATRIX.T @ chroma_norm  # (n_templates, n_frames)
    best_idx = np.argmax(scores, axis=0)
    frame_times = librosa.frames_to_time(np.arange(chroma.shape[1]), sr=sr, hop_length=hop_length)

    # Merge consecutive identical chords
    chords = []
    prev_label = None
    seg_start = 0.0

    for i, idx in enumerate(best_idx):
        root = TMPL_ROOTS[idx]
        qual = TMPL_QUALS[idx]
        label = f"{root}:{qual}"

        if label != prev_label:
            if prev_label is not None:
                pr, pq = prev_label.split(":")
                chords.append({
                    "start":   round(seg_start, 3),
                    "end":     round(float(frame_times[i]), 3),
                    "chord":   prev_label,
                    "root":    pr,
                    "quality": pq,
                    "display": f"{pr}{QUALITY_DISPLAY.get(pq, pq)}",
                })
            seg_start = float(frame_times[i])
            prev_label = label

    if prev_label:
        pr, pq = prev_label.split(":")
        chords.append({
            "start":   round(seg_start, 3),
            "end":     round(duration, 3),
            "chord":   prev_label,
            "root":    pr,
            "quality": pq,
            "display": f"{pr}{QUALITY_DISPLAY.get(pq, pq)}",
        })

    return chords, duration

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Chord recognition → JSON")
    parser.add_argument("audio_file", help="Input audio (mp3, wav, flac, …)")
    parser.add_argument("--output", "-o", default=None, help="Output JSON file (default: stdout)")
    parser.add_argument("--segment", "-s", type=float, default=0.5,
                        help="Smoothing window in seconds (default: 0.5)")
    args = parser.parse_args()

    chords, duration = recognize_chords(args.audio_file, segment_seconds=args.segment)
    print(f"[*] {len(chords)} chord segments detected.", file=sys.stderr)

    result = {"file": args.audio_file, "duration": duration, "chords": chords}
    out = json.dumps(result, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(out)
        print(f"[*] Saved → {args.output}", file=sys.stderr)
    else:
        print(out)

if __name__ == "__main__":
    main()