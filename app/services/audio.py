import os
import tempfile

from app.config import settings

# pydub has issues with Python 3.13, so we handle it gracefully
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False


def get_audio_duration(file_path: str) -> float:
    """
    Get the duration of an audio file in seconds.
    Works with most common formats thanks to pydub.
    """
    if not PYDUB_AVAILABLE:
        # fallback: return 0 if pydub not available
        # in production you'd want ffprobe as an alternative
        return 0.0

    audio = AudioSegment.from_file(file_path)
    return len(audio) / 1000.0  # pydub uses milliseconds


def chunk_audio_file(file_path: str) -> list[str]:
    """
    Split a large audio file into smaller chunks for Whisper.

    Whisper has a 25MB limit and works best with ~10 minute chunks.
    Returns a list of paths to the temporary chunk files.
    """
    if not PYDUB_AVAILABLE:
        # can't chunk without pydub, just return the original file
        return [file_path]

    audio = AudioSegment.from_file(file_path)
    duration_ms = len(audio)
    chunk_duration_ms = settings.whisper_chunk_duration_minutes * 60 * 1000

    # if the file is short enough, no need to chunk
    if duration_ms <= chunk_duration_ms:
        return [file_path]

    chunks = []
    temp_dir = tempfile.mkdtemp()

    # split into chunks with a small overlap to avoid cutting words
    overlap_ms = 1000  # 1 second overlap
    start = 0
    chunk_num = 0

    while start < duration_ms:
        end = min(start + chunk_duration_ms, duration_ms)
        chunk = audio[start:end]

        # save chunk as mp3 for smaller file size
        chunk_path = os.path.join(temp_dir, f"chunk_{chunk_num}.mp3")
        chunk.export(chunk_path, format="mp3")
        chunks.append(chunk_path)

        chunk_num += 1
        # move start forward, but account for overlap
        start = end - overlap_ms if end < duration_ms else duration_ms

    return chunks


def cleanup_chunks(chunk_paths: list[str]):
    """Remove temporary chunk files after processing."""
    for path in chunk_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
            # also try to remove the temp directory if it's empty
            parent = os.path.dirname(path)
            if os.path.isdir(parent) and not os.listdir(parent):
                os.rmdir(parent)
        except OSError:
            # not a big deal if cleanup fails
            pass
