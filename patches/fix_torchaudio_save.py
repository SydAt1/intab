"""
Monkey-patch torchaudio.save to use soundfile instead of torchcodec.

torchaudio >= 2.10 hardcodes torchcodec for save(), which requires CUDA
shared libraries (libnvrtc.so) that don't exist in CPU-only containers.
This patch replaces save() with a soundfile-based implementation so that
Demucs (which calls torchaudio.save internally) works on CPU.

Activated automatically via fix_torchaudio_save.pth in site-packages.
"""

try:
    import torchaudio
    import soundfile as sf

    def _soundfile_save(
        filepath, src, sample_rate,
        channels_first=True, format=None,
        encoding=None, bits_per_sample=-1,
        buffer_size=4096, compression=None, **kwargs
    ):
        import torch

        if isinstance(src, torch.Tensor):
            data = src.cpu().numpy()
        else:
            data = src

        # soundfile expects shape (samples, channels); torchaudio uses (channels, samples)
        if channels_first and data.ndim == 2:
            data = data.T

        subtype = "PCM_16"
        if bits_per_sample == 24:
            subtype = "PCM_24"
        elif bits_per_sample == 32:
            subtype = "PCM_32"

        sf.write(str(filepath), data, sample_rate, subtype=subtype)

    torchaudio.save = _soundfile_save

except ImportError:
    # torchaudio or soundfile not installed — nothing to patch
    pass
