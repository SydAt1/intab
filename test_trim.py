import asyncio
import librosa
from io import BytesIO
import soundfile as sf
import numpy as np

async def test():
    # generate a sine wave to act as random audio bytes
    sr = 22050
    t = np.linspace(0, 10, int(10 * sr)) # 10 seconds
    y = np.sin(2 * np.pi * 440 * t)
    
    out_io = BytesIO()
    sf.write(out_io, y, sr, format='WAV')
    raw_bytes = out_io.getvalue()
    
    # Trim to 2 seconds
    trim_start = 2.0
    trim_end = 4.0
    
    # emulate logic
    y2, sr2 = librosa.load(BytesIO(raw_bytes), sr=22050)
    start_sample = int(trim_start * sr2)
    end_sample = int(trim_end * sr2)
    y_trimmed = y2[start_sample:end_sample]
    
    out_io2 = BytesIO()
    sf.write(out_io2, y_trimmed, sr2, format='WAV')
    
    trimmed_len = len(y_trimmed) / sr2
    print(f"Original: {len(y)/sr}s, Trimmed: {trimmed_len}s")

asyncio.run(test())
