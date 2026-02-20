#!/usr/bin/env python3
"""Minimal Gmail read-only CLI via Google OAuth."""

from __future__ import annotations

import argparse
import base64
import os
from typing import Iterable

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read Gmail with OAuth (read-only).")
    parser.add_argument(
        "--credentials",
        default="gmail_credentials.json",
        help="Path to OAuth client credentials JSON from Google Cloud.",
    )
    parser.add_argument(
        "--token",
        default="gmail_token.json",
        help="Path to cached OAuth token JSON.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List message IDs + metadata.")
    list_parser.add_argument(
        "--query",
        default="",
        help="Gmail query, e.g. 'newer_than:7d from:someone@example.com'.",
    )
    list_parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="Number of messages to list.",
    )

    read_parser = subparsers.add_parser("read", help="Read one message by Gmail ID.")
    read_parser.add_argument("message_id", help="Gmail message ID.")
    read_parser.add_argument(
        "--max-chars",
        type=int,
        default=8000,
        help="Max number of body characters to print.",
    )
    return parser.parse_args()


def get_credentials(credentials_path: str, token_path: str) -> Credentials:
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(
                    f"OAuth credentials not found: {credentials_path}. "
                    "Download Desktop OAuth client JSON from Google Cloud."
                )
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())
    return creds


def get_service(credentials_path: str, token_path: str):
    creds = get_credentials(credentials_path, token_path)
    return build("gmail", "v1", credentials=creds)


def header_value(headers: Iterable[dict], name: str) -> str:
    lower_name = name.lower()
    for item in headers:
        if item.get("name", "").lower() == lower_name:
            return item.get("value", "")
    return ""


def decode_b64url(data: str) -> str:
    if not data:
        return ""
    padded = data + "=" * (-len(data) % 4)
    try:
        return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")
    except Exception:
        return ""


def extract_plain_text(payload: dict) -> str:
    body_data = payload.get("body", {}).get("data")
    mime_type = payload.get("mimeType", "")

    if mime_type == "text/plain" and body_data:
        return decode_b64url(body_data)

    text_parts = []
    for part in payload.get("parts", []) or []:
        if part.get("mimeType") == "text/plain":
            text_parts.append(decode_b64url(part.get("body", {}).get("data", "")))
        elif part.get("parts"):
            nested = extract_plain_text(part)
            if nested:
                text_parts.append(nested)

    if text_parts:
        return "\n".join(p for p in text_parts if p.strip())
    if body_data:
        return decode_b64url(body_data)
    return ""


def do_list(service, query: str, max_results: int) -> int:
    result = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    messages = result.get("messages", [])
    if not messages:
        print("No messages found.")
        return 0

    for idx, message in enumerate(messages, start=1):
        msg = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=message["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            )
            .execute()
        )
        headers = msg.get("payload", {}).get("headers", [])
        from_value = header_value(headers, "From")
        subject = header_value(headers, "Subject")
        date = header_value(headers, "Date")
        print(f"{idx}. id={message['id']}")
        print(f"   From: {from_value}")
        print(f"   Date: {date}")
        print(f"   Subject: {subject}")
    return 0


def do_read(service, message_id: str, max_chars: int) -> int:
    msg = (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )
    headers = msg.get("payload", {}).get("headers", [])
    from_value = header_value(headers, "From")
    to_value = header_value(headers, "To")
    subject = header_value(headers, "Subject")
    date = header_value(headers, "Date")
    body = extract_plain_text(msg.get("payload", {})).strip()

    print(f"id: {message_id}")
    print(f"From: {from_value}")
    print(f"To: {to_value}")
    print(f"Date: {date}")
    print(f"Subject: {subject}")
    print("-" * 60)
    if not body:
        print("[No plain-text body found]")
        return 0
    print(body[:max_chars])
    if len(body) > max_chars:
        print("\n[truncated]")
    return 0


def main() -> int:
    args = parse_args()
    service = get_service(args.credentials, args.token)
    if args.command == "list":
        return do_list(service, args.query, args.max_results)
    if args.command == "read":
        return do_read(service, args.message_id, args.max_chars)
    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
