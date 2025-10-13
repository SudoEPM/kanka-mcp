from mcp.server.fastmcp import FastMCP
from ..client import make_kanka_request, create_kanka_entity, update_kanka_entity

def format_organization_summary(org: dict) -> str:
    """Format an organization into a readable summary."""
    return f"""
Name: {org.get('name', 'Unknown')}
ID: {org.get('id', 'N/A')}
Entity ID: {org.get('entity_id', 'N/A')}
Type: {org.get('type') or 'None'}
Status: {'Defunct' if org.get('is_defunct') else 'Active'}
Parent Organization ID: {org.get('organisation_id') or 'None'}
Locations: {len(org.get('locations', []))} location(s)
Members: {len(org.get('members', []))} member(s)
Tags: {len(org.get('tags', []))} tag(s)
Is Private: {'Yes' if org.get('is_private') else 'No'}
"""

def format_organization_detail(org: dict) -> str:
    """Format an organization's full details."""
    return f"""
Name: {org.get('name', 'Unknown')}
ID: {org.get('id', 'N/A')}
Entity ID: {org.get('entity_id', 'N/A')}
Type: {org.get('type') or 'None'}
Status: {'Defunct' if org.get('is_defunct') else 'Active'}
Parent Organization ID: {org.get('organisation_id') or 'None (Top-level organization)'}

Entry/Description:
{org.get('entry', 'No description available.')}

Locations: {org.get('locations', [])}
Members: {org.get('members', [])}
Tags: {org.get('tags', [])}
Is Private: {'Yes' if org.get('is_private') else 'No'}
Created: {org.get('created_at')}
Last Updated: {org.get('updated_at')}
"""

def register_organization_tools(mcp: FastMCP):
    """Register all organization-related tools with the MCP server."""
    
    @mcp.tool()
    async def get_all_organizations() -> str:
        """Get a list of all organizations in the campaign.
        
        Returns a summary of all organizations including their name, ID, type, and basic info.
        """
        data = await make_kanka_request("organisations")
        
        if not data:
            return "Unable to fetch organizations."
        
        if "error" in data:
            return f"Error: {data['error']}"
        
        if "data" not in data or not data["data"]:
            return "No organizations found in this campaign."
        
        organizations = [format_organization_summary(org) for org in data["data"]]
        return "\n---\n".join(organizations)

    @mcp.tool()
    async def get_organization(organization_id: int) -> str:
        """Get detailed information about a specific organization.
        
        Args:
            organization_id: The ID of the organization to retrieve
        """
        data = await make_kanka_request(f"organisations/{organization_id}")
        
        if not data:
            return f"Unable to fetch organization with ID {organization_id}."
        
        if "error" in data:
            return f"Error: {data['error']}"
        
        if "data" not in data:
            return f"No organization found with ID {organization_id}."
        
        return format_organization_detail(data["data"])

    @mcp.tool()
    async def create_organization(
        name: str,
        entry: str = "",
        org_type: str = "",
        is_defunct: bool = False,
        parent_organization_id: int = None,
        location_ids: list = None,
        entity_image_uuid: str = None,
        is_private: bool = False
    ) -> str:
        """Create a new organization in the campaign.
        
        Args:
            name: The organization's name (required)
            entry: HTML description of the organization
            org_type: Organization type (e.g., "Guild", "Kingdom", "Company")
            is_defunct: Whether the organization is defunct/inactive
            parent_organization_id: ID of the parent organization (for sub-organizations)
            location_ids: List of location IDs where this organization has presence
            entity_image_uuid: Gallery image UUID for the organization image
            is_private: Whether the organization is only visible to admins
        """
        org_data = {
            "name": name,
            "entry": entry,
            "type": org_type,
            "is_defunct": is_defunct,
            "is_private": is_private
        }
        
        # Only include optional fields if provided
        if parent_organization_id is not None:
            org_data["organisation_id"] = parent_organization_id
        if location_ids is not None:
            org_data["locations"] = location_ids
        if entity_image_uuid is not None:
            org_data["entity_image_uuid"] = entity_image_uuid
        
        # Remove empty string values to keep the request clean
        org_data = {k: v for k, v in org_data.items() if v != ""}
        
        result = await create_kanka_entity("organisations", org_data)
        
        if not result:
            return "Failed to create organization."
        
        if "error" in result:
            return f"Error creating organization: {result['error']}"
        
        if "data" in result:
            organization = result["data"]
            return f"""
Successfully created organization!

Name: {organization.get('name')}
ID: {organization.get('id')}
Type: {organization.get('type') or 'None'}
Status: {'Defunct' if organization.get('is_defunct') else 'Active'}
Parent Organization ID: {organization.get('organisation_id') or 'None'}
Locations: {len(organization.get('locations', []))} location(s)
Visibility: {'Private' if organization.get('is_private') else 'Public'}

The organization has been added to your campaign.
"""
        
        return "Organization created, but unexpected response format."

    @mcp.tool()
    async def update_organization(
        organization_name: str,
        entry: str = None,
        org_type: str = None,
        is_defunct: bool = None,
        parent_organization_id: int = None,
        location_ids: list = None,
        entity_image_uuid: str = None,
        is_private: bool = None
    ) -> str:
        """Update an existing organization by name.
        
        First searches for the organization by name, then updates the specified fields.
        Only provided fields will be updated - others remain unchanged.
        
        Args:
            organization_name: The name of the organization to update (used for search)
            entry: HTML description of the organization
            org_type: Organization type (e.g., "Guild", "Kingdom", "Company")
            is_defunct: Whether the organization is defunct/inactive
            parent_organization_id: ID of the parent organization (for sub-organizations)
            location_ids: List of location IDs where this organization has presence
            entity_image_uuid: Gallery image UUID for the organization image
            is_private: Whether the organization is only visible to admins
        """
        # First, search for the organization by name
        organizations_data = await make_kanka_request("organisations")
        
        if not organizations_data or "data" not in organizations_data:
            return f"Unable to search for organization '{organization_name}'."
        
        if "error" in organizations_data:
            return f"Error searching for organization: {organizations_data['error']}"
        
        # Find organization with matching name (case-insensitive)
        target_organization = None
        for org in organizations_data["data"]:
            if org.get("name", "").lower() == organization_name.lower():
                target_organization = org
                break
        
        if not target_organization:
            return f"Organization '{organization_name}' not found in campaign."
        
        organization_id = target_organization["id"]
        
        # Build update data with only provided values
        update_data = {}
        if entry is not None:
            update_data["entry"] = entry
        if org_type is not None:
            update_data["type"] = org_type
        if is_defunct is not None:
            update_data["is_defunct"] = is_defunct
        if parent_organization_id is not None:
            update_data["organisation_id"] = parent_organization_id
        if location_ids is not None:
            update_data["locations"] = location_ids
        if entity_image_uuid is not None:
            update_data["entity_image_uuid"] = entity_image_uuid
        if is_private is not None:
            update_data["is_private"] = is_private
        
        if not update_data:
            return "No updates provided. Please specify at least one field to update."
        
        # Update the organization
        result = await update_kanka_entity(f"organisations/{organization_id}", update_data)
        
        if not result:
            return f"Failed to update organization '{organization_name}'."
        
        if "error" in result:
            return f"Error updating organization: {result['error']}"
        
        if "data" in result:
            organization = result["data"]
            updated_fields = list(update_data.keys())
            return f"""
Successfully updated organization '{organization_name}'!

Name: {organization.get('name')}
ID: {organization.get('id')}
Type: {organization.get('type') or 'None'}
Status: {'Defunct' if organization.get('is_defunct') else 'Active'}
Parent Organization ID: {organization.get('organisation_id') or 'None'}
Locations: {len(organization.get('locations', []))} location(s)
Visibility: {'Private' if organization.get('is_private') else 'Public'}

Updated fields: {', '.join(updated_fields)}
"""
        
        return "Organization updated, but unexpected response format."