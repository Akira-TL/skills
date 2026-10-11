"""Stable Python API for the browser-access locked page session."""
from browser_runtime.session import BrowserSession, TargetLock, locked_page, origin, serve_session

__all__ = ["BrowserSession", "TargetLock", "locked_page", "origin", "serve_session"]
