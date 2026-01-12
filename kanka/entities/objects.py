from mcp.server.fastmcp import FastMCP
from ..client import make_kanka_request, create_kanka_entity, update_kanka_entity
import httpx
import os

# Load from environment variables
KANKA_API_TOKEN = os.getenv("KANKA_API_TOKEN", "")
KANKA_CAMPAIGN_ID = os.getenv("KANKA_CAMPAIGN_ID", "")
KANKA_API_BASE = "https://api.kanka.io/1.0"

def format_item_summary(item: dict) -> str:
    """Format an item into a readable summary."""
    return f"""
Name: {item.get('name', 'Unknown')}
ID: {item.get('id', 'N/A')}
Entity ID: {item.get('entity_id', 'N/A')}
Type: {item.get('type') or 'None'}
Location ID: {item.get('location_id') or 'None'}
Parent Item ID: {item.get('item_id') or 'None'}
Tags: {len(item.get('tags', []))} tag(s)
"""

def format_item_detail(item: dict) -> str:
    """Format an item's full details."""
    return f"""
Name: {item.get('name', 'Unknown')}
ID: {item.get('id', 'N/A')}
Entity ID: {item.get('entity_id', 'N/A')}
Type: {item.get('type') or 'None'}
Price: {item.get('price') or 'None'}
Size: {item.get('size') or 'None'}
Weight: {item.get('weight') or 'None'}
Location ID: {item.get('location_id') or 'None'}
Creator ID: {item.get('creator_id') or 'None'}
Parent Item ID: {item.get('item_id') or 'None'}
Tags: {item.get('tags', [])}
Visibility: {'Private' if item.get('is_private') else 'Public'}

Entry/Description:
{item.get('entry', 'No description available.')}
"""

def register_object_tools(mcp: FastMCP):
    """Register all object (item) related tools with the MCP server."""

    @mcp.tool()
    async def get_all_items() -> str:
        """Get a list of all items in the campaign.

        Returns a summary of all items including their name, ID, and basic info.
        """
        data = await make_kanka_request("items")

        if not data:
            return "Unable to fetch items."

        if "error" in data:
            return f"Error: {data['error']}"

        if "data" not in data or not data["data"]:
            return "No items found in this campaign."

        items = [format_item_summary(item) for item in data["data"]]
        return "\n---\n".join(items)

    @mcp.tool()
    async def get_item(item_id: int) -> str:
        """Get detailed information about a specific item.

        Args:
            item_id: The ID of the item to retrieve
        """
        data = await make_kanka_request(f"items/{item_id}")

        if not data:
            return f"Unable to fetch item with ID {item_id}."

        if "error" in data:
            return f"Error: {data['error']}"

        if "data" not in data:
            return f"No item found with ID {item_id}."

        return format_item_detail(data["data"])

    @mcp.tool()
    async def create_item(
        name: str,
        entry: str = "",
        item_type: str = "",
        price: str = "",
        size: str = "",
        weight: str = "",
        location_id: int = None,
        creator_id: int = None,
        item_id: int = None,
        tags: list[int] = None,
        is_private: bool = False,
        tooltip: str = ""
    ) -> str:
        """Create a new item in the campaign.

        Args:
            name: The item's name (required)
            entry: HTML description of the item
            item_type: Item type/category
            price: Item price
            size: Item size
            weight: Item weight
            location_id: ID of the location where this item is found
            creator_id: Entity ID of the item's creator
            item_id: Parent item ID for hierarchical relationships
            tags: List of tag IDs to apply to this item
            is_private: Whether the item is only visible to admins
            tooltip: Hover text for the item (premium feature)
        """
        item_data = {
            "name": name,
            "entry": entry,
            "type": item_type,
            "price": price,
            "size": size,
            "weight": weight,
            "is_private": is_private,
            "tooltip": tooltip
        }

        # Only include optional ID fields if provided
        if location_id is not None:
            item_data["location_id"] = location_id
        if creator_id is not None:
            item_data["creator_id"] = creator_id
        if item_id is not None:
            item_data["item_id"] = item_id

        # Add tags if provided
        if tags is not None and len(tags) > 0:
            item_data["tags"] = tags
            item_data["save_tags"] = True

        # Remove empty string values to keep the request clean
        item_data = {k: v for k, v in item_data.items() if v != ""}

        result = await create_kanka_entity("items", item_data)

        if not result:
            return "Failed to create item."

        if "error" in result:
            return f"Error creating item: {result['error']}"

        if "data" in result:
            item = result["data"]
            return f"""
Successfully created item!

Name: {item.get('name')}
Item ID: {item.get('id')}
Entity ID: {item.get('entity_id')}
Type: {item.get('type') or 'None'}
Price: {item.get('price') or 'None'}
Size: {item.get('size') or 'None'}
Weight: {item.get('weight') or 'None'}
Location ID: {item.get('location_id') or 'None'}
Creator ID: {item.get('creator_id') or 'None'}
Parent Item ID: {item.get('item_id') or 'None'}
Tags: {len(item.get('tags', []))} tag(s)
Visibility: {'Private' if item.get('is_private') else 'Public'}

The item has been added to your campaign.
"""

        return "Item created, but unexpected response format."

    @mcp.tool()
    async def update_item(
        item_name: str,
        entry: str = None,
        item_type: str = None,
        price: str = None,
        size: str = None,
        weight: str = None,
        location_id: int = None,
        creator_id: int = None,
        item_id: int = None,
        tags: list[int] = None,
        is_private: bool = None,
        tooltip: str = None
    ) -> str:
        """Update an existing item by name.

        First searches for the item by name, then updates the specified fields.
        Only provided fields will be updated - others remain unchanged.

        Args:
            item_name: The name of the item to update (used for search)
            entry: HTML description of the item
            item_type: Item type/category
            price: Item price
            size: Item size
            weight: Item weight
            location_id: ID of the location where this item is found
            creator_id: Entity ID of the item's creator
            item_id: Parent item ID for hierarchical relationships
            tags: List of tag IDs to apply to this item (replaces existing tags)
            is_private: Whether the item is only visible to admins
            tooltip: Hover text for the item (premium feature)
        """
        # First, search for the item by name
        items_data = await make_kanka_request("items")

        if not items_data or "data" not in items_data:
            return f"Unable to search for item '{item_name}'."

        if "error" in items_data:
            return f"Error searching for item: {items_data['error']}"

        # Find item with matching name (case-insensitive)
        target_item = None
        for item in items_data["data"]:
            if item.get("name", "").lower() == item_name.lower():
                target_item = item
                break

        if not target_item:
            return f"Item '{item_name}' not found in campaign."

        item_id_to_update = target_item["id"]

        # Build update data with only provided values
        update_data = {}
        if entry is not None:
            update_data["entry"] = entry
        if item_type is not None:
            update_data["type"] = item_type
        if price is not None:
            update_data["price"] = price
        if size is not None:
            update_data["size"] = size
        if weight is not None:
            update_data["weight"] = weight
        if location_id is not None:
            update_data["location_id"] = location_id
        if creator_id is not None:
            update_data["creator_id"] = creator_id
        if item_id is not None:
            update_data["item_id"] = item_id
        if is_private is not None:
            update_data["is_private"] = is_private
        if tooltip is not None:
            update_data["tooltip"] = tooltip
        if tags is not None:
            update_data["tags"] = tags
            update_data["save_tags"] = True

        if not update_data:
            return "No updates provided. Please specify at least one field to update."

        # Update the item
        result = await update_kanka_entity(f"items/{item_id_to_update}", update_data)

        if not result:
            return f"Failed to update item '{item_name}'."

        if "error" in result:
            return f"Error updating item: {result['error']}"

        if "data" in result:
            item = result["data"]
            updated_fields = list(update_data.keys())
            return f"""
Successfully updated item '{item_name}'!

Name: {item.get('name')}
Item ID: {item.get('id')}
Entity ID: {item.get('entity_id')}
Type: {item.get('type') or 'None'}
Price: {item.get('price') or 'None'}
Size: {item.get('size') or 'None'}
Weight: {item.get('weight') or 'None'}
Location ID: {item.get('location_id') or 'None'}
Tags: {len(item.get('tags', []))} tag(s)
Visibility: {'Private' if item.get('is_private') else 'Public'}

Updated fields: {', '.join(updated_fields)}
"""

        return "Item updated, but unexpected response format."

    @mcp.tool()
    async def send_summary_notification(summary_text: str) -> str:
        """Send a summary notification via webhook.

        Creates a temporary item with tag 527715 which triggers a webhook notification.
        The item is automatically deleted after creation.

        This is useful for sending campaign summaries or notifications through your configured webhook.

        Args:
            summary_text: The summary text to send via webhook
        """
        # Tag ID that triggers the webhook
        NOTIFICATION_TAG_ID = 527715

        item_data = {
            "name": f"Summary: {summary_text[:100]}",
            "entry": summary_text,
            "type": "Notification",
            "tags": [NOTIFICATION_TAG_ID],
            "save_tags": True,
            "is_private": True  # Make it private so it doesn't clutter the public view
        }

        # Create the item
        result = await create_kanka_entity("items", item_data)

        if not result or "error" in result:
            error_msg = result.get('error', 'Unknown error') if result else 'Failed to create notification'
            return f"Failed to send notification: {error_msg}"

        if "data" not in result:
            return "Failed to send notification: unexpected response format."

        item = result["data"]
        item_id = item.get('id')

        if not item_id:
            return "Notification created but unable to clean up (no ID returned)."

        # Now delete the item to clean up
        headers = {
            "Authorization": f"Bearer {KANKA_API_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        url = f"{KANKA_API_BASE}/campaigns/{KANKA_CAMPAIGN_ID}/items/{item_id}"

        async with httpx.AsyncClient() as client:
            try:
                await client.delete(url, headers=headers, timeout=30.0)
            except:
                # Don't fail if cleanup fails - notification was still sent
                pass

        return f"""
Successfully sent summary notification!

Summary: {summary_text}
Notification Tag: {NOTIFICATION_TAG_ID}

The webhook notification has been triggered and the temporary item has been cleaned up.
"""
