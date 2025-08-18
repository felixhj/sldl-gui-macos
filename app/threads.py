from __future__ import annotations

import threading
from typing import Callable, Any, TypeVar

T = TypeVar('T')


def run_in_thread(target: Callable[..., T], name: str = "worker", *args: Any, **kwargs: Any) -> threading.Thread:
    """Start a daemon thread for background work and return it."""
    thread = threading.Thread(target=target, name=name, args=args, kwargs=kwargs, daemon=True)
    thread.start()
    return thread


def ui_dispatch(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Placeholder for UI main-thread dispatch.

    In PyObjC, replace this with performSelectorOnMainThread-based dispatch or
    NSThread utilities. Kept simple here to allow usage in tests without Cocoa.
    """
    return fn(*args, **kwargs)

