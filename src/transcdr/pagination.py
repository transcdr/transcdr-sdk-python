"""Cursor pagination.

Every list endpoint returns ``{"object": "list", "data": [...], "has_more",
"next_cursor"}``. The SDK wraps it in a page object::

    page = client.jobs.list(status="completed", limit=50)
    page.data, page.has_more, page.next_cursor

    for job in page.auto_paging_iter():  # walks every page lazily
        ...
"""

from __future__ import annotations

from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Dict,
    Generic,
    Iterator,
    List,
    Optional,
    TypeVar,
)

__all__ = ["SyncPage", "AsyncPage"]

T = TypeVar("T")


class _BasePage(Generic[T]):
    def __init__(self, body: Any) -> None:
        body = body if isinstance(body, dict) else {}
        self.raw: Dict[str, Any] = body
        self.data: List[T] = list(body.get("data") or [])
        self.next_cursor: Optional[str] = body.get("next_cursor")
        self.has_more: bool = bool(body.get("has_more")) and bool(self.next_cursor)

    def has_next_page(self) -> bool:
        return self.has_more

    def __iter__(self) -> Iterator[T]:
        """Iterate over this page's items only (see ``auto_paging_iter``)."""
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, index: int) -> T:
        return self.data[index]

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(len={len(self.data)}, has_more={self.has_more}, "
            f"next_cursor={self.next_cursor!r})"
        )


class SyncPage(_BasePage[T]):
    """One page of a list, able to fetch the pages after it."""

    def __init__(self, body: Any, fetch: Callable[[str], "SyncPage[T]"]) -> None:
        super().__init__(body)
        self._fetch = fetch

    def next_page(self) -> Optional["SyncPage[T]"]:
        """The following page, or ``None`` on the last one."""
        if not self.has_more or not self.next_cursor:
            return None
        return self._fetch(self.next_cursor)

    def auto_paging_iter(self) -> Iterator[T]:
        """Yield every item from this page onwards, fetching pages as needed."""
        page: Optional[SyncPage[T]] = self
        while page is not None:
            yield from page.data
            page = page.next_page()


class AsyncPage(_BasePage[T]):
    """One page of a list from :class:`~transcdr.AsyncTranscdr`."""

    def __init__(self, body: Any, fetch: Callable[[str], Awaitable["AsyncPage[T]"]]) -> None:
        super().__init__(body)
        self._fetch = fetch

    async def next_page(self) -> Optional["AsyncPage[T]"]:
        if not self.has_more or not self.next_cursor:
            return None
        return await self._fetch(self.next_cursor)

    async def auto_paging_iter(self) -> AsyncIterator[T]:
        """``async for item in page.auto_paging_iter(): ...``"""
        page: Optional[AsyncPage[T]] = self
        while page is not None:
            for item in page.data:
                yield item
            page = await page.next_page()
