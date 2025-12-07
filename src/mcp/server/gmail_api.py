#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import print_function

import logging
import base64
import os.path
import re

from typing import AsyncIterator, Dict, Any, Optional, Literal

from dateutil import tz
from datetime import date, datetime
from contextlib import asynccontextmanager
from pathlib import Path
from json import dumps
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from mcp.server.fastmcp.server import FastMCP, Context

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GmailServiceMCPServer")

SCOPES = [
    # Read-only
    "https://www.googleapis.com/auth/gmail.readonly",          # Chỉ đọc email
    # "https://www.googleapis.com/auth/gmail.metadata",          # Chỉ đọc metadata (subject, sender, label)
    # "https://www.googleapis.com/auth/gmail.labels",            # Xem và quản lý labels
    #
    # # Send / Compose
    "https://www.googleapis.com/auth/gmail.send",              # Gửi email
    "https://www.googleapis.com/auth/gmail.compose",           # Tạo và gửi email
    #
    # # Modify / Full access
    "https://www.googleapis.com/auth/gmail.modify",            # Gửi, đọc, xóa, thay đổi labels
    # "https://mail.google.com/",                                 # Full access, toàn quyền trên mailbox
    #
    # # Additional
    # "https://www.googleapis.com/auth/gmail.insert",            # Thêm email vào mailbox mà không trigger filters
    # "https://www.googleapis.com/auth/gmail.messages.modify",   # Thêm/xóa label trên email
    # "https://www.googleapis.com/auth/gmail.settings.basic",    # Quản lý cài đặt cơ bản (signature, vacation, forwarding)
    # "https://www.googleapis.com/auth/gmail.settings.sharing"   # Quản lý sharing settings (delegates)
]

CREDENTIAL_FILE = Path("/Users/minhnguyen/Main/Study/Major/Projects/Python/langrework/data/crendentials/minhnv14099_credential.json")
TOKEN_FILE = CREDENTIAL_FILE.with_name(CREDENTIAL_FILE.name.rstrip('.json') + "_token.json")

POPABLE_FIELDS = ()


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    # Setting something here
    try:
        yield {}
    finally:
        global _gmail_service, mcp_server
        if _gmail_service:
            logger.info('Close Gmail service.')
            _gmail_service.close()
            logger.info(f'MCP Server {mcp_server.name!r} shut down.')


mcp_server = FastMCP(
    name='GmailService',
    lifespan=server_lifespan
)

_gmail_service = None


def get_service():
    global _gmail_service

    if _gmail_service:
        ...
    else:
        creds = None

        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Error refreshing token: {str(e)}")
                    creds = None

        if not creds or not creds.valid:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIAL_FILE, SCOPES)
                creds = flow.run_local_server(
                    port=0,
                    prompt="consent",
                    access_type="offline"
                )
                # Save new token
                TOKEN_FILE.write_text(creds.to_json())
            except Exception as e:
                logger.error(f"Error verifying permission: {str(e)}")
        # --- Build Gmail API service ---
        try:
            _gmail_service = build("gmail", "v1", credentials=creds)
        except Exception as e:
            logger.error(f"Error building service: {str(e)}")
            _gmail_service = None

    return _gmail_service


@mcp_server.tool()
async def send_email(ctx: Context, to: str, subject: str, message_text: str) -> str:
    """Send an email message to a person

    Args:
        to: Email address of recipient.
        subject: Subject of the message.
        message_text: Content of the message.

    Returns:
        Result.
    """
    try:
        service = get_service()

        message = MIMEText(message_text)
        message["to"] = to
        message["subject"] = subject

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {"raw": encoded_message}

        send_message = service.users().messages().send(userId="me", body=create_message).execute()

        logger.info(f"Sent a message to {to!r} successfully. ID: {send_message['id']!r}")
        return f"Sent a message to {to!r} successfully. ID: {send_message['id']!r}"
    except Exception as e:
        logging.error(f"Error sending message: {str(e)}")
        return f"Error sending message: {str(e)}"


def _get_messages(max_results: Optional[int] = None, query: Optional[str] = None) -> list[dict]:
    """Get messages with query acting as the filter

    Args:
        query: Query to filter message
        max_results: Maximum number of messages to get. -1 if no mention

    Returns:
        List of messages.
    """
    try:
        service = get_service()
        results = service.users().messages().list(
            userId='me',
            maxResults=max_results,
            q=query
        ).execute()

        messages = []

        for m in results.get('messages', []):
            msg_info = get_full_info(m['id'])
            for k in POPABLE_FIELDS:
                msg_info.pop(k)

            messages.append(msg_info)

        return messages
    except Exception as e:
        logger.error(f"Error getting messages: {str(e)}")
        raise e from None


def get_full_info(msg_id: str):
    """
    Get all info: headers, subject, sender, labels, snippet, body
    """
    try:
        service = get_service()

        msg = service.users().messages().get(
            userId='me',
            id=msg_id,
            format='full'
        ).execute()

        headers = msg["payload"]["headers"]

        def get_header(name):
            value = next((h["value"] for h in headers if h["name"].lower() == name.lower()), None)

            try:
                value = value.encode().decode("unicode_escape")
                # value = value.encode("latin1").decode("utf8")
                return value
            except Exception:
                return value

        subject = get_header("subject")
        sender = get_header("From")
        to = get_header("to")

        def process_datetime(datetime_str: str):
            # remove UTC from header time
            clean_date = re.sub(r"\(.*\)", '', datetime_str).strip()
            dt_utc = datetime.strptime(clean_date, '%a, %d %b %Y %H:%M:%S %z')
            # timezone of local location
            local_tz = tz.tzlocal()
            # convert to date in local
            dt_local = dt_utc.astimezone(local_tz)

            return str(dt_local)

        send_time = get_header("Date")  # ví dụ: "Wed, 07 Feb 2024 10:20:33 +0700"
        send_time = process_datetime(send_time)

        # Labels
        labels = msg.get('labelIds', [])
        # Snippet
        snippet = msg.get('snippet', '')
        # Trạng thái read/unread
        is_unread = 'UNREAD' in labels

        # Body: decode base64
        body = ""
        parts = msg["payload"].get("parts", [])
        if parts:
            for part in parts:
                if part["mimeType"] == "text/plain":
                    body += base64.urlsafe_b64decode(
                        part["body"]["data"]
                    ).decode("utf-8")
        else:
            body = base64.urlsafe_b64decode(
                msg["payload"]["body"]["data"]
            ).decode("utf-8")

        return {
            "send_time": send_time,
            "subject": subject,
            "from": sender,
            "to": to,
            "labels": labels,
            "snippet": snippet,
            "body": body,
            "is_unread": is_unread
        }
    except Exception as e:
        logger.error(f"Error getting message {msg_id!r}: {str(e)}")
        return dict()


@mcp_server.tool()
def get_messages(ctx: Context, max_results: int = 1, query: Optional[str] = None) -> str:
    """Get messages with query acting as the filter

    Args:
        query: Query to filter message. It likes when type search on Web.
        max_results: Maximum number of messages to get. -1 if no mention

    Returns:
        Content of messages.
    """
    try:
        messages = _get_messages(max_results, query)
        messages_str = ""
        for m in messages:
            messages_str += dumps(m, indent=2)
            messages_str += '\n\n'
            messages_str += '-'*100 + '\n\n'

        logger.info(f"Get messages successfully, {len(messages)} messages.")
        return f'Get messages successfully. \n{messages}'
    except Exception as e:
        logger.error(f"Error getting messages: {str(e)}")
        return f"Error getting messages: {str(e)}"


@mcp_server.tool()
def get_messages_by_date(ctx: Context, date_: Optional[str] = None) -> str:
    """Get messages on a specific date

    Args:
        date_: Date info with form 'yyyy-mm-dd'. If the date is today, set it ``None``

    Returns:
        Content of messages.
    """
    if date_ is None:
        date_ = date.today()
        yyyy, mm, dd = date_.year, date_.month, date_.day
        date_ = date_.strftime("%Y-%m-%d")
    else:
        yyyy, mm, dd = date_.split(r"-")

    next_day = f"{yyyy}-{mm}-{int(dd)+1:02d}"
    query = f"after:{yyyy}/{mm}/{dd} before:{next_day.replace('-', '/')}"

    try:
        messages = _get_messages(query=query)

        messages_str = ""
        for m in messages:
            messages_str += dumps(m, indent=2)
            messages_str += '\n\n'
            messages_str += '-'*100 + '\n\n'

        logger.info(f"Get messages on {date_!r} successfully.")
        return f"Successfully! Messages on {date_!r}: \n {messages}"
    except Exception as e:
        logger.error(f"Error getting messages on {date_!r}: {str(e)}")
        return f"Error getting messages on {date_!r}: {str(e)}"


@mcp_server.prompt()
def general_system_prompt(ctx: Context):
    return [
        {
            "role": "user",
            "content": f"You are a very helpful assistance."
        }
    ]


def main():
    transport: Literal["stdio", "sse", "streamable-http"] = "stdio"
    mcp_server.run(transport=transport)
    logger.info(f'MCP Server Gmail API is running on transport {transport!r}')


if __name__ == '__main__':
    main()
