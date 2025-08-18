from __future__ import annotations

from pathlib import Path
from typing import List, Optional, cast, Any

from csv_processor import SessionLogger, SLDLCSVProcessor


class SessionFacade:
    """Coordinates session logging and post-processing.

    Provides a minimal, UI-agnostic facade over SessionLogger and
    SLDLCSVProcessor so the UI code stays simple.
    """

    def __init__(self, log_directory: Path | str) -> None:
        self.log_directory: Path = Path(log_directory)
        self.logger: SessionLogger = SessionLogger(str(self.log_directory))
        self._processor: SLDLCSVProcessor = SLDLCSVProcessor()

    def start(self, tracks: List[str], source_type: str) -> bool:
        """Start a new session with the given tracks and source type."""
        result: Any = self.logger.start_session(tracks, source_type)
        return bool(result)

    def update_track_state(self, track: str, state: int, failure_reason: int = 0) -> bool:
        """Update the state of a specific track in the session log."""
        result: Any = self.logger.update_track_state(track, state, failure_reason)
        return bool(result)

    def mark_remaining_tracks_failed(self, failure_reason: int = 7) -> bool:
        """Mark all remaining tracks as failed with the given reason."""
        result: Any = self.logger.mark_remaining_tracks_failed(failure_reason)
        return bool(result)

    def get_log_path(self) -> str:
        """Get the path to the current session log file."""
        return self.logger.get_log_path()

    def log_exists(self) -> bool:
        """Check if the session log file exists."""
        return self.logger.log_exists()

    def finalize_and_prefer_processed(self, index_file_path: str) -> Optional[Path]:
        """Process sldl _index.csv into log.csv, delete initial session log if superseded.

        Returns the path to processed log.csv if successful, else None.
        """
        try:
            index_path = Path(index_file_path)
            if not index_path.exists():
                return None

            if self._processor.process_csv_file(str(index_path)):
                processed_log = index_path.parent / "log.csv"
                # Delete initial session log if present
                try:
                    if self.log_exists():
                        session_log = Path(self.get_log_path())
                        if session_log.exists():
                            session_log.unlink()
                except Exception:
                    # Non-fatal cleanup failure
                    pass
                return processed_log
        except Exception:
            return None

        return None

