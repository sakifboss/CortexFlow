"""Generic pagination helpers shared by all list endpoints."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: Sequence[T]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size if self.page_size else 0


def paginate_params(page: int = 1, page_size: int = 20, max_size: int = 100) -> tuple[int, int]:
    page = max(1, page)
    page_size = max(1, min(page_size, max_size))
    return page, page_size


def offset_limit(page: int, page_size: int) -> tuple[int, int]:
    return (page - 1) * page_size, page_size
