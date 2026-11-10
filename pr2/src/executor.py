"""Фоновое выполнение задач конвертации."""

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore
from uuid import uuid4

PENDING_LIMIT = 8
WORKER_TIMEOUT = 150


class JobQueue:
    """Один рабочий поток и ограниченная очередь задач."""

    def __init__(self, store, directory, clock, lock):
        self.store = store
        self.directory = directory
        self.clock = clock
        self.lock = lock
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.slots = BoundedSemaphore(PENDING_LIMIT)

    def submit(self, body, video):
        if not self.slots.acquire(blocking=False):
            return None
        try:
            command = create_command(self.store, body, "queued")
            self.pool.submit(self.run, command["identifier"], video)
        except Exception:
            self.slots.release()
            raise
        return command

    def run(self, identifier, video):
        try:
            with self.lock:
                self.store.update_command_state(identifier, "running")
            result = execute(video, self.directory)
            with self.lock:
                complete(self.store, self.clock, identifier, *result)
        finally:
            self.slots.release()


def create_command(store, body, state):
    return store.create_command(body.timestamp, body.content,
                                body.participant, state, body.enqueued)


def complete(store, clock, identifier, result, state, exception):
    output = store.create_output(int(clock()), result, state, exception,
                                 identifier)
    command = store.update_command_state(identifier, state)
    return {"command": command, "output": output}


def execute(video, directory):
    """Передать MP4 утилите первого этапа через стандартный ввод."""
    name = uuid4()
    destination = directory / f"{name}.mp3"
    try:
        subprocess.run(
            [sys.executable, "-m", "pr2.src.converter",
             "--output", str(destination)],
            input=video, capture_output=True, check=True,
            timeout=WORKER_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return "", "failed", "Не удалось извлечь аудио из MP4."
    return f"/audio/{name}", "done", ""
