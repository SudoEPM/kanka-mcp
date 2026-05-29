from mcp.server.fastmcp import FastMCP
from ..client import make_kanka_request, create_kanka_entity, update_kanka_entity

def format_ability_summary(ability: dict) -> str:
    """Format an ability into a readable summary."""
    return f"""
Name: {ability.get('name', 'Unknown')}
ID: {ability.get('id', 'N/A')}
Entity ID: {ability.get('entity_id', 'N/A')}
Type: {ability.get('type') or 'None'}
Charges: {ability.get('charges') or 'None'}
Parent Ability ID: {ability.get('ability_id') or 'None'}
Tags: {len(ability.get('tags', []))} tag(s)
Is Private: {'Yes' if ability.get('is_private') else 'No'}
"""

def format_ability_detail(ability: dict) -> str:
    """Format an ability's full details."""
    return f"""
Name: {ability.get('name', 'Unknown')}
ID: {ability.get('id', 'N/A')}
Entity ID: {ability.get('entity_id', 'N/A')}
Type: {ability.get('type') or 'None'}
Charges: {ability.get('charges') or 'None'}
Parent Ability ID: {ability.get('ability_id') or 'None (Top-level ability)'}

Entry/Description:
{ability.get('entry', 'No description available.')}

Tags: {ability.get('tags', [])}
Is Private: {'Yes' if ability.get('is_private') else 'No'}
Created: {ability.get('created_at')}
Last Updated: {ability.get('updated_at')}
"""

def register_ability_tools(mcp: FastMCP):
    """Register all ability-related tools with the MCP server."""

    @mcp.tool()
    async def get_all_abilities() -> str:
        """Get a list of all abilities in the campaign."""
        data = await make_kanka_request("abilities")

        if not data:
            return "Unable to fetch abilities."
        if "error" in data:
            return f"Error: {data['error']}"
        if "data" not in data or not data["data"]:
            return "No abilities found in this campaign."

        abilities = [format_ability_summary(a) for a in data["data"]]
        return "\n---\n".join(abilities)

    @mcp.tool()
    async def get_ability(ability_id: int) -> str:
        """Get detailed information about a specific ability.

        Args:
            ability_id: The ID of the ability to retrieve
        """
        data = await make_kanka_request(f"abilities/{ability_id}")

        if not data:
            return f"Unable to fetch ability with ID {ability_id}."
        if "error" in data:
            return f"Error: {data['error']}"
        if "data" not in data:
            return f"No ability found with ID {ability_id}."

        return format_ability_detail(data["data"])

    @mcp.tool()
    async def create_ability(
        name: str,
        entry: str = "",
        ability_type: str = "",
        charges: str = "",
        parent_ability_id: int = None,
        entity_image_uuid: str = None,
        is_private: bool = False
    ) -> str:
        """Create a new ability in the campaign.

        Abilities cover spells, feats, class features, racial traits — any
        reusable mechanical effect. Classification is by the free-text `type`
        field rather than a fixed taxonomy.

        Args:
            name: The ability's name (required)
            entry: HTML description of the ability
            ability_type: Ability classification (e.g., "Spell", "Feat", "Racial")
            charges: Free-text charge capacity (e.g., "3/day", "1 per short rest")
            parent_ability_id: ID of the parent ability (for variants/upgrades)
            entity_image_uuid: Gallery image UUID for the ability image
            is_private: Whether the ability is only visible to admins
        """
        ability_data = {
            "name": name,
            "entry": entry,
            "type": ability_type,
            "charges": charges,
            "is_private": is_private
        }

        if parent_ability_id is not None:
            ability_data["ability_id"] = parent_ability_id
        if entity_image_uuid is not None:
            ability_data["entity_image_uuid"] = entity_image_uuid

        ability_data = {k: v for k, v in ability_data.items() if v != ""}

        result = await create_kanka_entity("abilities", ability_data)

        if not result:
            return "Failed to create ability."
        if "error" in result:
            return f"Error creating ability: {result['error']}"

        if "data" in result:
            ability = result["data"]
            return f"""
Successfully created ability!

Name: {ability.get('name')}
Ability ID: {ability.get('id')}
Entity ID: {ability.get('entity_id')}
Type: {ability.get('type') or 'None'}
Charges: {ability.get('charges') or 'None'}
Parent Ability ID: {ability.get('ability_id') or 'None'}
Visibility: {'Private' if ability.get('is_private') else 'Public'}

The ability has been added to your campaign.
"""

        return "Ability created, but unexpected response format."

    @mcp.tool()
    async def update_ability(
        ability_name: str,
        entry: str = None,
        ability_type: str = None,
        charges: str = None,
        parent_ability_id: int = None,
        entity_image_uuid: str = None,
        is_private: bool = None
    ) -> str:
        """Update an existing ability by name.

        Args:
            ability_name: The name of the ability to update (used for search)
            entry: HTML description of the ability
            ability_type: Ability classification
            charges: Free-text charge capacity
            parent_ability_id: ID of the parent ability
            entity_image_uuid: Gallery image UUID
            is_private: Whether the ability is only visible to admins
        """
        abilities_data = await make_kanka_request("abilities")

        if not abilities_data or "data" not in abilities_data:
            return f"Unable to search for ability '{ability_name}'."
        if "error" in abilities_data:
            return f"Error searching for ability: {abilities_data['error']}"

        target_ability = None
        for a in abilities_data["data"]:
            if a.get("name", "").lower() == ability_name.lower():
                target_ability = a
                break

        if not target_ability:
            return f"Ability '{ability_name}' not found in campaign."

        ability_id = target_ability["id"]

        update_data = {}
        if entry is not None:
            update_data["entry"] = entry
        if ability_type is not None:
            update_data["type"] = ability_type
        if charges is not None:
            update_data["charges"] = charges
        if parent_ability_id is not None:
            update_data["ability_id"] = parent_ability_id
        if entity_image_uuid is not None:
            update_data["entity_image_uuid"] = entity_image_uuid
        if is_private is not None:
            update_data["is_private"] = is_private

        if not update_data:
            return "No updates provided. Please specify at least one field to update."

        result = await update_kanka_entity(f"abilities/{ability_id}", update_data)

        if not result:
            return f"Failed to update ability '{ability_name}'."
        if "error" in result:
            return f"Error updating ability: {result['error']}"

        if "data" in result:
            ability = result["data"]
            updated_fields = list(update_data.keys())
            return f"""
Successfully updated ability '{ability_name}'!

Name: {ability.get('name')}
ID: {ability.get('id')}
Type: {ability.get('type') or 'None'}
Charges: {ability.get('charges') or 'None'}
Parent Ability ID: {ability.get('ability_id') or 'None'}
Visibility: {'Private' if ability.get('is_private') else 'Public'}

Updated fields: {', '.join(updated_fields)}
"""

        return "Ability updated, but unexpected response format."
