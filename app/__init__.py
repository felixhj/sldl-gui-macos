"""Application support modules for sldl-gui.

This package contains non-UI logic extracted from the main Cocoa app to
improve testability, readability, and maintainability. Modules are designed to
be imported independently without requiring PyObjC.
"""

__all__: list[str] = [
    "settings",
    "process", 
    "session",
    "playlist",
    "wishlist",
    "threads",
    "constants",
    "ui_helpers",
]

