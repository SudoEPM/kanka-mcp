from mcp.server.fastmcp import FastMCP
from ..client import make_kanka_request, create_kanka_entity, update_kanka_entity

def format_creature_summary(creature: dict) -> str:
    """Format a creature into a readable summary."""
    status_parts = []
    if creature.get('is_extinct'):
        status_parts.append('Extinct')
    if creature.get('is_dead'):
        status_parts.append('Dead')
    status = ', '.join(status_parts) if status_parts else 'Alive'

    return f"""
Name: {creature.get('name', 'Unknown')}
ID: {creature.get('id', 'N/A')}
Entity ID: {creature.get('entity_id', 'N/A')}
Type: {creature.get('type') or 'None'}
Status: {status}
Parent Creature ID: {creature.get('creature_id') or 'None'}
Tags: {len(creature.get('tags', []))} tag(s)
Is Private: {'Yes' if creature.get('is_private') else 'No'}
"""

def format_creature_detail(creature: dict) -> str:
    """Format a creature's full details."""
    status_parts = []
    if creature.get('is_extinct'):
        status_parts.append('Extinct')
    if creature.get('is_dead'):
        status_parts.append('Dead')
    status = ', '.join(status_parts) if status_parts else 'Alive'

    return f"""
Name: {creature.get('name', 'Unknown')}
ID: {creature.get('id', 'N/A')}
Entity ID: {creature.get('entity_id', 'N/A')}
Type: {creature.get('type') or 'None'}
Status: {status}
Parent Creature ID: {creature.get('creature_id') or 'None (Top-level creature)'}

Entry/Description:
{creature.get('entry', 'No description available.')}

Tags: {creature.get('tags', [])}
Locations: {creature.get('locations', [])}
Is Private: {'Yes' if creature.get('is_private') else 'No'}
Created: {creature.get('created_at')}
Last Updated: {creature.get('updated_at')}
"""

def register_creature_tools(mcp: FastMCP):
    """Register all creature-related tools with the MCP server."""

    @mcp.tool()
    async def get_all_creatures() -> str:
        """Get a list of all creatures in the campaign.

        Returns a summary of all creatures including their name, ID, type, and basic info.
        """
        data = await make_kanka_request("creatures")

        if not data:
            return "Unable to fetch creatures."

        if "error" in data:
            return f"Error: {data['error']}"

        if "data" not in data or not data["data"]:
            return "No creatures found in this campaign."

        creatures = [format_creature_summary(creature) for creature in data["data"]]
        return "\n---\n".join(creatures)

    @mcp.tool()
    async def get_creature(creature_id: int) -> str:
        """Get detailed information about a specific creature.

        Args:
            creature_id: The ID of the creature to retrieve
        """
        data = await make_kanka_request(f"creatures/{creature_id}")

        if not data:
            return f"Unable to fetch creature with ID {creature_id}."

        if "error" in data:
            return f"Error: {data['error']}"

        if "data" not in data:
            return f"No creature found with ID {creature_id}."

        return format_creature_detail(data["data"])

    @mcp.tool()
    async def create_creature(
        name: str,
        entry: str = "",
        creature_type: str = "",
        is_extinct: bool = False,
        is_dead: bool = False,
        parent_creature_id: int = None,
        entity_image_uuid: str = None,
        is_private: bool = False
    ) -> str:
        """Create a new creature in the campaign.

        Args:
            name: The creature's name (required)
            entry: HTML description of the creature
            creature_type: Creature type (e.g., "Dragon", "Beast", "Humanoid", "Undead")
            is_extinct: Whether the creature species is extinct
            is_dead: Whether this specific creature is dead
            parent_creature_id: ID of the parent creature (for sub-species or variants)
            entity_image_uuid: Gallery image UUID for the creature image
            is_private: Whether the creature is only visible to admins
        """
        creature_data = {
            "name": name,
            "entry": entry,
            "type": creature_type,
            "is_extinct": is_extinct,
            "is_dead": is_dead,
            "is_private": is_private
        }

        # Only include optional fields if provided
        if parent_creature_id is not None:
            creature_data["creature_id"] = parent_creature_id
        if entity_image_uuid is not None:
            creature_data["entity_image_uuid"] = entity_image_uuid

        # Remove empty string values to keep the request clean
        creature_data = {k: v for k, v in creature_data.items() if v != ""}

        result = await create_kanka_entity("creatures", creature_data)

        if not result:
            return "Failed to create creature."

        if "error" in result:
            return f"Error creating creature: {result['error']}"

        if "data" in result:
            creature = result["data"]
            status_parts = []
            if creature.get('is_extinct'):
                status_parts.append('Extinct')
            if creature.get('is_dead'):
                status_parts.append('Dead')
            status = ', '.join(status_parts) if status_parts else 'Alive'

            return f"""
Successfully created creature!

Name: {creature.get('name')}
Creature ID: {creature.get('id')}
Entity ID: {creature.get('entity_id')}
Type: {creature.get('type') or 'None'}
Status: {status}
Parent Creature ID: {creature.get('creature_id') or 'None'}
Visibility: {'Private' if creature.get('is_private') else 'Public'}

The creature has been added to your campaign.
"""

        return "Creature created, but unexpected response format."

    @mcp.tool()
    async def update_creature(
        creature_name: str,
        entry: str = None,
        creature_type: str = None,
        is_extinct: bool = None,
        is_dead: bool = None,
        parent_creature_id: int = None,
        entity_image_uuid: str = None,
        is_private: bool = None
    ) -> str:
        """Update an existing creature by name.

        First searches for the creature by name, then updates the specified fields.
        Only provided fields will be updated - others remain unchanged.

        Args:
            creature_name: The name of the creature to update (used for search)
            entry: HTML description of the creature
            creature_type: Creature type (e.g., "Dragon", "Beast", "Humanoid", "Undead")
            is_extinct: Whether the creature species is extinct
            is_dead: Whether this specific creature is dead
            parent_creature_id: ID of the parent creature (for sub-species or variants)
            entity_image_uuid: Gallery image UUID for the creature image
            is_private: Whether the creature is only visible to admins
        """
        # First, search for the creature by name
        creatures_data = await make_kanka_request("creatures")

        if not creatures_data or "data" not in creatures_data:
            return f"Unable to search for creature '{creature_name}'."

        if "error" in creatures_data:
            return f"Error searching for creature: {creatures_data['error']}"

        # Find creature with matching name (case-insensitive)
        target_creature = None
        for creature in creatures_data["data"]:
            if creature.get("name", "").lower() == creature_name.lower():
                target_creature = creature
                break

        if not target_creature:
            return f"Creature '{creature_name}' not found in campaign."

        creature_id = target_creature["id"]

        # Build update data with only provided values
        update_data = {}
        if entry is not None:
            update_data["entry"] = entry
        if creature_type is not None:
            update_data["type"] = creature_type
        if is_extinct is not None:
            update_data["is_extinct"] = is_extinct
        if is_dead is not None:
            update_data["is_dead"] = is_dead
        if parent_creature_id is not None:
            update_data["creature_id"] = parent_creature_id
        if entity_image_uuid is not None:
            update_data["entity_image_uuid"] = entity_image_uuid
        if is_private is not None:
            update_data["is_private"] = is_private

        if not update_data:
            return "No updates provided. Please specify at least one field to update."

        # Update the creature
        result = await update_kanka_entity(f"creatures/{creature_id}", update_data)

        if not result:
            return f"Failed to update creature '{creature_name}'."

        if "error" in result:
            return f"Error updating creature: {result['error']}"

        if "data" in result:
            creature = result["data"]
            updated_fields = list(update_data.keys())
            status_parts = []
            if creature.get('is_extinct'):
                status_parts.append('Extinct')
            if creature.get('is_dead'):
                status_parts.append('Dead')
            status = ', '.join(status_parts) if status_parts else 'Alive'

            return f"""
Successfully updated creature '{creature_name}'!

Name: {creature.get('name')}
ID: {creature.get('id')}
Type: {creature.get('type') or 'None'}
Status: {status}
Parent Creature ID: {creature.get('creature_id') or 'None'}
Visibility: {'Private' if creature.get('is_private') else 'Public'}

Updated fields: {', '.join(updated_fields)}
"""

        return "Creature updated, but unexpected response format."
