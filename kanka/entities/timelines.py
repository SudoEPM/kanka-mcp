from mcp.server.fastmcp import FastMCP
from ..client import make_kanka_request, create_kanka_entity, update_kanka_entity

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

        if not timelines_data:
            return f"Unable to search for timeline '{timeline_name}'."
        if "error" in timelines_data:
            return f"Error searching for timeline: {timelines_data['error']}"
        if "data" not in timelines_data:
            return f"Unexpected response searching for timeline '{timeline_name}'."

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

    # ── Timeline Eras ────────────────────────────────────────────────────────

    @mcp.tool()
    async def get_all_timeline_eras(timeline_id: int) -> str:
        """Get all eras for a specific timeline.

        Args:
            timeline_id: The ID of the timeline
        """
        data = await make_kanka_request(f"timelines/{timeline_id}/timeline_eras")

        if not data:
            return f"Unable to fetch eras for timeline {timeline_id}."
        if "error" in data:
            return f"Error: {data['error']}"
        if "data" not in data or not data["data"]:
            return "No eras found for this timeline."

        lines = []
        for era in data["data"]:
            lines.append(
                f"ID: {era.get('id')}  Name: {era.get('era') or era.get('name', 'Unknown')}"
                f"  Years: {era.get('start_year', '?')}–{era.get('end_year', '?')}"
                f"  Abbreviation: {era.get('abbreviation') or '—'}"
            )
        return "\n".join(lines)

    @mcp.tool()
    async def get_timeline_era(timeline_id: int, era_id: int) -> str:
        """Get details for a specific timeline era.

        Args:
            timeline_id: The ID of the timeline
            era_id: The ID of the era
        """
        data = await make_kanka_request(f"timelines/{timeline_id}/timeline_eras/{era_id}")

        if not data:
            return f"Unable to fetch era {era_id}."
        if "error" in data:
            return f"Error: {data['error']}"
        if "data" not in data:
            return f"No era found with ID {era_id}."

        era = data["data"]
        return f"""
Name: {era.get('era') or era.get('name', 'Unknown')}
ID: {era.get('id')}
Abbreviation: {era.get('abbreviation') or '—'}
Start Year: {era.get('start_year', 'N/A')}
End Year: {era.get('end_year', 'N/A')}
Visibility: {era.get('visibility') or 'all'}
Created: {era.get('created_at')}
Last Updated: {era.get('updated_at')}
"""

    @mcp.tool()
    async def create_timeline_era(
        timeline_id: int,
        name: str,
        abbreviation: str = "",
        start_year: int | None = None,
        end_year: int | None = None,
        visibility: str = "all"
    ) -> str:
        """Create a new era on a timeline.

        Args:
            timeline_id: The ID of the timeline to add the era to
            name: The era's name (required)
            abbreviation: Short form designation (e.g. "BC", "Age of Fire")
            start_year: Start year of the era
            end_year: End year of the era
            visibility: Who can see it — "all", "admin", or "self"
        """
        era_data: dict = {"era": name, "visibility": visibility}
        if abbreviation:
            era_data["abbreviation"] = abbreviation
        if start_year is not None:
            era_data["start_year"] = start_year
        if end_year is not None:
            era_data["end_year"] = end_year

        result = await create_kanka_entity(f"timelines/{timeline_id}/timeline_eras", era_data)

        if not result:
            return "Failed to create timeline era."
        if "error" in result:
            return f"Error creating era: {result['error']}"
        if "data" in result:
            era = result["data"]
            return f"""
Successfully created era!

Name: {era.get('era') or era.get('name')}
ID: {era.get('id')}
Timeline ID: {timeline_id}
Years: {era.get('start_year', '?')}–{era.get('end_year', '?')}
Visibility: {era.get('visibility') or 'all'}
"""
        return "Era created, but unexpected response format."

    @mcp.tool()
    async def update_timeline_era(
        timeline_id: int,
        era_id: int,
        name: str | None = None,
        abbreviation: str | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        visibility: str | None = None
    ) -> str:
        """Update an existing timeline era.

        Args:
            timeline_id: The ID of the timeline
            era_id: The ID of the era to update
            name: New name for the era
            abbreviation: Short form designation
            start_year: Start year of the era
            end_year: End year of the era
            visibility: Who can see it — "all", "admin", or "self"
        """
        update_data: dict = {}
        if name is not None:
            update_data["era"] = name
        if abbreviation is not None:
            update_data["abbreviation"] = abbreviation
        if start_year is not None:
            update_data["start_year"] = start_year
        if end_year is not None:
            update_data["end_year"] = end_year
        if visibility is not None:
            update_data["visibility"] = visibility

        if not update_data:
            return "No updates provided. Please specify at least one field to update."

        result = await update_kanka_entity(
            f"timelines/{timeline_id}/timeline_eras/{era_id}", update_data
        )

        if not result:
            return f"Failed to update era {era_id}."
        if "error" in result:
            return f"Error updating era: {result['error']}"
        if "data" in result:
            era = result["data"]
            return f"""
Successfully updated era!

Name: {era.get('era') or era.get('name')}
ID: {era.get('id')}
Updated fields: {', '.join(update_data.keys())}
"""
        return "Era updated, but unexpected response format."

    # ── Timeline Elements ────────────────────────────────────────────────────

    @mcp.tool()
    async def get_all_timeline_elements(timeline_id: int) -> str:
        """Get all elements for a specific timeline (across all eras).

        Args:
            timeline_id: The ID of the timeline
        """
        data = await make_kanka_request(f"timelines/{timeline_id}/timeline_elements")

        if not data:
            return f"Unable to fetch elements for timeline {timeline_id}."
        if "error" in data:
            return f"Error: {data['error']}"
        if "data" not in data or not data["data"]:
            return "No elements found for this timeline."

        lines = []
        for el in data["data"]:
            lines.append(
                f"ID: {el.get('id')}  Era ID: {el.get('era_id')}  Name: {el.get('name') or '—'}"
                f"  Entity ID: {el.get('entity_id') or '—'}  Date: {el.get('date') or '—'}"
            )
        return "\n".join(lines)

    @mcp.tool()
    async def get_timeline_element(timeline_id: int, element_id: int) -> str:
        """Get details for a specific timeline element.

        Args:
            timeline_id: The ID of the timeline
            element_id: The ID of the element
        """
        data = await make_kanka_request(
            f"timelines/{timeline_id}/timeline_elements/{element_id}"
        )

        if not data:
            return f"Unable to fetch element {element_id}."
        if "error" in data:
            return f"Error: {data['error']}"
        if "data" not in data:
            return f"No element found with ID {element_id}."

        el = data["data"]
        return f"""
Name: {el.get('name') or '—'}
ID: {el.get('id')}
Era ID: {el.get('era_id')}
Entity ID: {el.get('entity_id') or '—'}
Date: {el.get('date') or '—'}
Colour: {el.get('colour') or '—'}
Position: {el.get('position') or '—'}
Entry:
{el.get('entry') or 'No description.'}

Created: {el.get('created_at')}
Last Updated: {el.get('updated_at')}
"""

    @mcp.tool()
    async def create_timeline_element(
        timeline_id: int,
        era_id: int,
        name: str = "",
        entity_id: int | None = None,
        entry: str = "",
        date: str = "",
        colour: str = "",
        position: int | None = None,
        visibility_id: int = 1
    ) -> str:
        """Create a new element in a timeline era.

        Either name or entity_id is required; era_id is always required.

        Args:
            timeline_id: The ID of the timeline
            era_id: The ID of the era this element belongs to (required)
            name: Element name (required if entity_id not provided)
            entity_id: Link to an existing campaign entity (required if name not provided)
            entry: HTML description
            date: Custom date display string
            colour: Display colour
            position: Sort order within the era
            visibility_id: 1=all, 2=self, 3=admin, 4=self-admin, 5=members
        """
        if not name and entity_id is None:
            return "Error: either name or entity_id must be provided."

        el_data: dict = {"era_id": era_id, "visibility_id": visibility_id}
        if name:
            el_data["name"] = name
        if entity_id is not None:
            el_data["entity_id"] = entity_id
        if entry:
            el_data["entry"] = entry
        if date:
            el_data["date"] = date
        if colour:
            el_data["colour"] = colour
        if position is not None:
            el_data["position"] = position

        result = await create_kanka_entity(
            f"timelines/{timeline_id}/timeline_elements", el_data
        )

        if not result:
            return "Failed to create timeline element."
        if "error" in result:
            return f"Error creating element: {result['error']}"
        if "data" in result:
            el = result["data"]
            return f"""
Successfully created timeline element!

Name: {el.get('name') or '—'}
ID: {el.get('id')}
Era ID: {el.get('era_id')}
Entity ID: {el.get('entity_id') or '—'}
Date: {el.get('date') or '—'}
"""
        return "Element created, but unexpected response format."

    @mcp.tool()
    async def update_timeline_element(
        timeline_id: int,
        element_id: int,
        era_id: int | None = None,
        name: str | None = None,
        entity_id: int | None = None,
        entry: str | None = None,
        date: str | None = None,
        colour: str | None = None,
        position: int | None = None,
        visibility_id: int | None = None
    ) -> str:
        """Update an existing timeline element.

        Args:
            timeline_id: The ID of the timeline
            element_id: The ID of the element to update
            era_id: Move the element to a different era
            name: New name for the element
            entity_id: Link to a different campaign entity
            entry: HTML description
            date: Custom date display string
            colour: Display colour
            position: Sort order within the era
            visibility_id: 1=all, 2=self, 3=admin, 4=self-admin, 5=members
        """
        update_data: dict = {}
        if era_id is not None:
            update_data["era_id"] = era_id
        if name is not None:
            update_data["name"] = name
        if entity_id is not None:
            update_data["entity_id"] = entity_id
        if entry is not None:
            update_data["entry"] = entry
        if date is not None:
            update_data["date"] = date
        if colour is not None:
            update_data["colour"] = colour
        if position is not None:
            update_data["position"] = position
        if visibility_id is not None:
            update_data["visibility_id"] = visibility_id

        if not update_data:
            return "No updates provided. Please specify at least one field to update."

        result = await update_kanka_entity(
            f"timelines/{timeline_id}/timeline_elements/{element_id}", update_data
        )

        if not result:
            return f"Failed to update element {element_id}."
        if "error" in result:
            return f"Error updating element: {result['error']}"
        if "data" in result:
            el = result["data"]
            return f"""
Successfully updated timeline element!

Name: {el.get('name') or '—'}
ID: {el.get('id')}
Updated fields: {', '.join(update_data.keys())}
"""
        return "Element updated, but unexpected response format."
