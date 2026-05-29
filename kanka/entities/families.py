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

def format_family_summary(family: dict) -> str:
    """Format a family into a readable summary."""
    return f"""
Name: {family.get('name', 'Unknown')}
ID: {family.get('id', 'N/A')}
Entity ID: {family.get('entity_id', 'N/A')}
Type: {family.get('type') or 'None'}
Status: {_status_label(family)}
Parent Family ID: {family.get('family_id') or 'None'}
Location ID: {family.get('location_id') or 'None'}
Members: {len(family.get('members', []))} member(s)
Tags: {len(family.get('tags', []))} tag(s)
Is Private: {'Yes' if family.get('is_private') else 'No'}
"""

def format_family_detail(family: dict) -> str:
    """Format a family's full details."""
    return f"""
Name: {family.get('name', 'Unknown')}
ID: {family.get('id', 'N/A')}
Entity ID: {family.get('entity_id', 'N/A')}
Type: {family.get('type') or 'None'}
Status: {_status_label(family)}
Parent Family ID: {family.get('family_id') or 'None (Top-level family)'}
Location ID: {family.get('location_id') or 'None'}

Entry/Description:
{family.get('entry', 'No description available.')}

Members: {family.get('members', [])}
Tags: {family.get('tags', [])}
Is Private: {'Yes' if family.get('is_private') else 'No'}
Created: {family.get('created_at')}
Last Updated: {family.get('updated_at')}
"""

def register_family_tools(mcp: FastMCP):
    """Register all family-related tools with the MCP server."""

    @mcp.tool()
    async def get_all_families() -> str:
        """Get a list of all families in the campaign."""
        data = await make_kanka_request("families")

        if not data:
            return "Unable to fetch families."
        if "error" in data:
            return f"Error: {data['error']}"
        if "data" not in data or not data["data"]:
            return "No families found in this campaign."

        families = [format_family_summary(f) for f in data["data"]]
        return "\n---\n".join(families)

    @mcp.tool()
    async def get_family(family_id: int) -> str:
        """Get detailed information about a specific family.

        Args:
            family_id: The ID of the family to retrieve
        """
        data = await make_kanka_request(f"families/{family_id}")

        if not data:
            return f"Unable to fetch family with ID {family_id}."
        if "error" in data:
            return f"Error: {data['error']}"
        if "data" not in data:
            return f"No family found with ID {family_id}."

        return format_family_detail(data["data"])

    @mcp.tool()
    async def create_family(
        name: str,
        entry: str = "",
        family_type: str = "",
        status_id: int = None,
        parent_family_id: int = None,
        location_id: int = None,
        entity_image_uuid: str = None,
        is_private: bool = False
    ) -> str:
        """Create a new family in the campaign.

        Args:
            name: The family's name (required)
            entry: HTML description of the family
            family_type: Family type (e.g., "Noble House", "Clan", "Dynasty")
            status_id: ID of a campaign category_status (e.g. extinct). Use
                get_statuses_for("family") to discover valid IDs.
            parent_family_id: ID of the parent family (for cadet branches)
            location_id: ID of the family's seat/home location
            entity_image_uuid: Gallery image UUID for the family image
            is_private: Whether the family is only visible to admins
        """
        family_data = {
            "name": name,
            "entry": entry,
            "type": family_type,
            "is_private": is_private
        }

        if status_id is not None:
            family_data["status_id"] = status_id
        if parent_family_id is not None:
            family_data["family_id"] = parent_family_id
        if location_id is not None:
            family_data["location_id"] = location_id
        if entity_image_uuid is not None:
            family_data["entity_image_uuid"] = entity_image_uuid

        family_data = {k: v for k, v in family_data.items() if v != ""}

        result = await create_kanka_entity("families", family_data)

        if not result:
            return "Failed to create family."
        if "error" in result:
            return f"Error creating family: {result['error']}"

        if "data" in result:
            family = result["data"]
            return f"""
Successfully created family!

Name: {family.get('name')}
Family ID: {family.get('id')}
Entity ID: {family.get('entity_id')}
Type: {family.get('type') or 'None'}
Status: {_status_label(family)}
Parent Family ID: {family.get('family_id') or 'None'}
Location ID: {family.get('location_id') or 'None'}
Visibility: {'Private' if family.get('is_private') else 'Public'}

The family has been added to your campaign.
"""

        return "Family created, but unexpected response format."

    @mcp.tool()
    async def update_family(
        family_name: str,
        entry: str = None,
        family_type: str = None,
        status_id: int = None,
        parent_family_id: int = None,
        location_id: int = None,
        entity_image_uuid: str = None,
        is_private: bool = None
    ) -> str:
        """Update an existing family by name.

        Args:
            family_name: The name of the family to update (used for search)
            entry: HTML description of the family
            family_type: Family type
            status_id: ID of a campaign category_status. Use
                get_statuses_for("family") to discover valid IDs.
            parent_family_id: ID of the parent family
            location_id: ID of the family's seat/home location
            entity_image_uuid: Gallery image UUID
            is_private: Whether the family is only visible to admins
        """
        families_data = await make_kanka_request("families")

        if not families_data:
            return f"Unable to search for family '{family_name}'."
        if "error" in families_data:
            return f"Error searching for family: {families_data['error']}"
        if "data" not in families_data:
            return f"Unexpected response searching for family '{family_name}'."

        target_family = None
        for f in families_data["data"]:
            if f.get("name", "").lower() == family_name.lower():
                target_family = f
                break

        if not target_family:
            return f"Family '{family_name}' not found in campaign."

        family_id = target_family["id"]

        update_data = {}
        if entry is not None:
            update_data["entry"] = entry
        if family_type is not None:
            update_data["type"] = family_type
        if status_id is not None:
            update_data["status_id"] = status_id
        if parent_family_id is not None:
            update_data["family_id"] = parent_family_id
        if location_id is not None:
            update_data["location_id"] = location_id
        if entity_image_uuid is not None:
            update_data["entity_image_uuid"] = entity_image_uuid
        if is_private is not None:
            update_data["is_private"] = is_private

        if not update_data:
            return "No updates provided. Please specify at least one field to update."

        result = await update_kanka_entity(f"families/{family_id}", update_data)

        if not result:
            return f"Failed to update family '{family_name}'."
        if "error" in result:
            return f"Error updating family: {result['error']}"

        if "data" in result:
            family = result["data"]
            updated_fields = list(update_data.keys())
            return f"""
Successfully updated family '{family_name}'!

Name: {family.get('name')}
ID: {family.get('id')}
Type: {family.get('type') or 'None'}
Status: {_status_label(family)}
Parent Family ID: {family.get('family_id') or 'None'}
Location ID: {family.get('location_id') or 'None'}
Visibility: {'Private' if family.get('is_private') else 'Public'}

Updated fields: {', '.join(updated_fields)}
"""

        return "Family updated, but unexpected response format."
