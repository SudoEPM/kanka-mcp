import httpx
from mcp.server.fastmcp import FastMCP
from ..client import (
    KANKA_API_BASE,
    KANKA_API_TOKEN,
    KANKA_CAMPAIGN_ID,
    create_kanka_entity,
    make_kanka_request,
    update_kanka_entity,
)

def format_journal_summary(journal: dict) -> str:
    """Format a journal into a readable summary."""
    return f"""
Name: {journal.get('name', 'Unknown')}
ID: {journal.get('id', 'N/A')}
Entity ID: {journal.get('entity_id', 'N/A')}
Type: {journal.get('type') or 'None'}
Date: {journal.get('date') or 'No date'}
Author ID: {journal.get('author_id') or 'None'}
Calendar Date: {journal.get('calendar_year')}/{journal.get('calendar_month')}/{journal.get('calendar_day') if journal.get('calendar_year') else 'Not set'}
Parent Journal ID: {journal.get('journal_id') or 'None'}
Tags: {len(journal.get('tags', []))} tag(s)
Is Private: {'Yes' if journal.get('is_private') else 'No'}
"""

def format_journal_detail(journal: dict) -> str:
    """Format a journal's full details."""
    calendar_info = ""
    if journal.get('calendar_year'):
        calendar_info = f"\nCalendar Date: Year {journal.get('calendar_year')}, Month {journal.get('calendar_month')}, Day {journal.get('calendar_day')}"
        if journal.get('calendar_event_length'):
            calendar_info += f" (Duration: {journal.get('calendar_event_length')} days)"
    
    return f"""
Name: {journal.get('name', 'Unknown')}
ID: {journal.get('id', 'N/A')}
Entity ID: {journal.get('entity_id', 'N/A')}
Type: {journal.get('type') or 'None'}
Date: {journal.get('date') or 'No date'}
Author ID: {journal.get('author_id') or 'None'}
Parent Journal ID: {journal.get('journal_id') or 'None (Top-level journal)'}
{calendar_info}

Entry/Content:
{journal.get('entry', 'No content available.')}

Tags: {journal.get('tags', [])}
Is Private: {'Yes' if journal.get('is_private') else 'No'}
Created: {journal.get('created_at')}
Last Updated: {journal.get('updated_at')}
"""

def register_journal_tools(mcp: FastMCP):
    """Register all journal-related tools with the MCP server."""
    
    @mcp.tool()
    async def get_all_journals() -> str:
        """Get a list of all journals in the campaign.
        
        Returns a summary of all journals including their name, ID, type, and date info.
        """
        data = await make_kanka_request("journals")
        
        if not data:
            return "Unable to fetch journals."
        
        if "error" in data:
            return f"Error: {data['error']}"
        
        if "data" not in data or not data["data"]:
            return "No journals found in this campaign."
        
        journals = [format_journal_summary(journal) for journal in data["data"]]
        return "\n---\n".join(journals)

    @mcp.tool()
    async def get_journal(journal_id: int) -> str:
        """Get detailed information about a specific journal entry.
        
        Args:
            journal_id: The ID of the journal to retrieve
        """
        data = await make_kanka_request(f"journals/{journal_id}")
        
        if not data:
            return f"Unable to fetch journal with ID {journal_id}."
        
        if "error" in data:
            return f"Error: {data['error']}"
        
        if "data" not in data:
            return f"No journal found with ID {journal_id}."
        
        return format_journal_detail(data["data"])

    @mcp.tool()
    async def create_journal(
        name: str,
        entry: str = "",
        journal_type: str = "",
        date: str = "",
        author_id: int = None,
        journal_id: int = None,
        tags: list[int] = None,
        is_private: bool = False,
        tooltip: str = ""
    ) -> str:
        """Create a new journal in the campaign.

        Args:
            name: The journal's title (required)
            entry: HTML content of the journal
            journal_type: Journal type/category (e.g., "Session", "Log")
            date: Session or event date as a string
            author_id: Entity ID of the journal's author
            journal_id: Parent journal ID for creating sub-journals
            tags: List of tag IDs to apply to this journal
            is_private: Whether the journal is only visible to admins
            tooltip: Hover text for the journal (premium feature)
        """
        journal_data = {
            "name": name,
            "entry": entry,
            "type": journal_type,
            "date": date,
            "is_private": is_private,
            "tooltip": tooltip
        }

        # Only include optional ID fields if provided
        if author_id is not None:
            journal_data["author_id"] = author_id
        if journal_id is not None:
            journal_data["journal_id"] = journal_id

        # Add tags if provided
        if tags is not None and len(tags) > 0:
            journal_data["tags"] = tags
            journal_data["save_tags"] = True

        # Remove empty string values to keep the request clean
        journal_data = {k: v for k, v in journal_data.items() if v != ""}

        result = await create_kanka_entity("journals", journal_data)

        if not result:
            return "Failed to create journal."

        if "error" in result:
            return f"Error creating journal: {result['error']}"

        if "data" in result:
            journal = result["data"]
            return f"""
Successfully created journal!

Name: {journal.get('name')}
Journal ID: {journal.get('id')}
Entity ID: {journal.get('entity_id')}
Type: {journal.get('type') or 'None'}
Date: {journal.get('date') or 'None'}
Author ID: {journal.get('author_id') or 'None'}
Parent Journal ID: {journal.get('journal_id') or 'None (Top-level)'}
Tags: {len(journal.get('tags', []))} tag(s)
Visibility: {'Private' if journal.get('is_private') else 'Public'}

The journal has been added to your campaign.
"""

        return "Journal created, but unexpected response format."

    @mcp.tool()
    async def update_journal(
        journal_name: str,
        entry: str = None,
        journal_type: str = None,
        date: str = None,
        author_id: int = None,
        journal_id: int = None,
        tags: list[int] = None,
        is_private: bool = None,
        tooltip: str = None
    ) -> str:
        """Update an existing journal by name.

        First searches for the journal by name, then updates the specified fields.
        Only provided fields will be updated - others remain unchanged.

        Args:
            journal_name: The name of the journal to update (used for search)
            entry: HTML content of the journal
            journal_type: Journal type/category
            date: Session or event date as a string
            author_id: Entity ID of the journal's author
            journal_id: Parent journal ID
            tags: List of tag IDs to apply to this journal (replaces existing tags)
            is_private: Whether the journal is only visible to admins
            tooltip: Hover text for the journal (premium feature)
        """
        # First, search for the journal by name
        journals_data = await make_kanka_request("journals")

        if not journals_data or "data" not in journals_data:
            return f"Unable to search for journal '{journal_name}'."

        if "error" in journals_data:
            return f"Error searching for journal: {journals_data['error']}"

        # Find journal with matching name (case-insensitive)
        target_journal = None
        for journal in journals_data["data"]:
            if journal.get("name", "").lower() == journal_name.lower():
                target_journal = journal
                break

        if not target_journal:
            return f"Journal '{journal_name}' not found in campaign."

        journal_id_to_update = target_journal["id"]

        # Build update data with only provided values
        update_data = {}
        if entry is not None:
            update_data["entry"] = entry
        if journal_type is not None:
            update_data["type"] = journal_type
        if date is not None:
            update_data["date"] = date
        if author_id is not None:
            update_data["author_id"] = author_id
        if journal_id is not None:
            update_data["journal_id"] = journal_id
        if is_private is not None:
            update_data["is_private"] = is_private
        if tooltip is not None:
            update_data["tooltip"] = tooltip
        if tags is not None:
            update_data["tags"] = tags
            update_data["save_tags"] = True

        if not update_data:
            return "No updates provided. Please specify at least one field to update."

        # Update the journal
        result = await update_kanka_entity(f"journals/{journal_id_to_update}", update_data)

        if not result:
            return f"Failed to update journal '{journal_name}'."

        if "error" in result:
            return f"Error updating journal: {result['error']}"

        if "data" in result:
            journal = result["data"]
            updated_fields = list(update_data.keys())
            return f"""
Successfully updated journal '{journal_name}'!

Name: {journal.get('name')}
Journal ID: {journal.get('id')}
Entity ID: {journal.get('entity_id')}
Type: {journal.get('type') or 'None'}
Date: {journal.get('date') or 'None'}
Author ID: {journal.get('author_id') or 'None'}
Parent Journal ID: {journal.get('journal_id') or 'None (Top-level)'}
Tags: {len(journal.get('tags', []))} tag(s)
Visibility: {'Private' if journal.get('is_private') else 'Public'}

Updated fields: {', '.join(updated_fields)}
"""

        return "Journal updated, but unexpected response format."

    @mcp.tool()
    async def send_summary_notification(session_title: str, summary: str) -> str:
        """Send a summary notification via webhook.

        Creates a temporary journal with tag 527715 as a child of the Notification Triggers journal,
        which triggers a webhook notification. The journal is automatically deleted after creation.

        This is useful for sending campaign summaries or notifications through your configured webhook.

        Args:
            session_title: The session title (e.g., "Session 9 - Descent into the Cogs")
            summary: A brief summary of what happened in the session
        """
        # Tag ID that triggers the webhook
        NOTIFICATION_TAG_ID = 527715
        # Notification Triggers journal ID (parent journal)
        NOTIFICATION_TRIGGERS_JOURNAL_ID = 163442

        journal_data = {
            "name": session_title,
            "entry": summary,
            "tooltip": summary,
            "type": "Notification",
            "journal_id": NOTIFICATION_TRIGGERS_JOURNAL_ID,
            "tags": [NOTIFICATION_TAG_ID],
            "save_tags": True,
            "is_private": True  # Make it private so it doesn't clutter the public view
        }

        # Create the journal
        result = await create_kanka_entity("journals", journal_data)

        if not result or "error" in result:
            error_msg = result.get('error', 'Unknown error') if result else 'Failed to create notification'
            return f"Failed to send notification: {error_msg}"

        if "data" not in result:
            return "Failed to send notification: unexpected response format."

        journal = result["data"]
        journal_id = journal.get('id')

        if not journal_id:
            return "Notification created but unable to clean up (no ID returned)."

        # Now delete the journal to clean up
        headers = {
            "Authorization": f"Bearer {KANKA_API_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        url = f"{KANKA_API_BASE}/campaigns/{KANKA_CAMPAIGN_ID}/journals/{journal_id}"

        cleanup_ok = False
        cleanup_detail = ""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.delete(url, headers=headers, timeout=30.0)
                if resp.status_code < 400:
                    cleanup_ok = True
                else:
                    cleanup_detail = f"HTTP {resp.status_code}"
            except httpx.RequestError as e:
                cleanup_detail = str(e)

        cleanup_line = (
            "The webhook notification has been triggered and the temporary journal has been cleaned up."
            if cleanup_ok
            else f"The webhook notification has been triggered, but cleanup of journal {journal_id} failed ({cleanup_detail}) — delete it manually."
        )

        return f"""
Successfully sent summary notification!

Session: {session_title}
Summary: {summary}
Notification Tag: {NOTIFICATION_TAG_ID}
Parent Journal: Notification Triggers (ID: {NOTIFICATION_TRIGGERS_JOURNAL_ID})

{cleanup_line}
"""