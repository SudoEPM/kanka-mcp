from mcp.server.fastmcp import FastMCP
from ..client import make_kanka_request, create_kanka_entity, update_kanka_entity

def _status_label(char: dict) -> str:
    status = char.get('status') or {}
    key = status.get('key')
    status_id = char.get('status_id')
    if key and status_id:
        return f"{key} (status_id={status_id})"
    if status_id:
        return f"status_id={status_id}"
    return 'None'

def format_character_summary(char: dict) -> str:
    """Format a character into a readable summary."""
    return f"""
Name: {char.get('name', 'Unknown')}
ID: {char.get('id', 'N/A')}
Entity ID: {char.get('entity_id', 'N/A')}
Title: {char.get('title') or 'None'}
Age: {char.get('age') or 'Unknown'}
Sex: {char.get('sex') or 'Unknown'}
Type: {char.get('type') or 'None'}
Status: {_status_label(char)}
Location ID: {char.get('location_id') or 'None'}
Tags: {len(char.get('tags', []))} tag(s)
"""

def format_character_detail(char: dict) -> str:
    """Format a character's full details."""
    traits_text = ""
    if char.get('traits'):
        traits_text = "\n\nTraits:"
        for trait in char['traits']:
            traits_text += f"\n  - {trait.get('name')}: {trait.get('entry')}"

    return f"""
Name: {char.get('name', 'Unknown')}
ID: {char.get('id', 'N/A')}
Entity ID: {char.get('entity_id', 'N/A')}
Title: {char.get('title') or 'None'}
Age: {char.get('age') or 'Unknown'}
Sex: {char.get('sex') or 'Unknown'}
Pronouns: {char.get('pronouns') or 'None'}
Type: {char.get('type') or 'None'}
Status: {_status_label(char)}
Location ID: {char.get('location_id') or 'None'}

Entry/Description:
{char.get('entry', 'No description available.')}

Families: {char.get('families', [])}
Races: {char.get('races', [])}
Tags: {char.get('tags', [])}
{traits_text}
"""

def register_character_tools(mcp: FastMCP):
    """Register all character-related tools with the MCP server."""
    
    @mcp.tool()
    async def get_all_characters() -> str:
        """Get a list of all characters in the campaign.
        
        Returns a summary of all characters including their name, ID, and basic info.
        """
        data = await make_kanka_request("characters")
        
        if not data:
            return "Unable to fetch characters."
        
        if "error" in data:
            return f"Error: {data['error']}"
        
        if "data" not in data or not data["data"]:
            return "No characters found in this campaign."
        
        characters = [format_character_summary(char) for char in data["data"]]
        return "\n---\n".join(characters)

    @mcp.tool()
    async def get_character(character_id: int) -> str:
        """Get detailed information about a specific character.
        
        Args:
            character_id: The ID of the character to retrieve
        """
        data = await make_kanka_request(f"characters/{character_id}")
        
        if not data:
            return f"Unable to fetch character with ID {character_id}."
        
        if "error" in data:
            return f"Error: {data['error']}"
        
        if "data" not in data:
            return f"No character found with ID {character_id}."
        
        return format_character_detail(data["data"])

    @mcp.tool()
    async def create_character(
        name: str,
        entry: str = "",
        title: str = "",
        age: str = "",
        sex: str = "",
        pronouns: str = "",
        character_type: str = "",
        location_id: int = None,
        status_id: int = None,
        is_private: bool = False
    ) -> str:
        """Create a new character in the campaign.

        Args:
            name: The character's name (required)
            entry: HTML description of the character
            title: Character's title
            age: Character's age
            sex: Character's gender
            pronouns: Preferred pronouns
            character_type: Character type (e.g., "NPC", "PC", "Villain")
            location_id: ID of the character's location
            status_id: ID of a campaign category_status (e.g. alive/dead/missing).
                Use get_statuses_for("character") to discover valid IDs.
            is_private: Whether the character is only visible to admins
        """
        character_data = {
            "name": name,
            "entry": entry,
            "title": title,
            "age": age,
            "sex": sex,
            "pronouns": pronouns,
            "type": character_type,
            "is_private": is_private
        }

        if location_id is not None:
            character_data["location_id"] = location_id
        if status_id is not None:
            character_data["status_id"] = status_id

        # Remove empty string values to keep the request clean
        character_data = {k: v for k, v in character_data.items() if v != ""}

        result = await create_kanka_entity("characters", character_data)

        if not result:
            return "Failed to create character."

        if "error" in result:
            return f"Error creating character: {result['error']}"

        if "data" in result:
            character = result["data"]
            return f"""
Successfully created character!

Name: {character.get('name')}
Character ID: {character.get('id')}
Entity ID: {character.get('entity_id')}
Title: {character.get('title') or 'None'}
Age: {character.get('age') or 'Unknown'}
Sex: {character.get('sex') or 'Unknown'}
Type: {character.get('type') or 'None'}
Location ID: {character.get('location_id') or 'None'}
Status: {_status_label(character)}
Visibility: {'Private' if character.get('is_private') else 'Public'}

The character has been added to your campaign.
"""
        
        return "Character created, but unexpected response format."

    @mcp.tool()
    async def update_character(
        character_name: str,
        entry: str = None,
        title: str = None,
        age: str = None,
        sex: str = None,
        pronouns: str = None,
        character_type: str = None,
        location_id: int = None,
        status_id: int = None,
        is_private: bool = None
    ) -> str:
        """Update an existing character by name.

        First searches for the character by name, then updates the specified fields.
        Only provided fields will be updated - others remain unchanged.

        Args:
            character_name: The name of the character to update (used for search)
            entry: HTML description of the character
            title: Character's title
            age: Character's age
            sex: Character's gender
            pronouns: Preferred pronouns
            character_type: Character type (e.g., "NPC", "PC", "Villain")
            location_id: ID of the character's location
            status_id: ID of a campaign category_status (e.g. alive/dead/missing).
                Use get_statuses_for("character") to discover valid IDs.
            is_private: Whether the character is only visible to admins
        """
        # First, search for the character by name
        characters_data = await make_kanka_request("characters")
        
        if not characters_data or "data" not in characters_data:
            return f"Unable to search for character '{character_name}'."
        
        if "error" in characters_data:
            return f"Error searching for character: {characters_data['error']}"
        
        # Find character with matching name (case-insensitive)
        target_character = None
        for char in characters_data["data"]:
            if char.get("name", "").lower() == character_name.lower():
                target_character = char
                break
        
        if not target_character:
            return f"Character '{character_name}' not found in campaign."
        
        character_id = target_character["id"]
        
        # Build update data with only provided values
        update_data = {}
        if entry is not None:
            update_data["entry"] = entry
        if title is not None:
            update_data["title"] = title
        if age is not None:
            update_data["age"] = age
        if sex is not None:
            update_data["sex"] = sex
        if pronouns is not None:
            update_data["pronouns"] = pronouns
        if character_type is not None:
            update_data["type"] = character_type
        if location_id is not None:
            update_data["location_id"] = location_id
        if status_id is not None:
            update_data["status_id"] = status_id
        if is_private is not None:
            update_data["is_private"] = is_private
        
        if not update_data:
            return "No updates provided. Please specify at least one field to update."
        
        # Update the character
        result = await update_kanka_entity(f"characters/{character_id}", update_data)
        
        if not result:
            return f"Failed to update character '{character_name}'."
        
        if "error" in result:
            return f"Error updating character: {result['error']}"
        
        if "data" in result:
            character = result["data"]
            updated_fields = list(update_data.keys())
            return f"""
Successfully updated character '{character_name}'!

Name: {character.get('name')}
ID: {character.get('id')}
Title: {character.get('title') or 'None'}
Age: {character.get('age') or 'Unknown'}
Sex: {character.get('sex') or 'Unknown'}
Type: {character.get('type') or 'None'}
Location ID: {character.get('location_id') or 'None'}
Status: {_status_label(character)}
Visibility: {'Private' if character.get('is_private') else 'Public'}

Updated fields: {', '.join(updated_fields)}
"""
        
        return "Character updated, but unexpected response format."

    @mcp.tool()
    async def update_character_hotness(character_name: str, hotness_value: int) -> str:
        """Update a character's hotness attribute by name.
        
        This tool follows the complex flow: find character -> get entity_id -> 
        get entity attributes -> find/update hotness attribute.
        
        Args:
            character_name: The name of the character to update
            hotness_value: The new hotness value (must be an integer, e.g., 7, 8, 9)
        """
        # Step 1: Find the character by name
        characters_data = await make_kanka_request("characters")
        
        if not characters_data or "data" not in characters_data:
            return f"Unable to search for character '{character_name}'."
        
        if "error" in characters_data:
            return f"Error searching for character: {characters_data['error']}"
        
        target_character = None
        for char in characters_data["data"]:
            if char.get("name", "").lower() == character_name.lower():
                target_character = char
                break
        
        if not target_character:
            return f"Character '{character_name}' not found in campaign."
        
        entity_id = target_character.get("entity_id")
        if not entity_id:
            return f"Character '{character_name}' has no entity_id."
        
        # Step 2: Get entity attributes to find hotness attribute
        attributes_data = await make_kanka_request(f"entities/{entity_id}/attributes")
        
        if not attributes_data:
            return f"Unable to fetch attributes for character '{character_name}'."
        
        if "error" in attributes_data:
            return f"Error fetching attributes: {attributes_data['error']}"
        
        # Step 3: Find the hotness attribute
        hotness_attribute = None
        if "data" in attributes_data and attributes_data["data"]:
            for attr in attributes_data["data"]:
                if attr.get("name", "").lower() == "hotness":
                    hotness_attribute = attr
                    break
        
        # Step 4: Update or create the hotness attribute
        if hotness_attribute:
            # Update existing hotness attribute
            attribute_id = hotness_attribute["id"]
            update_data = {
                "name": hotness_attribute.get("name", "Hotness"),  # Preserve original casing
                "value": str(hotness_value),
                "type_id": hotness_attribute.get("type_id", 1)  # Keep existing type
            }
            
            result = await update_kanka_entity(f"entities/{entity_id}/attributes/{attribute_id}", update_data)
            
            if not result:
                return f"Failed to update hotness for '{character_name}'."
            
            if "error" in result:
                return f"Error updating hotness: {result['error']}"
            
            if "data" in result:
                return f"""
Successfully updated hotness for '{character_name}'!

Character: {character_name}
Entity ID: {entity_id}
Attribute: hotness
New Value: {hotness_value}
Previous Value: {hotness_attribute.get('value', 'Unknown')}
"""
        else:
            # Create new hotness attribute
            create_data = {
                "name": "Hotness",  # Use proper casing for new attributes
                "value": str(hotness_value),
                "type_id": 1  # Standard type
            }
            
            result = await create_kanka_entity(f"entities/{entity_id}/attributes", create_data)
            
            if not result:
                return f"Failed to create hotness attribute for '{character_name}'."
            
            if "error" in result:
                return f"Error creating hotness attribute: {result['error']}"
            
            if "data" in result:
                return f"""
Successfully created hotness attribute for '{character_name}'!

Character: {character_name}
Entity ID: {entity_id}
Attribute: hotness
Value: {hotness_value}
(New attribute created)
"""
        
        return "Hotness update completed, but unexpected response format."