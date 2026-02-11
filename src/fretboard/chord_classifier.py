import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Tuple, Dict
import pickle


class ChordDataGenerator:
    """
    Generates synthetic training data for chord classification.
    
    This is NOT fake data - it's a systematic enumeration of the chord space
    based on music theory rules.
    """
    
    # Music theory constants
    PITCH_CLASSES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    # Chord interval formulas (in semitones from root)
    CHORD_INTERVALS = {
        'Major': [0, 4, 7],
        'Minor': [0, 3, 7],
        'Diminished': [0, 3, 6],
        'Augmented': [0, 4, 8]
    }
    
    def __init__(self, include_variations: bool = True, variations_per_chord: int = 50):
        """
        Initialize the chord data generator.
        
        Args:
            include_variations: Whether to generate realistic variations
            variations_per_chord: Number of variations to generate per base chord
        """
        self.include_variations = include_variations
        self.variations_per_chord = variations_per_chord
        self.data = []
        self.labels = []
        
    def pitch_class_to_vector(self, pitch_classes: List[int]) -> np.ndarray:
        """
        Convert a list of pitch classes to a 12-dimensional binary vector.
        
        Args:
            pitch_classes: List of integers (0-11) representing active pitch classes
            
        Returns:
            12-dimensional binary vector
            
        Example:
            [0, 4, 7] (C major) -> [1,0,0,0,1,0,0,1,0,0,0,0]
        """
        vector = np.zeros(12, dtype=int)
        for pc in pitch_classes:
            vector[pc % 12] = 1
        return vector
    
    def generate_base_chord(self, root: int, chord_type: str) -> np.ndarray:
        """
        Generate a base chord vector from root and type.
        
        Args:
            root: Root note (0-11, where 0=C)
            chord_type: One of 'Major', 'Minor', 'Diminished', 'Augmented'
            
        Returns:
            12-dimensional pitch class vector
        """
        intervals = self.CHORD_INTERVALS[chord_type]
        pitch_classes = [(root + interval) % 12 for interval in intervals]
        return self.pitch_class_to_vector(pitch_classes)
    
    def generate_variation(self, base_vector: np.ndarray, variation_type: str = 'random') -> np.ndarray:
        """
        Generate a realistic variation of a base chord.
        
        This simulates real-world scenarios:
        - Incomplete voicings (missing notes)
        - Doubled notes (same pitch class in different octaves - no change in vector)
        - Slight errors or additional notes
        
        Args:
            base_vector: Original chord vector
            variation_type: Type of variation to apply
            
        Returns:
            Modified chord vector
        """
        vector = base_vector.copy()
        active_notes = np.where(vector == 1)[0]
        
        if variation_type == 'random':
            variation_type = np.random.choice(['drop_note', 'add_noise', 'none'], 
                                             p=[0.3, 0.1, 0.6])
        
        if variation_type == 'drop_note' and len(active_notes) > 2:
            # Drop one note (simulate incomplete voicing)
            # Keep at least 2 notes for meaningful classification
            note_to_drop = np.random.choice(active_notes)
            vector[note_to_drop] = 0
            
        elif variation_type == 'add_noise':
            # Add one random pitch class (simulate error or extension)
            # Low probability to keep dataset mostly clean
            inactive_notes = np.where(vector == 0)[0]
            if len(inactive_notes) > 0:
                note_to_add = np.random.choice(inactive_notes)
                vector[note_to_add] = 1
        
        # 'none' returns the vector unchanged
        return vector
    
    def generate_dataset(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate the complete synthetic dataset.
        
        Returns:
            X: Feature matrix (N x 12)
            y: Label vector (N,)
        """
        self.data = []
        self.labels = []
        
        print("Generating synthetic chord dataset...")
        print(f"Chord types: {list(self.CHORD_INTERVALS.keys())}")
        print(f"Roots: {len(self.PITCH_CLASSES)}")
        
        # Generate base chords
        for chord_type in self.CHORD_INTERVALS.keys():
            for root in range(12):  # All 12 roots
                # Create specific label (e.g., "C Major")
                root_name = self.PITCH_CLASSES[root]
                label = f"{root_name} {chord_type}"
                
                base_vector = self.generate_base_chord(root, chord_type)
                
                # Add the perfect base chord
                self.data.append(base_vector)
                self.labels.append(label)
                
                # Generate variations if enabled
                if self.include_variations:
                    for _ in range(self.variations_per_chord):
                        variation = self.generate_variation(base_vector)
                        self.data.append(variation)
                        self.labels.append(label)
        
        X = np.array(self.data)
        y = np.array(self.labels)
        
        print(f"\nDataset generated:")
        print(f"  Total samples: {len(X)}")
        print(f"  Features: {X.shape[1]} (pitch class binary vector)")
        print(f"  Classes: {len(np.unique(y))}")
        print(f"  Class distribution:")
        unique, counts = np.unique(y, return_counts=True)
        for label, count in zip(unique, counts):
            print(f"    {label}: {count}")
        
        return X, y
    
    def vector_to_notes(self, vector: np.ndarray) -> List[str]:
        """
        Convert a pitch class vector back to note names.
        
        Args:
            vector: 12-dimensional binary vector
            
        Returns:
            List of note names
        """
        return [self.PITCH_CLASSES[i] for i in range(12) if vector[i] == 1]


class ChordClassifier:
    """
    Main chord classification system.
    
    Uses a simple, interpretable ML model (not deep learning - that would be overkill)
    trained on synthetically generated data.
    """
    
    def __init__(self, model_type: str = 'random_forest'):
        """
        Initialize the classifier.
        
        Args:
            model_type: One of 'random_forest', 'logistic', 'svm'
        """
        self.model_type = model_type
        self.model = self._create_model(model_type)
        self.generator = ChordDataGenerator()
        self.is_trained = False
        
    def _create_model(self, model_type: str):
        """Create the appropriate sklearn model."""
        models = {
            'random_forest': RandomForestClassifier(n_estimators=100, random_state=42),
            'logistic': LogisticRegression(max_iter=1000, random_state=42),
            'svm': SVC(kernel='rbf', random_state=42, probability=True)
        }
        
        if model_type not in models:
            raise ValueError(f"Unknown model type: {model_type}. Choose from {list(models.keys())}")
        
        return models[model_type]
    
    def train(self, test_size: float = 0.2):
        """
        Train the classifier on synthetic data.
        
        Args:
            test_size: Proportion of data to use for testing
        """
        print(f"\nTraining {self.model_type} classifier...")
        print("=" * 60)
        
        # Generate dataset
        X, y = self.generator.generate_dataset()
        
        # Split into train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        print(f"\nTrain samples: {len(X_train)}")
        print(f"Test samples: {len(X_test)}")
        
        # Train
        self.model.fit(X_train, y_train)
        self.is_trained = True
        
        # Evaluate
        print("\n" + "=" * 60)
        print("EVALUATION RESULTS")
        print("=" * 60)
        
        y_pred_train = self.model.predict(X_train)
        y_pred_test = self.model.predict(X_test)
        
        train_acc = accuracy_score(y_train, y_pred_train)
        test_acc = accuracy_score(y_test, y_pred_test)
        
        print(f"\nTrain Accuracy: {train_acc:.4f}")
        print(f"Test Accuracy:  {test_acc:.4f}")
        
        print("\n" + "-" * 60)
        print("Classification Report (Test Set):")
        print("-" * 60)
        print(classification_report(y_test, y_pred_test))
        
        # Confusion matrix
        # Generate all expected labels
        all_labels = []
        for chord_type in self.generator.CHORD_INTERVALS.keys():
            for root_idx in range(12):
                root_name = self.generator.PITCH_CLASSES[root_idx]
                all_labels.append(f"{root_name} {chord_type}")
        
        cm = confusion_matrix(y_test, y_pred_test, labels=all_labels)
        
        self._plot_confusion_matrix(cm, all_labels)
        
        return train_acc, test_acc
    
    def _plot_confusion_matrix(self, cm: np.ndarray, labels: List[str]):
        """Plot and save confusion matrix."""
        # Increase size for 48x48 matrix
        plt.figure(figsize=(24, 20))
        sns.heatmap(cm, annot=False, fmt='d', cmap='Blues',
                   xticklabels=labels, yticklabels=labels)
        plt.title('Confusion Matrix - Chord Classification')
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')
        plt.xticks(rotation=90)
        plt.yticks(rotation=0)
        plt.tight_layout()
        output_path = os.path.join(os.path.dirname(__file__), 'visualizations/confusion_matrix.png')
        if not os.path.exists(os.path.dirname(output_path)):
            os.makedirs(os.path.dirname(output_path))
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"\n✓ Confusion matrix saved to: {output_path}")
    
    def predict(self, pitch_classes: List[int]) -> Tuple[str, float]:
        """
        Predict chord type from active pitch classes.
        
        Args:
            pitch_classes: List of active pitch classes (0-11)
            
        Returns:
            Tuple of (predicted_chord_type, confidence)
        """
        if not self.is_trained:
            raise RuntimeError("Model must be trained before prediction. Call train() first.")
        
        # Convert to vector
        vector = self.generator.pitch_class_to_vector(pitch_classes).reshape(1, -1)
        
        # Predict
        prediction = self.model.predict(vector)[0]
        
        # Get confidence (probability)
        if hasattr(self.model, 'predict_proba'):
            probabilities = self.model.predict_proba(vector)[0]
            confidence = np.max(probabilities)
        else:
            confidence = 1.0  # SVM without probability
        
        return prediction, confidence
    
    def predict_from_notes(self, note_names: List[str]) -> Tuple[str, float]:
        """
        Predict chord type from note names.
        
        Args:
            note_names: List of note names (e.g., ['C', 'E', 'G'])
            
        Returns:
            Tuple of (predicted_chord_type, confidence)
        """
        # Convert note names to pitch classes
        pitch_classes = []
        for note in note_names:
            if note in self.generator.PITCH_CLASSES:
                pitch_classes.append(self.generator.PITCH_CLASSES.index(note))
        
        return self.predict(pitch_classes)
    
    def save_model(self, filepath: str):
        """Save the trained model to disk."""
        if not self.is_trained:
            raise RuntimeError("Cannot save untrained model.")
        
        with open(filepath, 'wb') as f:
            pickle.dump(self.model, f)
        print(f"\n✓ Model saved to: {filepath}")
    
    def load_model(self, filepath: str):
        """Load a trained model from disk."""
        with open(filepath, 'rb') as f:
            self.model = pickle.load(f)
        self.is_trained = True
        print(f"\n✓ Model loaded from: {filepath}")


def demonstrate_system():
    """
    Demonstrate the complete system with examples.
    """
    print("\n" + "=" * 60)
    print("CHORD CLASSIFICATION SYSTEM DEMONSTRATION")
    print("=" * 60)
    
    # Create and train classifier
    classifier = ChordClassifier(model_type='random_forest')
    classifier.train(test_size=0.2)
    
    # Test examples
    print("\n" + "=" * 60)
    print("EXAMPLE PREDICTIONS")
    print("=" * 60)
    
    test_cases = [
        (['C', 'E', 'G'], "C Major"),
        (['A', 'C', 'E'], "A Minor"),
        (['D', 'F', 'Ab'], "D Diminished (D-F-Ab)"),
        (['C', 'E', 'G#'], "C Augmented"),
        (['C', 'G'], "C Major (incomplete - missing E)"),
        (['C', 'E', 'G', 'B'], "C Major with added note"),
    ]
    
    print()
    for notes, description in test_cases:
        prediction, confidence = classifier.predict_from_notes(notes)
        print(f"Notes: {notes}")
        print(f"Description: {description}")
        print(f"Prediction: {prediction} (confidence: {confidence:.2%})")
        print("-" * 40)
    
    # Save model
    classifier.save_model(os.path.join(os.path.dirname(__file__), 'model/chord_classifier.pkl'))
    
    print("\n" + "=" * 60)
    print("SYSTEM READY FOR INTEGRATION")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Connect to your fretboard UI")
    print("2. Extract pitch classes from clicked notes")
    print("3. Call classifier.predict(pitch_classes)")
    print("4. Display result to user")


if __name__ == "__main__":
    demonstrate_system()