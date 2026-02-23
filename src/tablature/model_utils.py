import torch
import librosa
import numpy as np
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model", "best_crnn_fixed.pth")
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

import torch.nn as nn

class GuitarTabCRNN(nn.Module):
    def __init__(self, n_bins=96):
        super().__init__()
        self.cnn = nn.Sequential(
            nn.Conv2d(1, 64, (5,5), padding=(2,2)),
            nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d((2,1)),
            nn.Conv2d(64, 128, (5,5), padding=(2,2)),
            nn.BatchNorm2d(128), nn.ReLU(), nn.MaxPool2d((2,1)),
            nn.Conv2d(128, 256, (3,3), padding=(1,1)),
            nn.BatchNorm2d(256), nn.ReLU(), nn.MaxPool2d((2,1)),
            nn.Conv2d(256, 256, (3,3), padding=(1,1)),
            nn.BatchNorm2d(256), nn.ReLU(),
        )
        reduced = n_bins // 8
        self.rnn = nn.GRU(256 * reduced, 256, num_layers=2, bidirectional=True, batch_first=True, dropout=0.3)
        self.fc = nn.Linear(512, 150)

    def forward(self, x):
        b, _, _, t = x.shape
        x = self.cnn(x)
        x = x.permute(0, 3, 1, 2).contiguous().view(b, t, -1)
        x, _ = self.rnn(x)
        return self.fc(x)  # logits

def load_model():
    """Loads the CRNN model."""
    try:
        model = GuitarTabCRNN().to(device)
        
        if os.path.exists(MODEL_PATH):
            checkpoint = torch.load(MODEL_PATH, map_location=device, weights_only=False)
            
            # Handle both old (plain state_dict) and new (full dict) formats
            if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
                model.load_state_dict(checkpoint['model_state_dict'])
            else:
                # Old format: just the state_dict
                model.load_state_dict(checkpoint)
                
            model.eval()
            return model
        else:
            print(f"Model file not found at {MODEL_PATH}")
            return None
    except Exception as e:
        print(f"Error loading model: {e}")
        return None

def extract_features(audio_path, sr=44100, hop_length=512, n_bins=96, bins_per_octave=24):
    """
    Extracts CQT features from the audio file matching the training data logic.
    """
    y, _ = librosa.load(audio_path, sr=sr)
    
    cqt = np.abs(librosa.cqt(y, sr=sr, hop_length=hop_length, 
                             n_bins=n_bins, bins_per_octave=bins_per_octave))
    cqt_db = librosa.amplitude_to_db(cqt, ref=np.max)
    
    # (1, 1, n_bins, T) format required by model
    tensor = torch.tensor(cqt_db, dtype=torch.float32).unsqueeze(0).unsqueeze(0).to(device)
    
    time_per_frame = hop_length / sr
    return tensor, sr, time_per_frame

def predict_notes(model, audio_path, threshold=0.5, min_duration_sec=0.08):
    """
    Runs inference and converts model output to list of note dicts.
    Returns format: [{'string': 1-6, 'fret': 0-24, 'onset': float, 'duration': float}, ...]
    """
    features, sr, time_per_frame = extract_features(audio_path)
    
    if model is None:
        print("Model is not loaded. Returning dummy notes for demonstration.")
        return _get_dummy_notes()
        
    with torch.no_grad():
        try:
            logits = model(features).cpu().numpy().squeeze(0)  # (T, 150)
            probs = 1 / (1 + np.exp(-logits))  # sigmoid
            return _parse_predictions(probs, time_per_frame, threshold, min_duration_sec)
        except Exception as e:
            print(f"Inference failed (likely shape mismatch or missing CRNN logic): {e}")
            print("Returning dummy notes for demonstration.")
            return _get_dummy_notes()

def _get_dummy_notes():
    return [
        {'string': 1, 'fret': 0, 'onset': 0.5, 'duration': 0.5},
        {'string': 2, 'fret': 1, 'onset': 1.0, 'duration': 0.5},
        {'string': 3, 'fret': 2, 'onset': 1.5, 'duration': 0.5},
        {'string': 1, 'fret': 3, 'onset': 2.0, 'duration': 0.5},
        {'string': 5, 'fret': 3, 'onset': 2.5, 'duration': 0.5},
        {'string': 6, 'fret': 0, 'onset': 3.0, 'duration': 0.5},
    ]

def _parse_predictions(probs, time_per_frame, threshold=0.5, min_duration_sec=0.08):
    probs_3d = probs.reshape(-1, 6, 25)
    
    # Per-string: only strongest fret
    active_frets = np.argmax(probs_3d, axis=2)           # (T, 6)
    max_probs = np.max(probs_3d, axis=2)                 # (T, 6)
    mask = max_probs > threshold

    notes = []
    for s in range(6):
        prev_fret = -1
        start = -1
        for t in range(len(mask)):
            fret = active_frets[t, s] if mask[t, s] else -1
            if fret != prev_fret:
                if prev_fret != -1:
                    duration = (t - start) * time_per_frame
                    if duration >= min_duration_sec:
                        notes.append({
                            'string': s + 1,
                            'fret': int(prev_fret),
                            'onset': float(start * time_per_frame),
                            'duration': float(duration)
                        })
                if fret != -1:
                    start = t
                prev_fret = fret
        # Close final note
        if prev_fret != -1:
            duration = (len(mask) - start) * time_per_frame
            if duration >= min_duration_sec:
                notes.append({
                    'string': s + 1,
                    'fret': int(prev_fret),
                    'onset': float(start * time_per_frame),
                    'duration': float(duration)
                })

    return sorted(notes, key=lambda x: x['onset'])
