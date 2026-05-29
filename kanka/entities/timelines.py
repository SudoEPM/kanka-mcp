from mcp.server.fastmcp import FastMCP
from ..client import make_kanka_request, create_kanka_entity, update_kanka_entity

# Timeline eras and era elements are separate sub-resources
# (/timelines/{id}/timeline_eras). Not exposed here yet — add when needed.

def format_timeline_summary(tl: dict) -> str:
    """Format a timeline into a readable summary."""
    return f"""
Name: {tl.get('name', 'Unknown')}
ID: {tl.get('id', 'N/A')}
Entity ID: {tl.get('entity_id', 'N/A')}
Type: {tl.get('type') or 'None'}
Tags: {len(tl.get('tags', []))} tag(s)
Is Private: {'Yes' if tl.get('is_private') else 'No'}
"""

def format_timeline_detail(tl: dict) -> str:
    """Format a timeline's full details."""
    eras = tl.get('eras', [])
    return f"""
Name: {tl.get('name', 'Unknown')}
ID: {tl.get('id', 'N/A')}
Entity ID: {tl.get('entity_id', 'N/A')}
Type: {tl.get('type') or 'None'}

Entry/Description:
{tl.get('entry', 'No description available.')}

Eras: {len(eras)} era(s)
Tags: {tl.get('tags', [])}
Is Private: {'Yes' if tl.get('is_private') else 'No'}
Created: {tl.get('created_at')}
Last Updated: {tl.get('updated_at')}
"""

def register_timeline_tools(mcp: FastMCP):
    """Register all timeline-related tools with the MCP server."""

    @mcp.tool()
    async def get_all_timelines() -> str:
        """Get a list of all timelines in the campaign."""
        data = await make_kanka_request("timelines")

        if not data:
            return "Unable to fetch timelines."
        if "error" in data:
            return f"Error: {data['error']}"
        if "data" not in data or not data["data"]:
            return "No timelines found in this campaign."

        timelines = [format_timeline_summary(t) for t in data["data"]]
        return "\n---\n".join(timelines)

    @mcp.tool()
    async def get_timeline(timeline_id: int) -> str:
        """Get detailed information about a specific timeline.

        Args:
            timeline_id: The ID of the timeline to retrieve
        """
        data = await make_kanka_request(f"timelines/{timeline_id}")

        if not data:
            return f"Unable to fetch timeline with ID {timeline_id}."
        if "error" in data:
            return f"Error: {data['error']}"
        if "data" not in data:
            return f"No timeline found with ID {timeline_id}."

        return format_timeline_detail(data["data"])

    @mcp.tool()
    async def create_timeline(
        name: str,
        entry: str = "",
        timeline_type: str = "",
        entity_image_uuid: str = None,
        is_private: bool = False
    ) -> str:
        """Create a new timeline in the campaign.

        Eras and era elements are managed via separate sub-resources (not
        exposed by this tool yet) — create the timeline first, then attach
        eras through the Kanka UI or a future tool.

        Args:
            name: The timeline's name (required)
            entry: HTML description of the timeline
            timeline_type: Timeline classification (e.g., "Historical", "Campaign")
            entity_image_uuid: Gallery image UUID for the timeline image
            is_private: Whether the timeline is only visible to admins
        """
        timeline_data = {
            "name": name,
            "entry": entry,
            "type": timeline_type,
            "is_private": is_private
        }

        if entity_image_uuid is not None:
            timeline_data["entity_image_uuid"] = entity_image_uuid

        timeline_data = {k: v for k, v in timeline_data.items() if v != ""}

        result = await create_kanka_entity("timelines", timeline_data)

        if not result:
            return "Failed to create timeline."
        if "error" in result:
            return f"Error creating timeline: {result['error']}"

        if "data" in result:
            tl = result["data"]
            return f"""
Successfully created timeline!

Name: {tl.get('name')}
Timeline ID: {tl.get('id')}
Entity ID: {tl.get('entity_id')}
Type: {tl.get('type') or 'None'}
Visibility: {'Private' if tl.get('is_private') else 'Public'}

The timeline has been added to your campaign.
"""

        return "Timeline created, but unexpected response format."

    @mcp.tool()
    async def update_timeline(
        timeline_name: str,
        entry: str = None,
        timeline_type: str = None,
        entity_image_uuid: str = None,
        is_private: bool = None
    ) -> str:
        """Update an existing timeline by name.

        Args:
            timeline_name: The name of the timeline to update (used for search)
            entry: HTML description of the timeline
            timeline_type: Timeline classification
            entity_image_uuid: Gallery image UUID
            is_private: Whether the timeline is only visible to admins
        """
        timelines_data = await make_kanka_request("timelines")

        if not timelines_data or "data" not in timelines_data:
            return f"Unable to search for timeline '{timeline_name}'."
        if "error" in timelines_data:
            return f"Error searching for timeline: {timelines_data['error']}"

        target_tl = None
        for t in timelines_data["data"]:
            if t.get("name", "").lower() == timeline_name.lower():
                target_tl = t
                break

        if not target_tl:
            return f"Timeline '{timeline_name}' not found in campaign."

        timeline_id = target_tl["id"]

        update_data = {}
        if entry is not None:
            update_data["entry"] = entry
        if timeline_type is not None:
            update_data["type"] = timeline_type
        if entity_image_uuid is not None:
            update_data["entity_image_uuid"] = entity_image_uuid
        if is_private is not None:
            update_data["is_private"] = is_private

        if not update_data:
            return "No updates provided. Please specify at least one field to update."

        result = await update_kanka_entity(f"timelines/{timeline_id}", update_data)

        if not result:
            return f"Failed to update timeline '{timeline_name}'."
        if "error" in result:
            return f"Error updating timeline: {result['error']}"

        if "data" in result:
            tl = result["data"]
            updated_fields = list(update_data.keys())
            return f"""
Successfully updated timeline '{timeline_name}'!

Name: {tl.get('name')}
ID: {tl.get('id')}
Type: {tl.get('type') or 'None'}
Visibility: {'Private' if tl.get('is_private') else 'Public'}

Updated fields: {', '.join(updated_fields)}
"""

        return "Timeline updated, but unexpected response format."
