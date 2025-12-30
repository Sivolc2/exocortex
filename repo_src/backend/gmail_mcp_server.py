#!/usr/bin/env python3
"""
Gmail MCP Server for Exocortex

This server provides access to Gmail messages via the MCP protocol.
Provides tools to:
- Search emails by query
- Read email content
- Get email statistics
- List recent emails
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import base64
from email.mime.text import MIMEText

from mcp.server import Server
from mcp.types import (
    Resource, Tool, TextContent,
    ListResourcesResult, ReadResourceResult, ListToolsResult, CallToolResult
)
from mcp.server.stdio import stdio_server
from pydantic import BaseModel

# Try to import Gmail API libraries
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False
    print("Warning: Google API libraries not available. Install with: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client", file=sys.stderr)

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Credentials path
PROJECT_ROOT = Path(__file__).parent.parent.parent
CREDENTIALS_DIR = PROJECT_ROOT / ".credentials"
TOKEN_FILE = CREDENTIALS_DIR / "gmail_token.json"
CREDENTIALS_FILE = CREDENTIALS_DIR / "gmail_credentials.json"

# Initialize MCP server
server = Server("exocortex-gmail")

class GmailMessage(BaseModel):
    """Gmail message model"""
    id: str
    thread_id: str
    subject: str
    from_: str
    to: str
    date: str
    snippet: str
    labels: List[str] = []

def get_gmail_service():
    """Authenticate and return Gmail API service"""
    if not GMAIL_AVAILABLE:
        raise RuntimeError("Gmail API libraries not installed")

    creds = None

    # Load existing token if available
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # If no valid credentials, need to authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"Gmail credentials not found at {CREDENTIALS_FILE}. "
                    "Please download OAuth credentials from Google Cloud Console and save to this location."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)

        # Save credentials for next run
        CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

def parse_message_headers(headers: List[Dict]) -> Dict[str, str]:
    """Parse email headers into a dict"""
    result = {}
    for header in headers:
        name = header.get('name', '').lower()
        value = header.get('value', '')
        result[name] = value
    return result

def get_message_body(message: Dict) -> str:
    """Extract plain text body from message"""
    try:
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        return base64.urlsafe_b64decode(data).decode('utf-8')
        elif 'body' in message['payload']:
            data = message['payload']['body'].get('data', '')
            if data:
                return base64.urlsafe_b64decode(data).decode('utf-8')
    except Exception as e:
        print(f"Error extracting message body: {e}", file=sys.stderr)
    return ""

def search_emails(query: str, max_results: int = 20) -> List[GmailMessage]:
    """Search emails using Gmail query syntax"""
    try:
        service = get_gmail_service()
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()

        messages = results.get('messages', [])
        email_list = []

        for msg in messages:
            msg_data = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='metadata',
                metadataHeaders=['Subject', 'From', 'To', 'Date']
            ).execute()

            headers = parse_message_headers(msg_data['payload']['headers'])

            email_list.append(GmailMessage(
                id=msg_data['id'],
                thread_id=msg_data['threadId'],
                subject=headers.get('subject', '(No subject)'),
                from_=headers.get('from', ''),
                to=headers.get('to', ''),
                date=headers.get('date', ''),
                snippet=msg_data.get('snippet', ''),
                labels=msg_data.get('labelIds', [])
            ))

        return email_list
    except Exception as e:
        print(f"Error searching emails: {e}", file=sys.stderr)
        raise

def get_email_content(message_id: str) -> Dict[str, Any]:
    """Get full email content by ID"""
    try:
        service = get_gmail_service()
        msg_data = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()

        headers = parse_message_headers(msg_data['payload']['headers'])
        body = get_message_body(msg_data)

        return {
            'id': msg_data['id'],
            'thread_id': msg_data['threadId'],
            'subject': headers.get('subject', '(No subject)'),
            'from': headers.get('from', ''),
            'to': headers.get('to', ''),
            'date': headers.get('date', ''),
            'labels': msg_data.get('labelIds', []),
            'snippet': msg_data.get('snippet', ''),
            'body': body
        }
    except Exception as e:
        print(f"Error getting email content: {e}", file=sys.stderr)
        raise

def get_email_stats() -> Dict[str, Any]:
    """Get statistics about Gmail account"""
    try:
        service = get_gmail_service()

        # Get total message count
        profile = service.users().getProfile(userId='me').execute()

        # Get recent message counts by label
        labels = service.users().labels().list(userId='me').execute()
        label_counts = {}

        for label in labels.get('labels', []):
            label_counts[label['name']] = label.get('messagesTotal', 0)

        return {
            'email_address': profile.get('emailAddress', ''),
            'total_messages': profile.get('messagesTotal', 0),
            'total_threads': profile.get('threadsTotal', 0),
            'history_id': profile.get('historyId', ''),
            'label_counts': label_counts
        }
    except Exception as e:
        print(f"Error getting email stats: {e}", file=sys.stderr)
        raise

# === MCP Resources ===

@server.list_resources()
async def list_resources() -> ListResourcesResult:
    """List available Gmail resources"""
    return ListResourcesResult(resources=[])

@server.read_resource()
async def read_resource(uri: str) -> ReadResourceResult:
    """Read a resource by URI"""
    raise ValueError(f"Unknown resource URI: {uri}")

# === MCP Tools ===

@server.list_tools()
async def list_tools() -> ListToolsResult:
    """List available Gmail tools"""
    tools = [
        Tool(
            name="search_emails",
            description="Search emails using Gmail query syntax (e.g., 'from:sender@example.com', 'subject:meeting', 'after:2024/01/01')",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Gmail search query"},
                    "max_results": {"type": "integer", "default": 20, "maximum": 100, "description": "Maximum number of results"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_email",
            description="Get full content of an email by message ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {"type": "string", "description": "Gmail message ID"}
                },
                "required": ["message_id"]
            }
        ),
        Tool(
            name="get_recent_emails",
            description="Get recent emails (last N days)",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "default": 7, "description": "Number of days to look back"},
                    "max_results": {"type": "integer", "default": 20, "maximum": 100, "description": "Maximum number of results"}
                },
                "required": []
            }
        ),
        Tool(
            name="get_email_stats",
            description="Get statistics about the Gmail account",
            inputSchema={"type": "object", "properties": {}}
        )
    ]
    return ListToolsResult(tools=tools)

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    """Handle tool calls"""

    if not GMAIL_AVAILABLE:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text="Gmail API not available. Please install: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client"
            )]
        )

    if name == "search_emails":
        query = arguments.get("query", "")
        max_results = min(arguments.get("max_results", 20), 100)

        try:
            messages = search_emails(query, max_results)
            result = {
                "query": query,
                "count": len(messages),
                "messages": [msg.model_dump() for msg in messages]
            }
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(result, indent=2))]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error searching emails: {str(e)}")]
            )

    elif name == "get_email":
        message_id = arguments.get("message_id", "")
        if not message_id:
            raise ValueError("message_id is required")

        try:
            content = get_email_content(message_id)
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(content, indent=2))]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error getting email: {str(e)}")]
            )

    elif name == "get_recent_emails":
        days = arguments.get("days", 7)
        max_results = min(arguments.get("max_results", 20), 100)

        # Build query for recent emails
        date = (datetime.now() - timedelta(days=days)).strftime('%Y/%m/%d')
        query = f"after:{date}"

        try:
            messages = search_emails(query, max_results)
            result = {
                "days": days,
                "count": len(messages),
                "messages": [msg.model_dump() for msg in messages]
            }
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(result, indent=2))]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error getting recent emails: {str(e)}")]
            )

    elif name == "get_email_stats":
        try:
            stats = get_email_stats()
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(stats, indent=2))]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error getting email stats: {str(e)}")]
            )

    else:
        raise ValueError(f"Unknown tool: {name}")

if __name__ == "__main__":
    import asyncio

    async def main():
        async with stdio_server() as streams:
            await server.run(streams[0], streams[1], server.create_initialization_options())

    asyncio.run(main())
