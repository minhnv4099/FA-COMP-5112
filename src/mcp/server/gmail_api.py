#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import print_function

import logging
import base64
import re
import warnings

from typing import AsyncIterator, Dict, Any, Optional, Literal

from dateutil import tz
from datetime import date
from contextlib import asynccontextmanager
from pathlib import Path
from json import dumps
from email.mime.text import MIMEText
from email.utils import parsedate_to_datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from mcp.server.fastmcp.server import FastMCP, Context

from src.telemetry.telemetry_decorator import telemetry_mcp_tool, telemetry_prompt, telemetry_resource
from src.telemetry.telemetry import record_startup, record_shutdown
from src.mcp.server.utils import require_human_confirm, NeedHumanConfirmException, HumanAbortedException

warnings.simplefilter(action='ignore', category=FutureWarning)


logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(levelname)s][%(name)s][%(funcName)s] - %(message)s #%(lineno)d'
)
logger = logging.getLogger("GmailServiceMCPServer")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",          # Chỉ đọc email
    "https://www.googleapis.com/auth/gmail.send",              # Gửi email
    "https://www.googleapis.com/auth/gmail.compose",           # Tạo và gửi email
    "https://www.googleapis.com/auth/gmail.modify",            # Gửi, đọc, xóa, thay đổi labels
]

CREDENTIAL_FILE = Path("/Users/minhnguyen/Main/Study/Major/Projects/Python/langrework/data/crendentials/minhnv14099_credential.json")
TOKEN_FILE = CREDENTIAL_FILE.with_name(CREDENTIAL_FILE.name.rstrip('.json') + "_token.json")

POPABLE_FIELDS = tuple()


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    # Setting something here
    try:
        record_startup()
        yield {}
    finally:
        global _gmail_service, mcp_server
        if _gmail_service:
            _gmail_service.close()
            logger.info('Close Gmail service.')
            logger.info(f'MCP Server {mcp_server.name!r} shut down.')
            record_shutdown()


mcp_server = FastMCP(
    name='GmailService',
    lifespan=server_lifespan
)

_gmail_service: Optional[None] = None


def get_service():
    global _gmail_service

    if _gmail_service:
        ...
    else:
        creds = None

        if TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Error refreshing token: {e}")
                    creds = None

        if not creds or not creds.valid:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIAL_FILE), SCOPES)
                creds = flow.run_local_server(
                    port=0,
                    prompt="consent",
                    access_type="offline"
                )
                # Save new token
                TOKEN_FILE.write_text(creds.to_json())
            except Exception as e:
                logger.error(f"Error verifying permission: {e}")
        # --- Build Gmail API service ---
        try:
            _gmail_service = build("gmail", "v1", credentials=creds)
        except Exception as e:
            logger.error(f"Error building service: {e}")
            _gmail_service = None

    return _gmail_service


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
        logger.error(f"Error getting messages: {e}")
        raise e from None


def get_full_info(msg_id: str) -> Dict[str, str]:
    """Get all info: date, subject, sender, labels, snippet, body.

    Args:
        msg_id: Id of message.

    Returns:
        Dictionary of values.
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
            dt_utc = parsedate_to_datetime(clean_date)
            # convert to date in local
            dt_utc = dt_utc.astimezone(tz.tzlocal())

            return dt_utc.strftime("%a, %d %b %Y %H:%M:%S")

        send_time = get_header("Date")  # "Wed, 07 Feb 2024 10:20:33 +0700"
        send_time = process_datetime(send_time)

        labels = msg.get('labelIds', [])
        snippet = msg.get('snippet', '')
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
        logger.error(f"Error getting message {msg_id!r}: {e}")
        return dict()


@mcp_server.tool()
@telemetry_mcp_tool("send_email")
def send_email(ctx: Context, to: str, subject: str, message_text: str, aux_kwargs: Optional[dict[str, Any]] = None):
    """Send an email message to a person. If human didn't provide recipient address, let try find it by yourself by using contacts.

    Args:
        to: Email address of recipient.
            If human didn't provide, let try find it by yourself by using contacts.
        subject: Subject of the message.
        message_text: Content of the message.

    Returns:
        Status of sending message.
    """
    asking_prompt = f"""
Confirm sending message:
    ---------------------------
    To: {to}
    Subject: {subject}
    Content: 
        {message_text}
    ---------------------------
Proceed this operation? (y/n): """.lstrip()

    try:
        require_human_confirm(asking_prompt=asking_prompt, kwargs=aux_kwargs)

        service = get_service()

        message = MIMEText(message_text)
        message["to"] = to
        message["subject"] = subject

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {"raw": encoded_message}

        send_message = service.users().messages().send(userId="me", body=create_message).execute()

        logger.info(f"Successfully! Sent a message to {to!r}. ID: {send_message['id']!r}")
        return f"Successfully! Sent a message to {to!r}. ID: {send_message['id']!r}"
    except NeedHumanConfirmException as e:
        return e.kwargs
    except HumanAbortedException as e:
        return str(e)
    except Exception as e:
        logging.error(f"Error sending message: {e}")
        return f"Error sending message: {e}"


@mcp_server.tool()
@telemetry_mcp_tool("get_messages")
def get_messages(ctx: Context, max_results: int = 10, query: Optional[str] = None) -> str:
    """Get messages with query acting as the filter

    Args:
        max_results: Maximum number of messages to get. None if no mention.
        query: Query to filter message. It likes when type search on Web.

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

        logger.info(f"Get {len(messages)} messages successfully with query: {query!r}.")
        return f'Get messages successfully. \n{messages}'
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        return f"Error getting messages: {e}"


@mcp_server.tool()
@telemetry_mcp_tool("get_messages_by_date")
def get_messages_by_date(ctx: Context, date_: Optional[str] = None) -> str:
    """Get messages on a specific date

    Args:
        date_: Date information in form 'yyyy-mm-dd'. If the date is today, set it ``None``

    Returns:
        Content of messages.
    """
    if date_ is None:
        date_ = date.today()
        yyyy, mm, dd = date_.year, date_.month, date_.day
        date_ = date_.strftime("%Y-%m-%d")
    else:
        yyyy, mm, dd = date_.split(r"-")

    # TODO: use +/- delta time
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
        logger.error(f"Error getting messages on {date_!r}: {e}")
        return f"Error getting messages on {date_!r}: {e}"


@mcp_server.prompt()
@telemetry_prompt(f"{mcp_server.name}--general_system_prompt")
def general_system_prompt(ctx: Context):
    return "You are a very helpful assistance."


def main():
    transport: Literal["stdio", "sse", "streamable-http"] = "stdio"
    logger.info(f'MCP Server Gmail API is running on transport {transport!r}.')
    mcp_server.run(transport=transport)


if __name__ == '__main__':
    main()
