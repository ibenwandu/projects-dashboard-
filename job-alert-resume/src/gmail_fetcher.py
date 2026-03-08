"""Fetch Indeed (and similar) job alert emails from Gmail via the Gmail API."""
from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Iterator

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .config import CREDENTIALS_PATH, GMAIL_MAX_MESSAGES, GMAIL_QUERY, SCOPES, TOKEN_PATH


def get_gmail_service(credentials_path: Path | None = None, token_path: Path | None = None):
    """Build Gmail API service with OAuth2. Prompts for login on first run and saves token."""
    creds_path = credentials_path or CREDENTIALS_PATH
    tok_path = token_path or TOKEN_PATH
    creds = None
    if tok_path.exists():
        creds = Credentials.from_authorized_user_file(str(tok_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not creds_path.exists():
                raise FileNotFoundError(
                    f"Gmail credentials not found at {creds_path}. "
                    "Download credentials.json from Google Cloud Console (Gmail API) and save it there."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        tok_path.parent.mkdir(parents=True, exist_ok=True)
        with open(tok_path, "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def _decode_body(payload: dict) -> str:
    """Decode email body from Gmail API message payload."""
    if "body" in payload and payload["body"].get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    if "parts" not in payload:
        return ""
    text_parts = []
    for part in payload["parts"]:
        if part.get("mimeType") in ("text/plain", "text/html") and part.get("body", {}).get("data"):
            text_parts.append(
                base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
            )
    # Prefer HTML for link extraction; fallback to plain
    html = next((p for p in text_parts if p.strip().lower().startswith("<")), "")
    return html or (text_parts[0] if text_parts else "")


def list_job_alert_messages(service, query: str | None = None, max_results: int = 50) -> list[dict]:
    """List message IDs and minimal metadata for job alert emails."""
    query = query or GMAIL_QUERY
    response = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=min(max_results, 100))
        .execute()
    )
    return response.get("messages", [])


def get_message_body(service, msg_id: str) -> str:
    """Get full message and return decoded body (HTML or plain)."""
    msg = (
        service.users()
        .messages()
        .get(userId="me", id=msg_id, format="full")
        .execute()
    )
    payload = msg.get("payload", {})
    return _decode_body(payload)


def fetch_job_alert_bodies(
    credentials_path: Path | None = None,
    token_path: Path | None = None,
    query: str | None = None,
    max_messages: int | None = None,
) -> Iterator[tuple[str, str]]:
    """
    Yield (message_id, body) for each job alert email.
    Use query/max_messages from config if not provided.
    """
    service = get_gmail_service(credentials_path=credentials_path, token_path=token_path)
    messages = list_job_alert_messages(
        service,
        query=query or GMAIL_QUERY,
        max_results=max_messages or GMAIL_MAX_MESSAGES,
    )
    for m in messages:
        mid = m["id"]
        try:
            body = get_message_body(service, mid)
        except Exception:
            body = ""
        yield mid, body
