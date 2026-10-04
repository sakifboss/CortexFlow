"""Ensure Qdrant collection exists. Run after migrations."""
from __future__ import annotations

import asyncio

from app.services.vector import vector


async def main() -> None:
    await vector.ensure_collection()
    print(f"[ok] Qdrant collection ready: {vector.collection}")


if __name__ == "__main__":
    asyncio.run(main())
