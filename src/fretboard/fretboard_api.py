from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import sys
import os

from src.filter.auth_filter import require_login

# Add parent directory to path to import chord_classifier
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from fretboard.chord_classifier import ChordClassifier

# Initialize router with auth dependency
router = APIRouter(prefix="", tags=["Chord Classification"])

# Load model at module import (singleton pattern)
print("Loading chord classification model...")
classifier = ChordClassifier(model_type='random_forest')

try:
    model_path = os.path.join(os.path.dirname(__file__), 'model/chord_classifier.pkl')
    classifier.load_model(model_path)
    print("✓ Chord classifier model loaded successfully!")
except FileNotFoundError:
    print("⚠ Model not found. Training new model...")
    classifier.train()
    classifier.save_model(model_path)
    print("✓ Model trained and saved!")


# Request/Response Models
class ChordDetectionRequest(BaseModel):
    """Request model for chord detection from note names"""
    notes: List[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "notes": ["C", "E", "G"]
            }
        }


class FretboardDetectionRequest(BaseModel):
    """Request model for chord detection from fretboard positions"""
    positions: List[List[int]]  # [[string, fret], [string, fret], ...]
    
    class Config:
        json_schema_extra = {
            "example": {
                "positions": [[0, 0], [1, 2], [2, 2]]
            }
        }


class ChordDetectionResponse(BaseModel):
    """Response model for chord detection"""
    chord_type: str
    confidence: float
    notes: List[str]
    note_count: int
    error: Optional[str] = None


class ModelInfoResponse(BaseModel):
    """Response model for model information"""
    model_type: str
    is_trained: bool
    supported_chords: List[str]
    pitch_classes: List[str]


# API Endpoints
@router.post("/chord/detect", response_model=ChordDetectionResponse, tags=["Chord Classification"])
async def detect_chord(request: ChordDetectionRequest):
    """
    Detect chord type from note names.
    
    - **notes**: List of note names (e.g., ["C", "E", "G"])
    - Returns: Chord type, confidence score, and detected notes
    
    Example:
        ```json
        {
            "notes": ["C", "E", "G"]
        }
        ```
    """
    try:
        if not request.notes:
            return ChordDetectionResponse(
                chord_type="-",
                confidence=0.0,
                notes=[],
                note_count=0,
                error="No notes provided"
            )
        
        # Remove duplicates (same pitch class in different octaves)
        unique_notes = list(set(request.notes))
        
        # Classify using ML model
        chord_type, confidence = classifier.predict_from_notes(unique_notes)
        
        return ChordDetectionResponse(
            chord_type=chord_type,
            confidence=float(confidence),
            notes=unique_notes,
            note_count=len(unique_notes)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chord classification failed: {str(e)}"
        )


@router.post("/chord/detect_positions", response_model=ChordDetectionResponse)
async def detect_chord_from_positions(request: FretboardDetectionRequest):
    """
    Detect chord type from fretboard positions.
    
    - **positions**: List of [string, fret] pairs (0-indexed)
    - Returns: Chord type, confidence score, and detected notes
    
    Example:
        ```json
        {
            "positions": [[0, 0], [1, 2], [2, 2]]
        }
        ```
    
    Guitar tuning: E B G D A E (standard, high to low)
    """
    try:
        if not request.positions:
            return ChordDetectionResponse(
                chord_type="-",
                confidence=0.0,
                notes=[],
                note_count=0,
                error="No positions provided"
            )
        
        # Guitar configuration (standard tuning, high to low)
        TUNING = ['E', 'B', 'G', 'D', 'A', 'E']
        NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        
        # Convert fretboard positions to note names
        notes = []
        for position in request.positions:
            if len(position) != 2:
                continue
            
            string, fret = position
            
            # Validate position
            if not (0 <= string < len(TUNING) and fret >= 0):
                continue
            
            # Calculate note
            open_note = TUNING[string]
            open_pitch = NOTES.index(open_note)
            final_pitch = (open_pitch + fret) % 12
            notes.append(NOTES[final_pitch])
        
        # Remove duplicates
        unique_notes = list(set(notes))
        
        if not unique_notes:
            return ChordDetectionResponse(
                chord_type="-",
                confidence=0.0,
                notes=[],
                note_count=0,
                error="Invalid fretboard positions"
            )
        
        # Classify using ML model
        chord_type, confidence = classifier.predict_from_notes(unique_notes)
        
        return ChordDetectionResponse(
            chord_type=chord_type,
            confidence=float(confidence),
            notes=unique_notes,
            note_count=len(unique_notes)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chord classification failed: {str(e)}"
        )


@router.get("/chord/model_info", response_model=ModelInfoResponse)
async def get_model_info():
    """
    Get information about the loaded chord classification model.
    
    Returns model type, training status, and supported chord types.
    """
    try:
        return ModelInfoResponse(
            model_type=classifier.model_type,
            is_trained=classifier.is_trained,
            supported_chords=list(classifier.generator.CHORD_INTERVALS.keys()),
            pitch_classes=classifier.generator.PITCH_CLASSES
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get model info: {str(e)}"
        )


@router.get("/chord/health")
async def chord_classifier_health():
    """
    Health check for the chord classification service.
    
    Returns status and model loading state.
    """
    return {
        "status": "healthy" if classifier.is_trained else "degraded",
        "service": "chord_classification",
        "model_loaded": classifier.is_trained,
        "model_type": classifier.model_type
    }