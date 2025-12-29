from __future__ import annotations

from typing import Any, Tuple, Protocol
try:
    # Import Cocoa types for alert helpers; safe in app runtime
    from Cocoa import NSAlert, NSAlertFirstButtonReturn
except Exception:
    NSAlert = None
    NSAlertFirstButtonReturn = 1


class UIDelegate(Protocol):
    """Protocol for UI delegate objects that support the required selectors."""
    def performSelectorOnMainThread_withObject_waitUntilDone_(self, selector: str, obj: Any, wait: bool) -> None: ...


def append_output(delegate: UIDelegate, text: str) -> None:
    """Append text to the output area."""
    try:
        delegate.performSelectorOnMainThread_withObject_waitUntilDone_(
            "appendOutput:", text, False
        )
    except Exception:
        # Best-effort; avoid crashing on UI dispatch errors
        pass


def update_status(delegate: UIDelegate, text: str) -> None:
    """Update the status text."""
    try:
        delegate.performSelectorOnMainThread_withObject_waitUntilDone_(
            "updateStatusText:", text, False
        )
    except Exception:
        pass


def switch_to_determinate(delegate: UIDelegate, max_steps: float) -> None:
    """Switch to determinate progress mode with the given maximum steps."""
    try:
        delegate.performSelectorOnMainThread_withObject_waitUntilDone_(
            "switchToDeterminateProgress:", max_steps, False
        )
    except Exception:
        pass


def update_progress_and_status(delegate: UIDelegate, step_and_status: Tuple[float, str]) -> None:
    """Update both progress and status text."""
    try:
        delegate.performSelectorOnMainThread_withObject_waitUntilDone_(
            "updateProgressAndStatus:", step_and_status, False
        )
    except Exception:
        pass


def reset_progress(delegate: UIDelegate) -> None:
    """Reset the progress indicator."""
    try:
        delegate.performSelectorOnMainThread_withObject_waitUntilDone_(
            "resetProgressIndicator", None, False
        )
    except Exception:
        pass


def enable_start_button(delegate: UIDelegate, enabled: bool) -> None:
    """Enable or disable the start button."""
    try:
        delegate.performSelectorOnMainThread_withObject_waitUntilDone_(
            "enableStartButton:", enabled, False
        )
    except Exception:
        pass


def show_info_alert(title: str, message: str) -> None:
    """Show an informational alert. Must be called on the main thread."""
    try:
        if NSAlert is None:
            return
        alert = NSAlert.alloc().init()
        alert.setMessageText_(title)
        alert.setInformativeText_(message)
        alert.addButtonWithTitle_("OK")
        # 1 = informational in legacy style enums
        try:
            alert.setAlertStyle_(1)
        except Exception:
            pass
        alert.runModal()
    except Exception:
        pass


def show_warning_alert(title: str, message: str) -> None:
    """Show a warning alert. Must be called on the main thread."""
    try:
        if NSAlert is None:
            return
        alert = NSAlert.alloc().init()
        alert.setMessageText_(title)
        alert.setInformativeText_(message)
        alert.addButtonWithTitle_("OK")
        try:
            alert.setAlertStyle_(2)  # warning
        except Exception:
            pass
        alert.runModal()
    except Exception:
        pass


def show_confirm_alert(title: str, message: str, ok_title: str = "OK", cancel_title: str = "Cancel") -> bool:
    """Show a confirmation alert and return True if OK/Confirm is pressed. Must be called on the main thread."""
    try:
        if NSAlert is None:
            return False
        alert = NSAlert.alloc().init()
        alert.setMessageText_(title)
        alert.setInformativeText_(message)
        # Add OK first, Cancel second; FirstButtonReturn means confirm
        alert.addButtonWithTitle_(ok_title)
        alert.addButtonWithTitle_(cancel_title)
        try:
            alert.setAlertStyle_(2)  # warning by default for confirms
        except Exception:
            pass
        response = alert.runModal()
        # Cast to int for comparison since we know it's a numeric response code
        try:
            response_int = int(response)
            return response_int == NSAlertFirstButtonReturn
        except (ValueError, TypeError):
            # If we can't convert to int, assume it's not the OK response
            return False
    except Exception:
        return False

