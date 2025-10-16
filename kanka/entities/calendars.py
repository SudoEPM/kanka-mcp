from mcp.server.fastmcp import FastMCP
from ..client import make_kanka_request, update_kanka_entity

def format_calendar_summary(calendar: dict) -> str:
    """Format a calendar into a readable summary."""
    return f"""
Name: {calendar.get('name', 'Unknown')}
ID: {calendar.get('id', 'N/A')}
Entity ID: {calendar.get('entity_id', 'N/A')}
Type: {calendar.get('type') or 'None'}
Current Date: Year {calendar.get('current_year', '?')}, Month {calendar.get('current_month', '?')}, Day {calendar.get('current_day', '?')}
Months: {len(calendar.get('months', []))} month(s)
Weekdays: {len(calendar.get('weekdays', []))} day(s)
Tags: {len(calendar.get('tags', []))} tag(s)
Is Private: {'Yes' if calendar.get('is_private') else 'No'}
"""

def format_calendar_detail(calendar: dict) -> str:
    """Format a calendar's full details."""
    months_info = ""
    if calendar.get('months'):
        months_info = "\n\nMonths:"
        for month in calendar['months']:
            months_info += f"\n  - {month.get('name')}: {month.get('length', '?')} days"
    
    weekdays_info = ""
    if calendar.get('weekdays'):
        weekdays_info = f"\n\nWeekdays: {', '.join(calendar['weekdays'])}"
    
    return f"""
Name: {calendar.get('name', 'Unknown')}
ID: {calendar.get('id', 'N/A')}
Entity ID: {calendar.get('entity_id', 'N/A')}
Type: {calendar.get('type') or 'None'}
Current Date: Year {calendar.get('current_year', '?')}, Month {calendar.get('current_month', '?')}, Day {calendar.get('current_day', '?')}

Entry/Description:
{calendar.get('entry', 'No description available.')}

{months_info}
{weekdays_info}

Seasons: {len(calendar.get('seasons', []))} season(s)
Moons: {len(calendar.get('moons', []))} moon(s)
Years: {len(calendar.get('years', []))} named year(s)
Tags: {calendar.get('tags', [])}
Is Private: {'Yes' if calendar.get('is_private') else 'No'}
Created: {calendar.get('created_at')}
Last Updated: {calendar.get('updated_at')}
"""

def register_calendar_tools(mcp: FastMCP):
    """Register all calendar-related tools with the MCP server."""
    
    @mcp.tool()
    async def get_all_calendars() -> str:
        """Get a list of all calendars in the campaign.
        
        Returns a summary of all calendars including their name, ID, current date, and basic info.
        """
        data = await make_kanka_request("calendars")
        
        if not data:
            return "Unable to fetch calendars."
        
        if "error" in data:
            return f"Error: {data['error']}"
        
        if "data" not in data or not data["data"]:
            return "No calendars found in this campaign."
        
        calendars = [format_calendar_summary(calendar) for calendar in data["data"]]
        return "\n---\n".join(calendars)

    @mcp.tool()
    async def get_calendar(calendar_id: int) -> str:
        """Get detailed information about a specific calendar.
        
        Args:
            calendar_id: The ID of the calendar to retrieve
        """
        data = await make_kanka_request(f"calendars/{calendar_id}")
        
        if not data:
            return f"Unable to fetch calendar with ID {calendar_id}."
        
        if "error" in data:
            return f"Error: {data['error']}"
        
        if "data" not in data:
            return f"No calendar found with ID {calendar_id}."
        
        return format_calendar_detail(data["data"])

    @mcp.tool()
    async def update_calendar_date(
        calendar_id: int,
        current_year: int = None,
        current_month: int = None,
        current_day: int = None
    ) -> str:
        """Update ONLY the current date of a calendar.
        
        This tool is restricted to only update the current date fields.
        No other calendar properties can be modified through this tool.
        
        Args:
            calendar_id: The ID of the calendar to update
            current_year: The new current year
            current_month: The new current month
            current_day: The new current day
        """
        # Build update data with date fields and required calendar structure
        update_data = {
            # Required calendar structure that must always be included
            "month_name": ["Zarantyr (Jan)", "Olarune (Feb)", "Therendor (Mar)", "Eyre (April)", "Dravago (May)", "Nymm (June)", "Lharvion (July)", "Barrakas (Aug)", "Rhaan (Sep)", "Sypheros (Oct)", "Aryth (Nov)", "Vult (Dec)"],
            "month_length": [28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28],
            "month_type": ["standard", "standard", "standard", "standard", "standard", "standard", "standard", "standard", "standard", "standard", "standard", "standard"],
            "month_alias": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
            "weekday": ["Sul", "Mol", "Zol", "Wir", "Zor", "Far", "Sar"]
        }
        
        # Add date fields if provided
        if current_year is not None:
            update_data["current_year"] = current_year
        if current_month is not None:
            update_data["current_month"] = current_month
        if current_day is not None:
            update_data["current_day"] = current_day
        
        # Check if at least one date field was provided (structure fields are always included)
        date_fields_provided = any([current_year is not None, current_month is not None, current_day is not None])
        if not date_fields_provided:
            return "No date updates provided. Please specify at least one date field to update (current_year, current_month, or current_day)."
        
        # Update the calendar with only date fields
        result = await update_kanka_entity(f"calendars/{calendar_id}", update_data)
        
        if not result:
            return f"Failed to update calendar {calendar_id}."
        
        if "error" in result:
            return f"Error updating calendar: {result['error']}"
        
        if "data" in result:
            calendar = result["data"]
            # Only show the date fields that were actually updated
            date_fields_updated = []
            if current_year is not None:
                date_fields_updated.append("current_year")
            if current_month is not None:
                date_fields_updated.append("current_month")
            if current_day is not None:
                date_fields_updated.append("current_day")
            
            return f"""
Successfully updated calendar date!

Name: {calendar.get('name')}
ID: {calendar.get('id')}
New Current Date: {calendar.get('date', 'Unknown')} (YYYY-MM-DD format)
Individual Fields: Year {calendar.get('current_year', '?')}, Month {calendar.get('current_month', '?')}, Day {calendar.get('current_day', '?')}

Updated date fields: {', '.join(date_fields_updated)}
(Calendar structure fields were included as required by the API)
"""
        
        return "Calendar date updated, but unexpected response format."