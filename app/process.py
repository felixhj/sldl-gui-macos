from __future__ import annotations

import os
import signal
import subprocess
import threading
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Protocol


class OutputCallback(Protocol):
    """Protocol for output callback functions."""
    def __call__(self, line: str) -> None: ...


class SldlRunner:
    """Encapsulates sldl process lifecycle.

    Responsibilities:
    - Build the sldl command line from inputs
    - Stream stdout lines to a callback (for UI append)
    - Support graceful stop with forced kill fallback
    """

    def __init__(
        self,
        sldl_path: Path | str,
        working_dir: Path | str,
        output_callback: Optional[OutputCallback] = None,
    ) -> None:
        self.sldl_path: str = str(sldl_path)
        self.working_dir: Path = Path(working_dir)
        self.output_callback: OutputCallback = output_callback or (lambda _line: None)
        self._process: Optional[subprocess.Popen[str]] = None
        self._reader_thread: Optional[threading.Thread] = None

    @property
    def process(self) -> Optional[subprocess.Popen[str]]:
        return self._process

    def build_command(self, args: Iterable[str]) -> List[str]:
        return [self.sldl_path, *list(args)]

    def start(self, args: Iterable[str]) -> None:
        if self._process is not None:
            raise RuntimeError("Process already started")

        cmd = self.build_command(args)
        self._process = subprocess.Popen(
            cmd,
            cwd=str(self.working_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        def _reader(proc: subprocess.Popen[str]) -> None:
            try:
                assert proc.stdout is not None
                for line in proc.stdout:
                    self.output_callback(line)
            finally:
                # Drain remaining output and close
                try:
                    if proc.stdout is not None:
                        proc.stdout.close()
                except Exception:
                    pass

        self._reader_thread = threading.Thread(target=_reader, args=(self._process,), name="sldl-stdout-reader", daemon=True)
        self._reader_thread.start()

    def stop(self, graceful_seconds: float = 5.0) -> None:
        """Attempt graceful stop (SIGINT) then force kill after timeout."""
        proc = self._process
        if proc is None or proc.poll() is not None:
            return

        try:
            # Prefer SIGINT to allow sldl to write index files
            if os.name == "posix":
                proc.send_signal(signal.SIGINT)
            else:
                proc.terminate()
        except Exception:
            pass

        try:
            proc.wait(timeout=graceful_seconds)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def wait(self) -> int:
        proc = self._process
        if proc is None:
            return 0
        return proc.wait()

