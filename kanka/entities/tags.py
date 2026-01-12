from mcp.server.fastmcp import FastMCP
from ..client import make_kanka_request, create_kanka_entity, update_kanka_entity

def format_tag_summary(tag: dict) -> str:
    """Format a tag into a readable summary."""
    return f"""
Name: {tag.get('name', 'Unknown')}
ID: {tag.get('id', 'N/A')}
Entity ID: {tag.get('entity_id', 'N/A')}
Type: {tag.get('type') or 'None'}
Colour: {tag.get('colour') or 'None'}
Parent Tag ID: {tag.get('tag_id') or 'None'}
Is Hidden: {'Yes' if tag.get('is_hidden') else 'No'}
Auto-Applied: {'Yes' if tag.get('is_auto_applied') else 'No'}
"""

def format_tag_detail(tag: dict) -> str:
    """Format a tag's full details."""
    return f"""
Name: {tag.get('name', 'Unknown')}
ID: {tag.get('id', 'N/A')}
Entity ID: {tag.get('entity_id', 'N/A')}
Type: {tag.get('type') or 'None'}
Colour: {tag.get('colour') or 'None'}
Parent Tag ID: {tag.get('tag_id') or 'None'}
Is Hidden: {'Yes' if tag.get('is_hidden') else 'No'}
Auto-Applied: {'Yes' if tag.get('is_auto_applied') else 'No'}
Visibility: {'Private' if tag.get('is_private') else 'Public'}

Entry/Description:
{tag.get('entry', 'No description available.')}

Tooltip: {tag.get('tooltip') or 'None'}
Tags: {tag.get('tags', [])}
"""

def register_tag_tools(mcp: FastMCP):
    """Register all tag-related tools with the MCP server."""

    @mcp.tool()
    async def get_all_tags() -> str:
        """Get a list of all tags in the campaign.

        Returns a summary of all tags including their name, ID, and basic info.
        """
        data = await make_kanka_request("tags")

        if not data:
            return "Unable to fetch tags."

        if "error" in data:
            return f"Error: {data['error']}"

        if "data" not in data or not data["data"]:
            return "No tags found in this campaign."

        tags = [format_tag_summary(tag) for tag in data["data"]]
        return "\n---\n".join(tags)

    @mcp.tool()
    async def get_tag(tag_id: int) -> str:
        """Get detailed information about a specific tag.

        Args:
            tag_id: The ID of the tag to retrieve
        """
        data = await make_kanka_request(f"tags/{tag_id}")

        if not data:
            return f"Unable to fetch tag with ID {tag_id}."

        if "error" in data:
            return f"Error: {data['error']}"

        if "data" not in data:
            return f"No tag found with ID {tag_id}."

        return format_tag_detail(data["data"])

    @mcp.tool()
    async def create_tag(
        name: str,
        entry: str = "",
        tag_type: str = "",
        colour: str = "",
        tag_id: int = None,
        is_hidden: bool = False,
        is_auto_applied: bool = False,
        is_private: bool = False,
        tooltip: str = ""
    ) -> str:
        """Create a new tag in the campaign.

        Args:
            name: The tag's name (required)
            entry: HTML description of the tag
            tag_type: Tag classification/type
            colour: Visual color for the tag (e.g., hex code or color name)
            tag_id: Parent tag ID if this is a sub-tag
            is_hidden: Whether to hide this tag from entity displays
            is_auto_applied: Whether to automatically assign this tag to new entities
            is_private: Whether the tag is only visible to admins
            tooltip: Hover text for the tag (premium feature)
        """
        tag_data = {
            "name": name,
            "entry": entry,
            "type": tag_type,
            "colour": colour,
            "is_hidden": is_hidden,
            "is_auto_applied": is_auto_applied,
            "is_private": is_private,
            "tooltip": tooltip
        }

        # Only include tag_id if provided
        if tag_id is not None:
            tag_data["tag_id"] = tag_id

        # Remove empty string values to keep the request clean
        tag_data = {k: v for k, v in tag_data.items() if v != ""}

        result = await create_kanka_entity("tags", tag_data)

        if not result:
            return "Failed to create tag."

        if "error" in result:
            return f"Error creating tag: {result['error']}"

        if "data" in result:
            tag = result["data"]
            return f"""
Successfully created tag!

Name: {tag.get('name')}
Tag ID: {tag.get('id')}
Entity ID: {tag.get('entity_id')}
Type: {tag.get('type') or 'None'}
Colour: {tag.get('colour') or 'None'}
Parent Tag ID: {tag.get('tag_id') or 'None'}
Is Hidden: {'Yes' if tag.get('is_hidden') else 'No'}
Auto-Applied: {'Yes' if tag.get('is_auto_applied') else 'No'}
Visibility: {'Private' if tag.get('is_private') else 'Public'}

The tag has been added to your campaign.
"""

        return "Tag created, but unexpected response format."

    @mcp.tool()
    async def update_tag(
        tag_name: str,
        entry: str = None,
        tag_type: str = None,
        colour: str = None,
        tag_id: int = None,
        is_hidden: bool = None,
        is_auto_applied: bool = None,
        is_private: bool = None,
        tooltip: str = None
    ) -> str:
        """Update an existing tag by name.

        First searches for the tag by name, then updates the specified fields.
        Only provided fields will be updated - others remain unchanged.

        Args:
            tag_name: The name of the tag to update (used for search)
            entry: HTML description of the tag
            tag_type: Tag classification/type
            colour: Visual color for the tag
            tag_id: Parent tag ID if this is a sub-tag
            is_hidden: Whether to hide this tag from entity displays
            is_auto_applied: Whether to automatically assign this tag to new entities
            is_private: Whether the tag is only visible to admins
            tooltip: Hover text for the tag (premium feature)
        """
        # First, search for the tag by name
        tags_data = await make_kanka_request("tags")

        if not tags_data or "data" not in tags_data:
            return f"Unable to search for tag '{tag_name}'."

        if "error" in tags_data:
            return f"Error searching for tag: {tags_data['error']}"

        # Find tag with matching name (case-insensitive)
        target_tag = None
        for tag in tags_data["data"]:
            if tag.get("name", "").lower() == tag_name.lower():
                target_tag = tag
                break

        if not target_tag:
            return f"Tag '{tag_name}' not found in campaign."

        tag_id_to_update = target_tag["id"]

        # Build update data with only provided values
        update_data = {}
        if entry is not None:
            update_data["entry"] = entry
        if tag_type is not None:
            update_data["type"] = tag_type
        if colour is not None:
            update_data["colour"] = colour
        if tag_id is not None:
            update_data["tag_id"] = tag_id
        if is_hidden is not None:
            update_data["is_hidden"] = is_hidden
        if is_auto_applied is not None:
            update_data["is_auto_applied"] = is_auto_applied
        if is_private is not None:
            update_data["is_private"] = is_private
        if tooltip is not None:
            update_data["tooltip"] = tooltip

        if not update_data:
            return "No updates provided. Please specify at least one field to update."

        # Update the tag
        result = await update_kanka_entity(f"tags/{tag_id_to_update}", update_data)

        if not result:
            return f"Failed to update tag '{tag_name}'."

        if "error" in result:
            return f"Error updating tag: {result['error']}"

        if "data" in result:
            tag = result["data"]
            updated_fields = list(update_data.keys())
            return f"""
Successfully updated tag '{tag_name}'!

Name: {tag.get('name')}
Tag ID: {tag.get('id')}
Entity ID: {tag.get('entity_id')}
Type: {tag.get('type') or 'None'}
Colour: {tag.get('colour') or 'None'}
Parent Tag ID: {tag.get('tag_id') or 'None'}
Is Hidden: {'Yes' if tag.get('is_hidden') else 'No'}
Auto-Applied: {'Yes' if tag.get('is_auto_applied') else 'No'}
Visibility: {'Private' if tag.get('is_private') else 'Public'}

Updated fields: {', '.join(updated_fields)}
"""

        return "Tag updated, but unexpected response format."
