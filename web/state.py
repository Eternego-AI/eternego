"""Shared web state — imported by both app and routes without circular deps."""

active_threads: set[str] = set()
