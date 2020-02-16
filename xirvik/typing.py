"""Typing helpers."""
from typing import TypeVar, Callable

__all__ = ("Method0", "Method1")

T = TypeVar('T')
U = TypeVar('U')
V = TypeVar('V')
Method0 = Callable[[T], V]
Method1 = Callable[[T, U], V]
