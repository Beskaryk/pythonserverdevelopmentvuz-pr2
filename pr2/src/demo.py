"""Три MP4 с разными аудиодорожками для демонстрации."""

import subprocess
import sys
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

DIRECTORY = Path(__file__).parents[1] / "data" / "examples"
FREQUENCIES = (440, 550, 660)


def make_sample(path, frequency):
    """Создать короткое видео с тестовым звуком."""
    subprocess.run([
        get_ffmpeg_exe(), "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=black:s=160x120:r=25",
        "-f", "lavfi", "-i", f"sine=frequency={frequency}",
        "-t", "1", "-c:v", "mpeg4", "-c:a", "aac", str(path),
    ], check=True)


def main():
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    for index, frequency in enumerate(FREQUENCIES, start=1):
        source = DIRECTORY / f"sample-{index}.mp4"
        output = source.with_suffix(".mp3")
        make_sample(source, frequency)
        with source.open("rb") as video:
            subprocess.run([sys.executable, "-m", "pr2.src.converter",
                            "--output", str(output)], stdin=video, check=True)
        print(f"{source.name} -> {output}")


if __name__ == "__main__":
    main()
