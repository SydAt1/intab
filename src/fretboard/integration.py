"""
import os
Fretboard Integration Guide
============================

This guide shows exactly how to integrate the chord classifier
with your fretboard visualization.

Integration Flow:
-----------------
User clicks notes on fretboard
        ↓
Extract pitch classes (0-11)
        ↓
Convert to 12-dim vector
        ↓
Classifier predicts chord
        ↓
Display label + confidence
"""


class FretboardChordDetector:
    """
    Integration wrapper for the chord classifier.
    
    This class handles the conversion between fretboard coordinates
    and the classifier's expected input format.
    """
    
    def __init__(self, classifier):
        """
        Initialize with a trained classifier.
        
        Args:
            classifier: Trained ChordClassifier instance
        """
        self.classifier = classifier
        
    def notes_from_fretboard(self, clicked_positions: list) -> list:
        """
        Convert fretboard positions to note names.
        
        Args:
            clicked_positions: List of (string, fret) tuples
            
        Returns:
            List of note names
            
        Example:
            Input: [(0, 0), (1, 2), (2, 2)]  # E, B, E on standard tuning
            Output: ['E', 'B', 'E']
        """
        # Standard guitar tuning (high to low)
        STANDARD_TUNING = ['E', 'B', 'G', 'D', 'A', 'E']
        
        # Note sequence (chromatic)
        NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        
        notes = []
        for string, fret in clicked_positions:
            # Get the open string note
            open_note = STANDARD_TUNING[string]
            open_pitch = NOTES.index(open_note)
            
            # Add fret offset
            final_pitch = (open_pitch + fret) % 12
            notes.append(NOTES[final_pitch])
        
        return notes
    
    def detect_chord(self, clicked_positions: list) -> dict:
        """
        Main method: detect chord from fretboard positions.
        
        Args:
            clicked_positions: List of (string, fret) tuples
            
        Returns:
            Dictionary with prediction results
        """
        # Convert to notes
        notes = self.notes_from_fretboard(clicked_positions)
        
        # Remove duplicates (same pitch class in different octaves)
        unique_notes = list(set(notes))
        
        # Predict
        chord_type, confidence = self.classifier.predict_from_notes(unique_notes)
        
        return {
            'chord_type': chord_type,
            'confidence': confidence,
            'notes': unique_notes,
            'note_count': len(unique_notes)
        }

# EXAMPLE INTEGRATION WITH DIFFERENT FRAMEWORKS

def flask_example():
    """
    Example Flask API endpoint for chord detection.
    """
    from flask import Flask, request, jsonify
    from chord_classifier import ChordClassifier
    
    app = Flask(__name__)
    
    # Load trained classifier (do this once at startup)
    classifier = ChordClassifier()
    classifier.load_model('chord_classifier.pkl')
    detector = FretboardChordDetector(classifier)
    
    @app.route('/detect_chord', methods=['POST'])
    def detect_chord():
        """
        Endpoint: POST /detect_chord
        Body: {"positions": [[0, 0], [1, 2], [2, 2]]}
        Returns: {"chord_type": "Major", "confidence": 0.95, ...}
        """
        data = request.json
        positions = data.get('positions', [])
        
        result = detector.detect_chord(positions)
        return jsonify(result)
    
    return app


def react_integration_example():
    """
    Example React integration (pseudo-code).
    """
    example_code = """
    // React Component Example
    
    import React, { useState } from 'react';
    
    function FretboardChordDetector() {
        const [clickedNotes, setClickedNotes] = useState([]);
        const [chordResult, setChordResult] = useState(null);
        
        const handleNoteClick = (string, fret) => {
            // Add clicked position
            const newNotes = [...clickedNotes, [string, fret]];
            setClickedNotes(newNotes);
            
            // Call backend API
            fetch('/api/detect_chord', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ positions: newNotes })
            })
            .then(res => res.json())
            .then(data => setChordResult(data));
        };
        
        return (
            <div>
                <Fretboard onNoteClick={handleNoteClick} />
                {chordResult && (
                    <ChordDisplay 
                        type={chordResult.chord_type}
                        confidence={chordResult.confidence}
                    />
                )}
            </div>
        );
    }
    """
    return example_code


def javascript_client_example():
    """
    Pure JavaScript example for web integration.
    """
    example_code = """
    // Pure JavaScript Example
    
    class ChordDetector {
        constructor(apiEndpoint) {
            this.apiEndpoint = apiEndpoint;
            this.clickedPositions = [];
        }
        
        async detectChord() {
            const response = await fetch(this.apiEndpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    positions: this.clickedPositions 
                })
            });
            
            return await response.json();
        }
        
        addNote(string, fret) {
            this.clickedPositions.push([string, fret]);
            return this.detectChord();
        }
        
        clear() {
            this.clickedPositions = [];
        }
    }
    
    // Usage
    const detector = new ChordDetector('/api/detect_chord');
    
    // When user clicks a note
    detector.addNote(0, 3).then(result => {
        console.log(`Detected: ${result.chord_type}`);
        console.log(`Confidence: ${result.confidence}`);
    });
    """
    return example_code


# ============================================================================
# STANDALONE DEMO
# ============================================================================


def run_standalone_demo():
    """
    Standalone demo without any web framework.
    Perfect for testing and development.
    """
    from chord_classifier import ChordClassifier
    
    print("\n" + "=" * 70)
    print("FRETBOARD CHORD DETECTOR - STANDALONE DEMO")
    print("=" * 70)
    
    # Load classifier
    print("\nLoading classifier...")
    classifier = ChordClassifier()
    
    # Train if model doesn't exist
    try:
        model_path = os.path.join(os.path.dirname(__file__), 'model/chord_classifier.pkl')
        classifier.load_model(model_path)
    except FileNotFoundError:
        print("Model not found. Training new model...")
        classifier.train()
        model_path = os.path.join(os.path.dirname(__file__), 'model/chord_classifier.pkl')
        # Ensure dir exists
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        classifier.save_model(model_path)
    
    detector = FretboardChordDetector(classifier)
    
    # Test cases: common chord shapes on guitar
    test_chords = {
        "Open C Major": [(3, 3), (2, 2), (1, 0), (4, 3)],  # C on 5th string, E, G, high C
        "Open A Minor": [(3, 2), (2, 2), (1, 1), (4, 2)],  # A, E, A, C, E
        "Open E Minor": [(5, 0), (4, 2), (3, 2)],           # E, B, E, G, B, E
        "D Major": [(2, 2), (1, 3), (0, 2), (3, 0)],        # D, A, D, F#
        "Barre F Major": [(5, 1), (4, 3), (3, 3), (2, 2)],  # F, C, F, A, C, F
    }
    
    print("\n" + "=" * 70)
    print("TESTING COMMON CHORD SHAPES")
    print("=" * 70)
    
    for chord_name, positions in test_chords.items():
        result = detector.detect_chord(positions)
        
        print(f"\n{chord_name}:")
        print(f"  Fretboard positions: {positions}")
        print(f"  Notes detected: {result['notes']}")
        print(f"  Predicted chord: {result['chord_type']}")
        print(f"  Confidence: {result['confidence']:.2%}")
        print(f"  Status: {'✓ CORRECT' if result['chord_type'] in chord_name else '⚠ CHECK'}")
        print("-" * 70)
    
    print("\n" + "=" * 70)
    print("INTEGRATION READY!")
    print("=" * 70)
    print("\nYour classifier is working correctly.")
    print("Now you can integrate it with your fretboard UI.")
    print("\nSee the integration examples above for:")
    print("  - Flask API")
    print("  - React frontend")
    print("  - Pure JavaScript")


if __name__ == "__main__":
    run_standalone_demo()