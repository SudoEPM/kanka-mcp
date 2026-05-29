from mcp.server.fastmcp import FastMCP
from ..client import make_kanka_request, create_kanka_entity, update_kanka_entity

# Notes in Kanka are in-world artifacts (letters found in a tower, a journal
# entry left by an NPC, a pamphlet from a cult). GM-facing prep typically lives
# in Journals. Both are wiki-style entities and either can be used either way;
# the convention above just matches how Kanka itself frames them.

def format_note_summary(note: dict) -> str:
    """Format a note into a readable summary."""
    return f"""
Name: {note.get('name', 'Unknown')}
ID: {note.get('id', 'N/A')}
Entity ID: {note.get('entity_id', 'N/A')}
Type: {note.get('type') or 'None'}
Parent Note ID: {note.get('note_id') or 'None'}
Tags: {len(note.get('tags', []))} tag(s)
Is Private: {'Yes' if note.get('is_private') else 'No'}
"""

def format_note_detail(note: dict) -> str:
    """Format a note's full details."""
    return f"""
Name: {note.get('name', 'Unknown')}
ID: {note.get('id', 'N/A')}
Entity ID: {note.get('entity_id', 'N/A')}
Type: {note.get('type') or 'None'}
Parent Note ID: {note.get('note_id') or 'None (Top-level note)'}

Entry/Description:
{note.get('entry', 'No description available.')}

Tags: {note.get('tags', [])}
Is Private: {'Yes' if note.get('is_private') else 'No'}
Created: {note.get('created_at')}
Last Updated: {note.get('updated_at')}
"""

def register_note_tools(mcp: FastMCP):
    """Register all note-related tools with the MCP server."""

    @mcp.tool()
    async def get_all_notes() -> str:
        """Get a list of all notes in the campaign.

        Notes in Kanka are typically in-world artifacts (letters, found pages,
        in-character writings). GM prep usually lives in Journals.
        """
        data = await make_kanka_request("notes")

        if not data:
            return "Unable to fetch notes."
        if "error" in data:
            return f"Error: {data['error']}"
        if "data" not in data or not data["data"]:
            return "No notes found in this campaign."

        notes = [format_note_summary(n) for n in data["data"]]
        return "\n---\n".join(notes)

    @mcp.tool()
    async def get_note(note_id: int) -> str:
        """Get detailed information about a specific note.

        Args:
            note_id: The ID of the note to retrieve
        """
        data = await make_kanka_request(f"notes/{note_id}")

        if not data:
            return f"Unable to fetch note with ID {note_id}."
        if "error" in data:
            return f"Error: {data['error']}"
        if "data" not in data:
            return f"No note found with ID {note_id}."

        return format_note_detail(data["data"])

    @mcp.tool()
    async def create_note(
        name: str,
        entry: str = "",
        note_type: str = "",
        parent_note_id: int = None,
        entity_image_uuid: str = None,
        is_private: bool = False
    ) -> str:
        """Create a new note in the campaign.

        Notes are typically in-world artifacts: a letter found in a wizard's
        tower, a pamphlet from a cult, an NPC's diary entry. Use Journals for
        GM-facing session/world prep.

        Args:
            name: The note's title (required)
            entry: HTML body of the note
            note_type: Note category (e.g., "Letter", "Diary", "Pamphlet")
            parent_note_id: ID of the parent note (for nested notes)
            entity_image_uuid: Gallery image UUID for the note image
            is_private: Whether the note is only visible to admins
        """
        note_data = {
            "name": name,
            "entry": entry,
            "type": note_type,
            "is_private": is_private
        }

        if parent_note_id is not None:
            note_data["note_id"] = parent_note_id
        if entity_image_uuid is not None:
            note_data["entity_image_uuid"] = entity_image_uuid

        note_data = {k: v for k, v in note_data.items() if v != ""}

        result = await create_kanka_entity("notes", note_data)

        if not result:
            return "Failed to create note."
        if "error" in result:
            return f"Error creating note: {result['error']}"

        if "data" in result:
            note = result["data"]
            return f"""
Successfully created note!

Name: {note.get('name')}
Note ID: {note.get('id')}
Entity ID: {note.get('entity_id')}
Type: {note.get('type') or 'None'}
Parent Note ID: {note.get('note_id') or 'None'}
Visibility: {'Private' if note.get('is_private') else 'Public'}

The note has been added to your campaign.
"""

        return "Note created, but unexpected response format."

    @mcp.tool()
    async def update_note(
        note_name: str,
        entry: str = None,
        note_type: str = None,
        parent_note_id: int = None,
        entity_image_uuid: str = None,
        is_private: bool = None
    ) -> str:
        """Update an existing note by name.

        Args:
            note_name: The name of the note to update (used for search)
            entry: HTML body of the note
            note_type: Note category
            parent_note_id: ID of the parent note
            entity_image_uuid: Gallery image UUID
            is_private: Whether the note is only visible to admins
        """
        notes_data = await make_kanka_request("notes")

        if not notes_data or "data" not in notes_data:
            return f"Unable to search for note '{note_name}'."
        if "error" in notes_data:
            return f"Error searching for note: {notes_data['error']}"

        target_note = None
        for n in notes_data["data"]:
            if n.get("name", "").lower() == note_name.lower():
                target_note = n
                break

        if not target_note:
            return f"Note '{note_name}' not found in campaign."

        note_id = target_note["id"]

        update_data = {}
        if entry is not None:
            update_data["entry"] = entry
        if note_type is not None:
            update_data["type"] = note_type
        if parent_note_id is not None:
            update_data["note_id"] = parent_note_id
        if entity_image_uuid is not None:
            update_data["entity_image_uuid"] = entity_image_uuid
        if is_private is not None:
            update_data["is_private"] = is_private

        if not update_data:
            return "No updates provided. Please specify at least one field to update."

        result = await update_kanka_entity(f"notes/{note_id}", update_data)

        if not result:
            return f"Failed to update note '{note_name}'."
        if "error" in result:
            return f"Error updating note: {result['error']}"

        if "data" in result:
            note = result["data"]
            updated_fields = list(update_data.keys())
            return f"""
Successfully updated note '{note_name}'!

Name: {note.get('name')}
ID: {note.get('id')}
Type: {note.get('type') or 'None'}
Parent Note ID: {note.get('note_id') or 'None'}
Visibility: {'Private' if note.get('is_private') else 'Public'}

Updated fields: {', '.join(updated_fields)}
"""

        return "Note updated, but unexpected response format."
