"""Извлечение аудио из MP4."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from imageio_ffmpeg import get_ffmpeg_exe

CONVERSION_TIMEOUT = 120


def convert(source, destination):
    """Сохранить первую аудиодорожку в MP3."""
    command = [
        get_ffmpeg_exe(), "-nostdin", "-y", "-loglevel", "error",
        "-f", "mov", "-enable_drefs", "0", "-i", str(source),
        "-map", "0:a:0", "-vn", "-c:a", "libmp3lame",
        "-f", "mp3", str(destination),
    ]
    subprocess.run(command, check=True, capture_output=True,
                   timeout=CONVERSION_TIMEOUT)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    output = parser.parse_args().output
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with TemporaryDirectory(dir=output.parent) as directory:
            source = Path(directory) / "input.mp4"
            result = Path(directory) / "audio.mp3"
            with source.open("wb") as file:
                shutil.copyfileobj(sys.stdin.buffer, file)
            convert(source, result)
            result.replace(output)
    except (OSError, RuntimeError, subprocess.SubprocessError):
        parser.exit(1, "Cannot extract MP3 from this MP4.\n")


if __name__ == "__main__":
    main()
