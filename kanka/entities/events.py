from mcp.server.fastmcp import FastMCP
from ..client import make_kanka_request, create_kanka_entity, update_kanka_entity

def format_event_summary(event: dict) -> str:
    """Format an event into a readable summary."""
    calendar_date = ""
    if event.get('calendar_id'):
        calendar_date = f"\nCalendar Date: Year {event.get('calendar_year', '?')}, Month {event.get('calendar_month', '?')}, Day {event.get('calendar_day', '?')}"

    return f"""
Name: {event.get('name', 'Unknown')}
ID: {event.get('id', 'N/A')}
Entity ID: {event.get('entity_id', 'N/A')}
Type: {event.get('type') or 'None'}
Date: {event.get('date') or 'None'}
Parent Event ID: {event.get('event_id') or 'None'}
Calendar ID: {event.get('calendar_id') or 'None'}{calendar_date}
Location ID: {event.get('location_id') or 'None'}
Tags: {len(event.get('tags', []))} tag(s)
Is Private: {'Yes' if event.get('is_private') else 'No'}
"""

def format_event_detail(event: dict) -> str:
    """Format an event's full details."""
    calendar_info = ""
    if event.get('calendar_id'):
        calendar_info = f"""
Calendar ID: {event.get('calendar_id')}
Calendar Date: Year {event.get('calendar_year', '?')}, Month {event.get('calendar_month', '?')}, Day {event.get('calendar_day', '?')}"""

    return f"""
Name: {event.get('name', 'Unknown')}
ID: {event.get('id', 'N/A')}
Entity ID: {event.get('entity_id', 'N/A')}
Type: {event.get('type') or 'None'}
Date: {event.get('date') or 'None'}
Parent Event ID: {event.get('event_id') or 'None (Main Event)'}{calendar_info}
Location ID: {event.get('location_id') or 'None'}

Entry/Description:
{event.get('entry', 'No description available.')}

Tags: {event.get('tags', [])}
Is Private: {'Yes' if event.get('is_private') else 'No'}
Created: {event.get('created_at')}
Last Updated: {event.get('updated_at')}
"""

def register_event_tools(mcp: FastMCP):
    """Register all event-related tools with the MCP server."""

    @mcp.tool()
    async def get_all_events() -> str:
        """Get a list of all events in the campaign.

        Returns a summary of all events including their name, ID, date, and basic info.
        """
        data = await make_kanka_request("events")

        if not data:
            return "Unable to fetch events."

        if "error" in data:
            return f"Error: {data['error']}"

        if "data" not in data or not data["data"]:
            return "No events found in this campaign."

        events = [format_event_summary(event) for event in data["data"]]
        return "\n---\n".join(events)

    @mcp.tool()
    async def get_event(event_id: int) -> str:
        """Get detailed information about a specific event.

        Args:
            event_id: The ID of the event to retrieve
        """
        data = await make_kanka_request(f"events/{event_id}")

        if not data:
            return f"Unable to fetch event with ID {event_id}."

        if "error" in data:
            return f"Error: {data['error']}"

        if "data" not in data:
            return f"No event found with ID {event_id}."

        return format_event_detail(data["data"])

    @mcp.tool()
    async def create_event(
        name: str,
        entry: str = "",
        event_type: str = "",
        date: str = "",
        parent_event_id: int = None,
        calendar_id: int = None,
        calendar_year: int = None,
        calendar_month: int = None,
        calendar_day: int = None,
        location_id: int = None,
        entity_image_uuid: str = None,
        is_private: bool = False
    ) -> str:
        """Create a new event in the campaign.

        IMPORTANT: When creating events on a calendar, you should first use get_calendar()
        to retrieve the calendar details and understand its month/day structure. This ensures
        you create events with valid month and day values according to that calendar's configuration.

        For example, if a calendar has 12 months with varying lengths (28, 30, or 31 days),
        you need to ensure calendar_month is between 1-12 and calendar_day doesn't exceed
        that month's length.

        Args:
            name: The event's name (required)
            entry: HTML description of the event
            event_type: Event type (e.g., "Battle", "Festival", "Meeting")
            date: A simple date string for display
            parent_event_id: ID of the parent event (for sub-events)
            calendar_id: ID of the calendar this event is on
            calendar_year: The year on the calendar (required if calendar_id is set)
            calendar_month: The month number on the calendar (required if calendar_id is set)
            calendar_day: The day number on the calendar (required if calendar_id is set)
            location_id: ID of the event's location
            entity_image_uuid: Gallery image UUID for the event image
            is_private: Whether the event is only visible to admins
        """
        event_data = {
            "name": name,
            "entry": entry,
            "type": event_type,
            "date": date,
            "is_private": is_private
        }

        # Handle calendar-related fields
        if calendar_id is not None:
            event_data["calendar_id"] = calendar_id

            # If calendar_id is provided, year/month/day should also be provided
            if calendar_year is None or calendar_month is None or calendar_day is None:
                return "When calendar_id is provided, calendar_year, calendar_month, and calendar_day must also be provided. Consider using get_calendar() to check the calendar structure first."

            event_data["calendar_year"] = calendar_year
            event_data["calendar_month"] = calendar_month
            event_data["calendar_day"] = calendar_day

        # Only include optional IDs if provided
        if parent_event_id is not None:
            event_data["event_id"] = parent_event_id
        if location_id is not None:
            event_data["location_id"] = location_id
        if entity_image_uuid is not None:
            event_data["entity_image_uuid"] = entity_image_uuid

        # Remove empty string values to keep the request clean
        event_data = {k: v for k, v in event_data.items() if v != ""}

        result = await create_kanka_entity("events", event_data)

        if not result:
            return "Failed to create event."

        if "error" in result:
            return f"Error creating event: {result['error']}"

        if "data" in result:
            event = result["data"]
            calendar_info = ""
            if event.get('calendar_id'):
                calendar_info = f"\nCalendar: {event.get('calendar_id')} - Year {event.get('calendar_year')}, Month {event.get('calendar_month')}, Day {event.get('calendar_day')}"

            return f"""
Successfully created event!

Name: {event.get('name')}
Event ID: {event.get('id')}
Entity ID: {event.get('entity_id')}
Type: {event.get('type') or 'None'}
Date: {event.get('date') or 'None'}
Parent Event ID: {event.get('event_id') or 'None'}{calendar_info}
Location ID: {event.get('location_id') or 'None'}
Visibility: {'Private' if event.get('is_private') else 'Public'}

The event has been added to your campaign.
"""

        return "Event created, but unexpected response format."

    @mcp.tool()
    async def update_event(
        event_name: str,
        entry: str = None,
        event_type: str = None,
        date: str = None,
        parent_event_id: int = None,
        calendar_id: int = None,
        calendar_year: int = None,
        calendar_month: int = None,
        calendar_day: int = None,
        location_id: int = None,
        entity_image_uuid: str = None,
        is_private: bool = None
    ) -> str:
        """Update an existing event by name.

        First searches for the event by name, then updates the specified fields.
        Only provided fields will be updated - others remain unchanged.

        IMPORTANT: When updating calendar dates, you should first use get_calendar()
        to retrieve the calendar details and understand its month/day structure. This ensures
        you update events with valid month and day values according to that calendar's configuration.

        Args:
            event_name: The name of the event to update (used for search)
            entry: HTML description of the event
            event_type: Event type (e.g., "Battle", "Festival", "Meeting")
            date: A simple date string for display
            parent_event_id: ID of the parent event (for sub-events)
            calendar_id: ID of the calendar this event is on
            calendar_year: The year on the calendar
            calendar_month: The month number on the calendar
            calendar_day: The day number on the calendar
            location_id: ID of the event's location
            entity_image_uuid: Gallery image UUID for the event image
            is_private: Whether the event is only visible to admins
        """
        # First, search for the event by name
        events_data = await make_kanka_request("events")

        if not events_data:
            return f"Unable to search for event '{event_name}'."
        if "error" in events_data:
            return f"Error searching for event: {events_data['error']}"
        if "data" not in events_data:
            return f"Unexpected response searching for event '{event_name}'."

        # Find event with matching name (case-insensitive)
        target_event = None
        for event in events_data["data"]:
            if event.get("name", "").lower() == event_name.lower():
                target_event = event
                break

        if not target_event:
            return f"Event '{event_name}' not found in campaign."

        event_id = target_event["id"]

        # Build update data with only provided values
        update_data = {}
        if entry is not None:
            update_data["entry"] = entry
        if event_type is not None:
            update_data["type"] = event_type
        if date is not None:
            update_data["date"] = date
        if parent_event_id is not None:
            update_data["event_id"] = parent_event_id
        if calendar_id is not None:
            update_data["calendar_id"] = calendar_id
        if calendar_year is not None:
            update_data["calendar_year"] = calendar_year
        if calendar_month is not None:
            update_data["calendar_month"] = calendar_month
        if calendar_day is not None:
            update_data["calendar_day"] = calendar_day
        if location_id is not None:
            update_data["location_id"] = location_id
        if entity_image_uuid is not None:
            update_data["entity_image_uuid"] = entity_image_uuid
        if is_private is not None:
            update_data["is_private"] = is_private

        # Validation: if updating calendar_id, recommend providing full date
        if calendar_id is not None:
            if calendar_year is None or calendar_month is None or calendar_day is None:
                # Check if existing event has these values
                if not target_event.get('calendar_year') or not target_event.get('calendar_month') or not target_event.get('calendar_day'):
                    return "When updating calendar_id, it's recommended to also provide calendar_year, calendar_month, and calendar_day. Consider using get_calendar() to check the calendar structure first."

        if not update_data:
            return "No updates provided. Please specify at least one field to update."

        # Update the event
        result = await update_kanka_entity(f"events/{event_id}", update_data)

        if not result:
            return f"Failed to update event '{event_name}'."

        if "error" in result:
            return f"Error updating event: {result['error']}"

        if "data" in result:
            event = result["data"]
            updated_fields = list(update_data.keys())

            calendar_info = ""
            if event.get('calendar_id'):
                calendar_info = f"\nCalendar: {event.get('calendar_id')} - Year {event.get('calendar_year')}, Month {event.get('calendar_month')}, Day {event.get('calendar_day')}"

            return f"""
Successfully updated event '{event_name}'!

Name: {event.get('name')}
ID: {event.get('id')}
Type: {event.get('type') or 'None'}
Date: {event.get('date') or 'None'}
Parent Event ID: {event.get('event_id') or 'None'}{calendar_info}
Location ID: {event.get('location_id') or 'None'}
Visibility: {'Private' if event.get('is_private') else 'Public'}

Updated fields: {', '.join(updated_fields)}
"""

        return "Event updated, but unexpected response format."
