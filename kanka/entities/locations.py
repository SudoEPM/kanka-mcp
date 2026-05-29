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

def format_location_summary(location: dict) -> str:
    """Format a location into a readable summary."""
    return f"""
Name: {location.get('name', 'Unknown')}
ID: {location.get('id', 'N/A')}
Entity ID: {location.get('entity_id', 'N/A')}
Type: {location.get('type') or 'None'}
Status: {_status_label(location)}
Parent Location ID: {location.get('location_id') or 'None'}
Tags: {len(location.get('tags', []))} tag(s)
Is Private: {'Yes' if location.get('is_private') else 'No'}
"""

def format_location_detail(location: dict) -> str:
    """Format a location's full details."""
    return f"""
Name: {location.get('name', 'Unknown')}
ID: {location.get('id', 'N/A')}
Entity ID: {location.get('entity_id', 'N/A')}
Type: {location.get('type') or 'None'}
Status: {_status_label(location)}
Parent Location ID: {location.get('location_id') or 'None (Top-level location)'}

Entry/Description:
{location.get('entry', 'No description available.')}

Tags: {location.get('tags', [])}
Is Private: {'Yes' if location.get('is_private') else 'No'}
Created: {location.get('created_at')}
Last Updated: {location.get('updated_at')}
"""

def register_location_tools(mcp: FastMCP):
    """Register all location-related tools with the MCP server."""
    
    @mcp.tool()
    async def get_all_locations() -> str:
        """Get a list of all locations in the campaign.
        
        Returns a summary of all locations including their name, ID, type, and basic info.
        """
        data = await make_kanka_request("locations")
        
        if not data:
            return "Unable to fetch locations."
        
        if "error" in data:
            return f"Error: {data['error']}"
        
        if "data" not in data or not data["data"]:
            return "No locations found in this campaign."
        
        locations = [format_location_summary(location) for location in data["data"]]
        return "\n---\n".join(locations)

    @mcp.tool()
    async def get_location(location_id: int) -> str:
        """Get detailed information about a specific location.
        
        Args:
            location_id: The ID of the location to retrieve
        """
        data = await make_kanka_request(f"locations/{location_id}")
        
        if not data:
            return f"Unable to fetch location with ID {location_id}."
        
        if "error" in data:
            return f"Error: {data['error']}"
        
        if "data" not in data:
            return f"No location found with ID {location_id}."
        
        return format_location_detail(data["data"])

    @mcp.tool()
    async def create_location(
        name: str,
        entry: str = "",
        location_type: str = "",
        status_id: int = None,
        parent_location_id: int = None,
        entity_image_uuid: str = None,
        is_private: bool = False
    ) -> str:
        """Create a new location in the campaign.

        Args:
            name: The location's name (required)
            entry: HTML description of the location
            location_type: Location type (e.g., "City", "Forest", "Dungeon", "Country")
            status_id: ID of a campaign category_status (e.g. destroyed). Use
                get_statuses_for("location") to discover valid IDs.
            parent_location_id: ID of the parent location (for sub-locations)
            entity_image_uuid: Gallery image UUID for the location image
            is_private: Whether the location is only visible to admins
        """
        location_data = {
            "name": name,
            "entry": entry,
            "type": location_type,
            "is_private": is_private
        }

        # Only include optional fields if provided
        if status_id is not None:
            location_data["status_id"] = status_id
        if parent_location_id is not None:
            location_data["location_id"] = parent_location_id
        if entity_image_uuid is not None:
            location_data["entity_image_uuid"] = entity_image_uuid
        
        # Remove empty string values to keep the request clean
        location_data = {k: v for k, v in location_data.items() if v != ""}
        
        result = await create_kanka_entity("locations", location_data)
        
        if not result:
            return "Failed to create location."
        
        if "error" in result:
            return f"Error creating location: {result['error']}"
        
        if "data" in result:
            location = result["data"]
            return f"""
Successfully created location!

Name: {location.get('name')}
Location ID: {location.get('id')}
Entity ID: {location.get('entity_id')}
Type: {location.get('type') or 'None'}
Status: {_status_label(location)}
Parent Location ID: {location.get('location_id') or 'None'}
Visibility: {'Private' if location.get('is_private') else 'Public'}

The location has been added to your campaign.
"""
        
        return "Location created, but unexpected response format."

    @mcp.tool()
    async def update_location(
        location_name: str,
        entry: str = None,
        location_type: str = None,
        status_id: int = None,
        parent_location_id: int = None,
        entity_image_uuid: str = None,
        is_private: bool = None
    ) -> str:
        """Update an existing location by name.

        First searches for the location by name, then updates the specified fields.
        Only provided fields will be updated - others remain unchanged.

        Args:
            location_name: The name of the location to update (used for search)
            entry: HTML description of the location
            location_type: Location type (e.g., "City", "Forest", "Dungeon", "Country")
            status_id: ID of a campaign category_status (e.g. destroyed). Use
                get_statuses_for("location") to discover valid IDs.
            parent_location_id: ID of the parent location (for sub-locations)
            entity_image_uuid: Gallery image UUID for the location image
            is_private: Whether the location is only visible to admins
        """
        # First, search for the location by name
        locations_data = await make_kanka_request("locations")
        
        if not locations_data or "data" not in locations_data:
            return f"Unable to search for location '{location_name}'."
        
        if "error" in locations_data:
            return f"Error searching for location: {locations_data['error']}"
        
        # Find location with matching name (case-insensitive)
        target_location = None
        for location in locations_data["data"]:
            if location.get("name", "").lower() == location_name.lower():
                target_location = location
                break
        
        if not target_location:
            return f"Location '{location_name}' not found in campaign."
        
        location_id = target_location["id"]
        
        # Build update data with only provided values
        update_data = {}
        if entry is not None:
            update_data["entry"] = entry
        if location_type is not None:
            update_data["type"] = location_type
        if status_id is not None:
            update_data["status_id"] = status_id
        if parent_location_id is not None:
            update_data["location_id"] = parent_location_id
        if entity_image_uuid is not None:
            update_data["entity_image_uuid"] = entity_image_uuid
        if is_private is not None:
            update_data["is_private"] = is_private
        
        if not update_data:
            return "No updates provided. Please specify at least one field to update."
        
        # Update the location
        result = await update_kanka_entity(f"locations/{location_id}", update_data)
        
        if not result:
            return f"Failed to update location '{location_name}'."
        
        if "error" in result:
            return f"Error updating location: {result['error']}"
        
        if "data" in result:
            location = result["data"]
            updated_fields = list(update_data.keys())
            return f"""
Successfully updated location '{location_name}'!

Name: {location.get('name')}
ID: {location.get('id')}
Type: {location.get('type') or 'None'}
Status: {_status_label(location)}
Parent Location ID: {location.get('location_id') or 'None'}
Visibility: {'Private' if location.get('is_private') else 'Public'}

Updated fields: {', '.join(updated_fields)}
"""
        
        return "Location updated, but unexpected response format."