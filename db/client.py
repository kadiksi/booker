"""Async Supabase PostgREST client (REST API via httpx — no sync calls in the hot path)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class SupabaseError(Exception):
    """Raised when Supabase REST returns an error or unexpected payload."""


class SupabaseClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0) -> None:
        self._base = f"{base_url.rstrip('/')}/rest/v1"
        self._headers = {
            "apikey": api_key,
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._client = httpx.AsyncClient(base_url=self._base, headers=self._headers, timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json_body: Any = None,
        prefer: str | None = None,
    ) -> httpx.Response:
        headers = dict(self._headers)
        if prefer:
            headers["Prefer"] = prefer
        try:
            response = await self._client.request(method, path, params=params, json=json_body, headers=headers)
        except httpx.RequestError as e:
            logger.exception("Supabase network error: %s", e)
            raise SupabaseError("Database connection failed") from e

        if response.status_code >= 400:
            body = response.text[:500]
            logger.error("Supabase error %s: %s", response.status_code, body)
            raise SupabaseError(f"Database error ({response.status_code})")
        return response

    async def fetch_user_by_telegram_id(self, telegram_id: str) -> dict[str, Any] | None:
        r = await self._request(
            "GET",
            "/users",
            params={"telegram_id": f"eq.{telegram_id}", "select": "*"},
        )
        data = r.json()
        if not data:
            return None
        return data[0]

    async def insert_user(
        self,
        telegram_id: str,
        current_book: str | None,
    ) -> dict[str, Any]:
        payload = {
            "telegram_id": telegram_id,
            "current_book": current_book,
        }
        r = await self._request(
            "POST",
            "/users",
            json_body=payload,
            prefer="return=representation",
        )
        data = r.json()
        if not data:
            raise SupabaseError("Failed to create user")
        return data[0]

    async def update_user(self, telegram_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        r = await self._request(
            "PATCH",
            "/users",
            params={"telegram_id": f"eq.{telegram_id}"},
            json_body=fields,
            prefer="return=representation",
        )
        data = r.json()
        if not data:
            raise SupabaseError("User not found or update failed")
        return data[0]

    async def fetch_chunk(self, book_id: str, position: int) -> dict[str, Any] | None:
        r = await self._request(
            "GET",
            "/chunks",
            params={
                "book_id": f"eq.{book_id}",
                "position": f"eq.{position}",
                "select": "*",
            },
        )
        data = r.json()
        if not data:
            return None
        return data[0]

    async def count_chunks(self, book_id: str) -> int:
        r = await self._request(
            "GET",
            "/chunks",
            params={
                "book_id": f"eq.{book_id}",
                "select": "position",
            },
        )
        return len(r.json())

    async def upsert_book(self, book_id: str, title: str) -> None:
        """Insert book or update title if id already exists (handles 409 without relying on merge-duplicates)."""
        try:
            response = await self._client.post(
                "/books",
                json={"id": book_id, "title": title},
                headers={**self._headers, "Prefer": "return=minimal"},
            )
        except httpx.RequestError as e:
            logger.exception("Supabase network error on upsert_book: %s", e)
            raise SupabaseError("Database connection failed") from e

        if response.status_code in (200, 201):
            return
        if response.status_code == 409:
            await self._request(
                "PATCH",
                "/books",
                params={"id": f"eq.{book_id}"},
                json_body={"title": title},
                prefer="return=minimal",
            )
            return
        body = response.text[:500]
        logger.error("upsert_book failed %s: %s", response.status_code, body)
        raise SupabaseError(f"Database error ({response.status_code})")

    async def insert_chunks_bulk(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        await self._request("POST", "/chunks", json_body=rows, prefer="return=minimal")

    async def delete_chunks_for_book(self, book_id: str) -> None:
        await self._request("DELETE", "/chunks", params={"book_id": f"eq.{book_id}"})

    async def list_books(self) -> list[dict[str, Any]]:
        r = await self._request(
            "GET",
            "/books",
            params={"select": "id,title"},
        )
        rows = r.json()
        rows.sort(key=lambda x: (x.get("title") or "").lower())
        return rows

    async def fetch_book(self, book_id: str) -> dict[str, Any] | None:
        r = await self._request(
            "GET",
            "/books",
            params={"id": f"eq.{book_id}", "select": "*"},
        )
        data = r.json()
        return data[0] if data else None

    async def fetch_user_book(self, telegram_id: str, book_id: str) -> dict[str, Any] | None:
        r = await self._request(
            "GET",
            "/user_books",
            params={
                "telegram_id": f"eq.{telegram_id}",
                "book_id": f"eq.{book_id}",
                "select": "*",
            },
        )
        data = r.json()
        return data[0] if data else None

    async def insert_user_book(
        self,
        telegram_id: str,
        book_id: str,
        current_position: int = 0,
        last_read_date: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "telegram_id": telegram_id,
            "book_id": book_id,
            "current_position": current_position,
            "last_read_date": last_read_date,
        }
        r = await self._request(
            "POST",
            "/user_books",
            json_body=payload,
            prefer="return=representation",
        )
        data = r.json()
        if not data:
            raise SupabaseError("Failed to create user_book row")
        return data[0]

    async def update_user_book(
        self,
        telegram_id: str,
        book_id: str,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        r = await self._request(
            "PATCH",
            "/user_books",
            params={
                "telegram_id": f"eq.{telegram_id}",
                "book_id": f"eq.{book_id}",
            },
            json_body=fields,
            prefer="return=representation",
        )
        data = r.json()
        if not data:
            raise SupabaseError("user_books update failed")
        return data[0]

    async def delete_book_cascade(self, book_id: str) -> None:
        await self._request("DELETE", "/books", params={"id": f"eq.{book_id}"})
