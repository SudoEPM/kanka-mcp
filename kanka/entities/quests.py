from mcp.server.fastmcp import FastMCP
from ..client import make_kanka_request, create_kanka_entity, update_kanka_entity

# Quest image UUIDs for different quest types
QUEST_IMAGES = {
    "completed": "a019c307-6c4b-48c8-82e4-da12aa72bf1b",  # Green checkmark
    "combat": "a019c682-3641-4a88-878f-f35a271eee79",     # Crossed swords
    "locate": "a019c5e9-edb1-436d-9048-0dbccd0ca22d",     # Map with magnifying glass
    "investigate": "a019c64b-68ce-4d8d-8c79-1bca39358bff", # Magnifying glass
    "generic": "a019c568-65ad-44c1-9d24-d0980262d207"     # Scroll with quill
}

# Default-system category_status ID for "completed" on quests.
# Auto-image-swap keys off this; campaigns with custom statuses won't trigger it.
QUEST_COMPLETED_STATUS_ID = 10

def _status_label(quest: dict) -> str:
    status = quest.get('status') or {}
    key = status.get('key')
    status_id = quest.get('status_id')
    if key and status_id:
        return f"{key} (status_id={status_id})"
    if status_id:
        return f"status_id={status_id}"
    return 'None'

def detect_quest_type(name: str, entry: str) -> str:
    """Detect quest type based on name and description to assign appropriate image."""
    text = f"{name} {entry}".lower()
    
    # Combat keywords
    combat_keywords = ["kill", "slay", "defeat", "destroy", "eliminate", "fight", "battle", "combat", "attack"]
    if any(keyword in text for keyword in combat_keywords):
        return "combat"
    
    # Locate/recovery keywords
    locate_keywords = ["find", "locate", "recover", "retrieve", "search for", "look for", "discover", "collect", "gather"]
    if any(keyword in text for keyword in locate_keywords):
        return "locate"
    
    # Investigation keywords
    investigate_keywords = ["investigate", "figure out", "learn about", "research", "examine", "study", "uncover", "determine"]
    if any(keyword in text for keyword in investigate_keywords):
        return "investigate"
    
    # Default to generic
    return "generic"

def format_quest_summary(quest: dict) -> str:
    """Format a quest into a readable summary."""
    return f"""
Name: {quest.get('name', 'Unknown')}
ID: {quest.get('id', 'N/A')}
Entity ID: {quest.get('entity_id', 'N/A')}
Type: {quest.get('type') or 'None'}
Status: {_status_label(quest)}
Parent Quest ID: {quest.get('quest_id') or 'None'}
Instigator ID: {quest.get('instigator_id') or 'None'}
Location ID: {quest.get('location_id') or 'None'}
Tags: {len(quest.get('tags', []))} tag(s)
Is Private: {'Yes' if quest.get('is_private') else 'No'}
"""

def format_quest_detail(quest: dict) -> str:
    """Format a quest's full details."""
    calendar_info = ""
    if quest.get('calendar_year'):
        calendar_info = f"\nCalendar Date: Year {quest.get('calendar_year')}, Month {quest.get('calendar_month')}, Day {quest.get('calendar_day')}"
    
    return f"""
Name: {quest.get('name', 'Unknown')}
ID: {quest.get('id', 'N/A')}
Entity ID: {quest.get('entity_id', 'N/A')}
Type: {quest.get('type') or 'None'}
Status: {_status_label(quest)}
Parent Quest ID: {quest.get('quest_id') or 'None (Main Quest)'}
Instigator ID: {quest.get('instigator_id') or 'None'}
Location ID: {quest.get('location_id') or 'None'}
{calendar_info}

Entry/Description:
{quest.get('entry', 'No description available.')}

Tags: {quest.get('tags', [])}
Is Private: {'Yes' if quest.get('is_private') else 'No'}
Created: {quest.get('created_at')}
Last Updated: {quest.get('updated_at')}
"""

def register_quest_tools(mcp: FastMCP):
    """Register all quest-related tools with the MCP server."""
    
    @mcp.tool()
    async def get_all_quests() -> str:
        """Get a list of all quests in the campaign.
        
        Returns a summary of all quests including their name, ID, status, and basic info.
        """
        data = await make_kanka_request("quests")
        
        if not data:
            return "Unable to fetch quests."
        
        if "error" in data:
            return f"Error: {data['error']}"
        
        if "data" not in data or not data["data"]:
            return "No quests found in this campaign."
        
        quests = [format_quest_summary(quest) for quest in data["data"]]
        return "\n---\n".join(quests)

    @mcp.tool()
    async def get_quest(quest_id: int) -> str:
        """Get detailed information about a specific quest.
        
        Args:
            quest_id: The ID of the quest to retrieve
        """
        data = await make_kanka_request(f"quests/{quest_id}")
        
        if not data:
            return f"Unable to fetch quest with ID {quest_id}."
        
        if "error" in data:
            return f"Error: {data['error']}"
        
        if "data" not in data:
            return f"No quest found with ID {quest_id}."
        
        return format_quest_detail(data["data"])

    @mcp.tool()
    async def create_quest(
        name: str,
        entry: str = "",
        quest_type: str = "",
        status_id: int = None,
        parent_quest_id: int = None,
        instigator_id: int = None,
        location_id: int = None,
        entity_image_uuid: str = None,
        is_private: bool = False
    ) -> str:
        """Create a new quest in the campaign.

        Args:
            name: The quest's name (required)
            entry: HTML description of the quest
            quest_type: Quest type (e.g., "Main", "Side", "Personal")
            status_id: ID of a campaign category_status (e.g. not_started/ongoing/
                completed/abandoned). Use get_statuses_for("quest") to discover
                valid IDs. Passing the default "completed" id (10)
                also auto-applies the checkmark image.
            parent_quest_id: ID of the parent quest (for sub-quests)
            instigator_id: ID of the entity that gave/started this quest
            location_id: ID of the quest's starting location
            entity_image_uuid: Gallery image UUID for the quest image (overrides
                auto-detection)
            is_private: Whether the quest is only visible to admins
        """
        quest_data = {
            "name": name,
            "entry": entry,
            "type": quest_type,
            "is_private": is_private
        }

        if status_id is not None:
            quest_data["status_id"] = status_id

        # Auto-assign image: explicit override wins, else completed-checkmark for
        # the default "completed" status, else heuristic type detection.
        if entity_image_uuid is not None:
            quest_data["entity_image_uuid"] = entity_image_uuid
        elif status_id == QUEST_COMPLETED_STATUS_ID:
            quest_data["entity_image_uuid"] = QUEST_IMAGES["completed"]
        else:
            detected_type = detect_quest_type(name, entry)
            quest_data["entity_image_uuid"] = QUEST_IMAGES[detected_type]

        # Only include optional IDs if provided
        if parent_quest_id is not None:
            quest_data["quest_id"] = parent_quest_id
        if instigator_id is not None:
            quest_data["instigator_id"] = instigator_id
        if location_id is not None:
            quest_data["location_id"] = location_id
        
        # Remove empty string values to keep the request clean
        quest_data = {k: v for k, v in quest_data.items() if v != ""}
        
        result = await create_kanka_entity("quests", quest_data)
        
        if not result:
            return "Failed to create quest."
        
        if "error" in result:
            return f"Error creating quest: {result['error']}"
        
        if "data" in result:
            quest = result["data"]
            return f"""
Successfully created quest!

Name: {quest.get('name')}
Quest ID: {quest.get('id')}
Entity ID: {quest.get('entity_id')}
Type: {quest.get('type') or 'None'}
Status: {_status_label(quest)}
Parent Quest ID: {quest.get('quest_id') or 'None'}
Instigator ID: {quest.get('instigator_id') or 'None'}
Location ID: {quest.get('location_id') or 'None'}
Visibility: {'Private' if quest.get('is_private') else 'Public'}

The quest has been added to your campaign.
"""
        
        return "Quest created, but unexpected response format."

    @mcp.tool()
    async def update_quest(
        quest_name: str,
        entry: str = None,
        quest_type: str = None,
        status_id: int = None,
        parent_quest_id: int = None,
        instigator_id: int = None,
        location_id: int = None,
        entity_image_uuid: str = None,
        is_private: bool = None
    ) -> str:
        """Update an existing quest by name.

        First searches for the quest by name, then updates the specified fields.
        Only provided fields will be updated - others remain unchanged.

        Args:
            quest_name: The name of the quest to update (used for search)
            entry: HTML description of the quest
            quest_type: Quest type (e.g., "Main", "Side", "Personal")
            status_id: ID of a campaign category_status (e.g. not_started/ongoing/
                completed/abandoned). Use get_statuses_for("quest") to discover
                valid IDs. Passing the default "completed" id (10)
                also auto-applies the checkmark image unless entity_image_uuid is set.
            parent_quest_id: ID of the parent quest (for sub-quests)
            instigator_id: ID of the entity that gave/started this quest
            location_id: ID of the quest's starting location
            entity_image_uuid: Gallery image UUID for the quest image (overrides
                auto-detection)
            is_private: Whether the quest is only visible to admins
        """
        # First, search for the quest by name
        quests_data = await make_kanka_request("quests")

        if not quests_data:
            return f"Unable to search for quest '{quest_name}'."
        if "error" in quests_data:
            return f"Error searching for quest: {quests_data['error']}"
        if "data" not in quests_data:
            return f"Unexpected response searching for quest '{quest_name}'."
        
        # Find quest with matching name (case-insensitive)
        target_quest = None
        for quest in quests_data["data"]:
            if quest.get("name", "").lower() == quest_name.lower():
                target_quest = quest
                break
        
        if not target_quest:
            return f"Quest '{quest_name}' not found in campaign."
        
        quest_id = target_quest["id"]
        
        # Build update data with only provided values
        update_data = {}
        if entry is not None:
            update_data["entry"] = entry
        if quest_type is not None:
            update_data["type"] = quest_type
        if status_id is not None:
            update_data["status_id"] = status_id
        if parent_quest_id is not None:
            update_data["quest_id"] = parent_quest_id
        if instigator_id is not None:
            update_data["instigator_id"] = instigator_id
        if location_id is not None:
            update_data["location_id"] = location_id
        if is_private is not None:
            update_data["is_private"] = is_private

        # Image logic: explicit override wins; else swap to checkmark when status
        # is transitioning to the default "completed"; else, if status is moving
        # away from "completed", re-detect from quest name/entry.
        if entity_image_uuid is not None:
            update_data["entity_image_uuid"] = entity_image_uuid
        elif status_id == QUEST_COMPLETED_STATUS_ID:
            update_data["entity_image_uuid"] = QUEST_IMAGES["completed"]
        elif status_id is not None and target_quest.get("status_id") == QUEST_COMPLETED_STATUS_ID:
            current_name = target_quest.get("name", "")
            current_entry = target_quest.get("entry", "")
            final_entry = entry if entry is not None else current_entry
            detected_type = detect_quest_type(current_name, final_entry)
            update_data["entity_image_uuid"] = QUEST_IMAGES[detected_type]
        
        if not update_data:
            return "No updates provided. Please specify at least one field to update."
        
        # Update the quest
        result = await update_kanka_entity(f"quests/{quest_id}", update_data)
        
        if not result:
            return f"Failed to update quest '{quest_name}'."
        
        if "error" in result:
            return f"Error updating quest: {result['error']}"
        
        if "data" in result:
            quest = result["data"]
            updated_fields = list(update_data.keys())
            return f"""
Successfully updated quest '{quest_name}'!

Name: {quest.get('name')}
ID: {quest.get('id')}
Type: {quest.get('type') or 'None'}
Status: {_status_label(quest)}
Parent Quest ID: {quest.get('quest_id') or 'None'}
Instigator ID: {quest.get('instigator_id') or 'None'}
Location ID: {quest.get('location_id') or 'None'}
Visibility: {'Private' if quest.get('is_private') else 'Public'}

Updated fields: {', '.join(updated_fields)}
"""
        
        return "Quest updated, but unexpected response format."