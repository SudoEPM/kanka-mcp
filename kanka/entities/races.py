from mcp.server.fastmcp import FastMCP
from ..client import make_kanka_request, create_kanka_entity, update_kanka_entity

def _status_label(entity: dict) -> str:
    status = entity.get('status') or {}
    key = status.get('key')
    status_id = entity.get('status_id')
    if key and status_id:
        return f"{key} (status_id={status_id})"
    if status_id:
        return f"status_id={status_id}"
    return 'None'

def format_race_summary(race: dict) -> str:
    """Format a race into a readable summary."""
    return f"""
Name: {race.get('name', 'Unknown')}
ID: {race.get('id', 'N/A')}
Entity ID: {race.get('entity_id', 'N/A')}
Type: {race.get('type') or 'None'}
Status: {_status_label(race)}
Parent Race ID: {race.get('race_id') or 'None'}
Locations: {len(race.get('locations', []))} location(s)
Tags: {len(race.get('tags', []))} tag(s)
Is Private: {'Yes' if race.get('is_private') else 'No'}
"""

def format_race_detail(race: dict) -> str:
    """Format a race's full details."""
    return f"""
Name: {race.get('name', 'Unknown')}
ID: {race.get('id', 'N/A')}
Entity ID: {race.get('entity_id', 'N/A')}
Type: {race.get('type') or 'None'}
Status: {_status_label(race)}
Parent Race ID: {race.get('race_id') or 'None (Top-level race)'}

Entry/Description:
{race.get('entry', 'No description available.')}

Locations: {race.get('locations', [])}
Tags: {race.get('tags', [])}
Is Private: {'Yes' if race.get('is_private') else 'No'}
Created: {race.get('created_at')}
Last Updated: {race.get('updated_at')}
"""

def register_race_tools(mcp: FastMCP):
    """Register all race-related tools with the MCP server."""

    @mcp.tool()
    async def get_all_races() -> str:
        """Get a list of all races in the campaign."""
        data = await make_kanka_request("races")

        if not data:
            return "Unable to fetch races."
        if "error" in data:
            return f"Error: {data['error']}"
        if "data" not in data or not data["data"]:
            return "No races found in this campaign."

        races = [format_race_summary(r) for r in data["data"]]
        return "\n---\n".join(races)

    @mcp.tool()
    async def get_race(race_id: int) -> str:
        """Get detailed information about a specific race.

        Args:
            race_id: The ID of the race to retrieve
        """
        data = await make_kanka_request(f"races/{race_id}")

        if not data:
            return f"Unable to fetch race with ID {race_id}."
        if "error" in data:
            return f"Error: {data['error']}"
        if "data" not in data:
            return f"No race found with ID {race_id}."

        return format_race_detail(data["data"])

    @mcp.tool()
    async def create_race(
        name: str,
        entry: str = "",
        race_type: str = "",
        status_id: int = None,
        parent_race_id: int = None,
        location_ids: list[int] = None,
        entity_image_uuid: str = None,
        is_private: bool = False
    ) -> str:
        """Create a new race in the campaign.

        Args:
            name: The race's name (required)
            entry: HTML description of the race
            race_type: Race type (e.g., "Humanoid", "Dragonborn subrace")
            status_id: ID of a campaign category_status (e.g. extinct). Use
                get_statuses_for("race") to discover valid IDs.
            parent_race_id: ID of the parent race (for subraces)
            location_ids: List of location IDs where this race is found
            entity_image_uuid: Gallery image UUID for the race image
            is_private: Whether the race is only visible to admins
        """
        race_data = {
            "name": name,
            "entry": entry,
            "type": race_type,
            "is_private": is_private
        }

        if status_id is not None:
            race_data["status_id"] = status_id
        if parent_race_id is not None:
            race_data["race_id"] = parent_race_id
        if location_ids is not None:
            race_data["locations"] = location_ids
        if entity_image_uuid is not None:
            race_data["entity_image_uuid"] = entity_image_uuid

        race_data = {k: v for k, v in race_data.items() if v != ""}

        result = await create_kanka_entity("races", race_data)

        if not result:
            return "Failed to create race."
        if "error" in result:
            return f"Error creating race: {result['error']}"

        if "data" in result:
            race = result["data"]
            return f"""
Successfully created race!

Name: {race.get('name')}
Race ID: {race.get('id')}
Entity ID: {race.get('entity_id')}
Type: {race.get('type') or 'None'}
Status: {_status_label(race)}
Parent Race ID: {race.get('race_id') or 'None'}
Locations: {len(race.get('locations', []))} location(s)
Visibility: {'Private' if race.get('is_private') else 'Public'}

The race has been added to your campaign.
"""

        return "Race created, but unexpected response format."

    @mcp.tool()
    async def update_race(
        race_name: str,
        entry: str = None,
        race_type: str = None,
        status_id: int = None,
        parent_race_id: int = None,
        location_ids: list[int] = None,
        entity_image_uuid: str = None,
        is_private: bool = None
    ) -> str:
        """Update an existing race by name.

        Args:
            race_name: The name of the race to update (used for search)
            entry: HTML description of the race
            race_type: Race type
            status_id: ID of a campaign category_status. Use
                get_statuses_for("race") to discover valid IDs.
            parent_race_id: ID of the parent race
            location_ids: List of location IDs (replaces existing)
            entity_image_uuid: Gallery image UUID
            is_private: Whether the race is only visible to admins
        """
        races_data = await make_kanka_request("races")

        if not races_data:
            return f"Unable to search for race '{race_name}'."
        if "error" in races_data:
            return f"Error searching for race: {races_data['error']}"
        if "data" not in races_data:
            return f"Unexpected response searching for race '{race_name}'."

        target_race = None
        for r in races_data["data"]:
            if r.get("name", "").lower() == race_name.lower():
                target_race = r
                break

        if not target_race:
            return f"Race '{race_name}' not found in campaign."

        race_id = target_race["id"]

        update_data = {}
        if entry is not None:
            update_data["entry"] = entry
        if race_type is not None:
            update_data["type"] = race_type
        if status_id is not None:
            update_data["status_id"] = status_id
        if parent_race_id is not None:
            update_data["race_id"] = parent_race_id
        if location_ids is not None:
            update_data["locations"] = location_ids
        if entity_image_uuid is not None:
            update_data["entity_image_uuid"] = entity_image_uuid
        if is_private is not None:
            update_data["is_private"] = is_private

        if not update_data:
            return "No updates provided. Please specify at least one field to update."

        result = await update_kanka_entity(f"races/{race_id}", update_data)

        if not result:
            return f"Failed to update race '{race_name}'."
        if "error" in result:
            return f"Error updating race: {result['error']}"

        if "data" in result:
            race = result["data"]
            updated_fields = list(update_data.keys())
            return f"""
Successfully updated race '{race_name}'!

Name: {race.get('name')}
ID: {race.get('id')}
Type: {race.get('type') or 'None'}
Status: {_status_label(race)}
Parent Race ID: {race.get('race_id') or 'None'}
Locations: {len(race.get('locations', []))} location(s)
Visibility: {'Private' if race.get('is_private') else 'Public'}

Updated fields: {', '.join(updated_fields)}
"""

        return "Race updated, but unexpected response format."
