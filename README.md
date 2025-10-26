# Kanka MCP Server

A Model Context Protocol (MCP) server that provides AI assistants with tools to interact with the [Kanka](https://kanka.io) campaign management platform. This allows LLMs like Claude to create, read, and update your Kanka campaign data through natural conversation.

## Overview

This MCP server enables AI assistants to help you maintain and manage your Kanka campaign by providing tools for interacting with various entities. This allows for AI assistants to perform actions like creating or updating character records, creating or updating journal entries, and more!

### What This Server Can Do

- **Create & Update** campaign entities (characters, locations, creatures, quests, etc.)
- **Retrieve & Search** campaign data for reference and context
- **Manage Posts** on any entity (session recaps, character notes, location descriptions)
- **Establish Connections** between entities with attitudes and relationship details
- **Track Progress** on quests with automatic image assignment
- **Update Calendar Dates** for in-game time tracking

### What This Server Cannot Do

- **Delete entities** - This server deliberately excludes delete operations to prevent accidental data loss
- **Modify core campaign settings** - Campaign-level configuration remains manual
- **Upload new images** - Uses existing gallery images via UUID references

## Setup

### Prerequisites

- Python 3.13 or higher
- [uv](https://docs.astral.sh/uv/) package manager (recommended) or pip
- A [Kanka](https://kanka.io) account with an active campaign
- Kanka API token with appropriate permissions

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/kanka-mcp.git
   cd kanka-mcp
   ```

2. **Install dependencies:**

   Using `uv` (recommended):
   ```bash
   uv sync
   ```

   Using `pip`:
   ```bash
   pip install -e .
   ```

3. **Configure environment variables:**

   Create a `.env` file in the project root:
   ```env
   KANKA_API_TOKEN=your_api_token_here
   KANKA_CAMPAIGN_ID=your_campaign_id_here
   ```

   - **Get your API token**: Go to [Kanka Settings > API](https://app.kanka.io/settings/api) and generate a personal access token
   - **Find your campaign ID**: Visit your campaign in Kanka - the ID is in the URL: `https://app.kanka.io/campaign/{CAMPAIGN_ID}/`

### Claude Desktop Setup

To use this MCP server with Claude Desktop, add it to your Claude configuration file:

**macOS/Linux**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "kanka": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/kanka-mcp",
        "run",
        "kanka"
      ],
      "env": {
        "KANKA_API_TOKEN": "your_api_token_here",
        "KANKA_CAMPAIGN_ID": "your_campaign_id_here"
      }
    }
  }
}
```

**Important**: Replace `/absolute/path/to/kanka-mcp` with the actual absolute path to your clone of this repository.

After updating the config, restart Claude Desktop. You should see the Kanka MCP tools available in the tools menu.

### Other LLM Integrations

This MCP server follows the standard Model Context Protocol and can be integrated with any MCP-compatible client:

- **Continue.dev**: See [MCP documentation for Continue](https://docs.continue.dev/features/model-context-protocol)
- **Zed Editor**: See [Zed MCP documentation](https://zed.dev/docs/assistant/model-context-protocol)
- **Custom Integrations**: Reference the [MCP SDK documentation](https://modelcontextprotocol.io/introduction)

For all integrations, you'll need to provide the same environment variables (`KANKA_API_TOKEN` and `KANKA_CAMPAIGN_ID`) and ensure the server can be invoked via the command line.

### Running Locally / Testing

To test the server locally or debug issues:

```bash
# Using uv (recommended)
uv run kanka

# Using Python directly
python -m kanka.server
```

The server runs in stdio mode and communicates via JSON-RPC. If your environment variables are not set correctly, you'll see error messages indicating which variables are missing.

## Campaign-Specific Customizations

This MCP server was originally built for a specific campaign and includes some hardcoded values. If you're using this with your own campaign, you may want to customize the following:

### Hotness Attribute (Character Tools)

The `update_character_hotness` tool manages a custom attribute called "Hotness" which was created for my campaign as a character rating system. This will work with any campaign but creates/updates a character attribute named "Hotness". You can either:
- Use this tool as-is if you want a similar attribute
- Modify the tool to use a different attribute name
- Remove the tool if not needed

**Location**: `kanka/entities/characters.py` lines 271-375

### Session Recap Journal (Journal Tools)

The `create_session_recap` tool targets a specific journal entity (ID: `8112269`) which is the "Campaign 2 Recaps" journal in my campaign. To use this with your campaign:

1. Create a journal in your Kanka campaign for session recaps
2. Get the journal's **entity_id** (not the journal_id)
3. Update the constant in `kanka/entities/journals.py` line 107:
   ```python
   CAMPAIGN_2_JOURNAL_ENTITY_ID = your_journal_entity_id
   ```

Alternatively, use the generic `create_post` tool instead, which works with any entity.

**Location**: `kanka/entities/journals.py` lines 89-139

### Quest Images (Quest Tools)

The quest creation and update tools automatically assign images based on quest type and status using hardcoded gallery image UUIDs from my campaign:

```python
QUEST_IMAGES = {
    "completed": "a019c307-6c4b-48c8-82e4-da12aa72bf1b",   # Green checkmark
    "combat": "a019c682-3641-4a88-878f-f35a271eee79",      # Crossed swords
    "locate": "a019c5e9-edb1-436d-9048-0dbccd0ca22d",      # Map with magnifying glass
    "investigate": "a019c64b-68ce-4d8d-8c79-1bca39358bff", # Magnifying glass
    "generic": "a019c568-65ad-44c1-9d24-d0980262d207"      # Scroll with quill
}
```

To use this with your campaign:

1. Upload quest images to your Kanka campaign gallery
2. Get the image UUIDs from the gallery
3. Update the `QUEST_IMAGES` dictionary in `kanka/entities/quests.py` lines 5-11

Or simply remove the auto-assignment logic and let the AI specify `entity_image_uuid` manually when creating quests.

**Location**: `kanka/entities/quests.py` lines 5-11, 153-160, 267-280

## Available Tools

### Character Tools (5 tools)

**Get Operations:**
- `get_all_characters()` - List all characters with summaries (name, title, age, sex, death status)
- `get_character(character_id)` - Get detailed information about a specific character

**Create/Update Operations:**
- `create_character(name, entry, title, age, sex, pronouns, character_type, location_id, is_dead, is_private)` - Create a new character
- `update_character(character_name, ...)` - Update an existing character by name
- `update_character_hotness(character_name, hotness_value)` - Update character's hotness attribute *Campaign-specific*

**Key Features:**
- Search by name for updates (case-insensitive)
- Support for pronouns and character types
- Track death status and privacy settings
- Link characters to locations

---

### Journal Tools (7 tools)

**Get Operations:**
- `get_all_journals()` - List all journals with summaries (name, type, date, calendar info)
- `get_journal(journal_id)` - Get detailed information about a specific journal

**Post Operations:**
- `get_posts(entity_id)` - Get all posts from any entity (sorted by position)
- `get_post(entity_id, post_id)` - Get full details of a specific post
- `create_post(entity_id, title, content, position, is_private)` - Create a post on any entity
- `update_post(entity_id, post_id, ...)` - Update an existing post
- `create_session_recap(session_title, entry)` - Create session recap in Campaign 2 Recaps journal *Campaign-specific*

**Key Features:**
- Posts work on ANY entity type (journals, characters, locations, etc.)
- Automatic position calculation for post ordering
- HTML content support
- Session recap tool positions new posts at top (position 1)

---

### Quest Tools (4 tools)

**Get Operations:**
- `get_all_quests()` - List all quests with summaries (name, status, type, parent quest)
- `get_quest(quest_id)` - Get detailed information about a specific quest

**Create/Update Operations:**
- `create_quest(name, entry, quest_type, is_completed, parent_quest_id, instigator_id, location_id, entity_image_uuid, is_private)` - Create a new quest
- `update_quest(quest_name, ...)` - Update an existing quest by name

**Key Features:**
- Automatic image assignment based on keywords (combat, locate, investigate, generic) *Uses campaign-specific image UUIDs*
- Completion status automatically assigns checkmark image
- Support for sub-quests via parent_quest_id
- Track quest givers via instigator_id
- Search by name for updates

---

### Organization Tools (3 tools)

**Get Operations:**
- `get_all_organizations()` - List all organizations with summaries (name, type, status, locations, members)
- `get_organization(organization_id)` - Get detailed information about a specific organization

**Create/Update Operations:**
- `create_organization(name, entry, org_type, is_defunct, parent_organization_id, location_ids, entity_image_uuid, is_private)` - Create a new organization
- `update_organization(organization_name, ...)` - Update an existing organization by name

**Key Features:**
- Support for hierarchical organizations via parent_organization_id
- Track defunct/inactive organizations
- Associate organizations with multiple locations
- Search by name for updates

---

### Calendar Tools (3 tools)

**Get Operations:**
- `get_all_calendars()` - List all calendars with summaries (name, current date, months, weekdays)
- `get_calendar(calendar_id)` - Get detailed calendar structure (months, weekdays, seasons, moons)

**Update Operations:**
- `update_calendar_date(calendar_id, current_year, current_month, current_day)` - Update ONLY the current date

**Key Features:**
- Restricted update tool (only modifies current date, not calendar structure)
- Requires at least one date field
- Use `get_calendar()` first to understand the calendar structure before updating

---

### Location Tools (3 tools)

**Get Operations:**
- `get_all_locations()` - List all locations with summaries (name, type, status, parent location)
- `get_location(location_id)` - Get detailed information about a specific location

**Create/Update Operations:**
- `create_location(name, entry, location_type, is_destroyed, parent_location_id, entity_image_uuid, is_private)` - Create a new location
- `update_location(location_name, ...)` - Update an existing location by name

**Key Features:**
- Support for hierarchical locations via parent_location_id
- Track destroyed/ruined locations
- Search by name for updates
- Common location types: City, Forest, Dungeon, Country, etc.

---

### Event Tools (3 tools)

**Get Operations:**
- `get_all_events()` - List all events with summaries (name, date, calendar info, location)
- `get_event(event_id)` - Get detailed information about a specific event

**Create/Update Operations:**
- `create_event(name, entry, event_type, date, parent_event_id, calendar_id, calendar_year, calendar_month, calendar_day, location_id, entity_image_uuid, is_private)` - Create a new event
- `update_event(event_name, ...)` - Update an existing event by name

**Key Features:**
- Calendar integration (requires calendar_id, year, month, day together)
- Support for hierarchical events via parent_event_id
- Display date string for non-calendar events
- Recommend using `get_calendar()` first to validate month/day ranges
- Search by name for updates

---

### Creature Tools (3 tools)

**Get Operations:**
- `get_all_creatures()` - List all creatures with summaries (name, type, status, parent creature)
- `get_creature(creature_id)` - Get detailed information about a specific creature

**Create/Update Operations:**
- `create_creature(name, entry, creature_type, is_extinct, is_dead, parent_creature_id, entity_image_uuid, is_private)` - Create a new creature
- `update_creature(creature_name, ...)` - Update an existing creature by name

**Key Features:**
- Track both species extinction (`is_extinct`) and individual death (`is_dead`)
- Support for sub-species/variants via parent_creature_id
- Search by name for updates
- Common creature types: Dragon, Beast, Humanoid, Undead, etc.

---

### Connection Tools (5 tools)

> **Important Note**: In Kanka's API these are called "relations" but they appear as "Connections" in the GUI. The tools use both terms interchangeably.

> **Critical**: Connections use **ENTITY IDs**, not type-specific IDs (like character_id, location_id, creature_id, etc.). Every entity in Kanka has an `entity_id` field - you must use this value.

**Get Operations:**
- `get_all_connections()` - List all connections in the campaign
- `get_entity_connections(entity_id)` - Get all connections for a specific entity
- `get_connection(entity_id, connection_id)` - Get detailed information about a specific connection

**Create/Update Operations:**
- `create_connection(owner_id, target_id, relation, attitude, colour, two_way, is_pinned, visibility_id)` - Create a new connection between entities
- `update_connection(owner_id, connection_id, ...)` - Update an existing connection

**Key Features:**
- **Attitude scoring**: -100 (hostile) to 100 (friendly)
- **Color coding**: Hex color codes for visual organization
- **Bidirectional connections**: `two_way=True` creates both directions automatically
- **Pinning**: Display connections in entity submenus
- **Visibility control**: 1=All, 2=Self, 3=Admin, 4=Self&Admin, 5=Members
- Works between ANY entity types (character�character, character�location, etc.)

**Example Connection Relations:**
- "Father of", "Mother of", "Sibling of"
- "Member of", "Leader of"
- "Enemy of", "Ally of", "Rival of"
- "Lives in", "Owns", "Works at"

---

## Tool Summary Statistics

- **Total Tools**: 34 MCP tools
- **Entity Types**: 9 (Characters, Journals, Quests, Organizations, Calendars, Locations, Events, Creatures, Connections)
- **GET Operations**: 13 tools
- **CREATE Operations**: 9 tools
- **UPDATE Operations**: 8 tools
- **Special Tools**: 4 (session recaps, post management, hotness updates, entity connections)

## Common Patterns

### Entity IDs vs Type-Specific IDs

Kanka uses two types of IDs:
- **Type-specific IDs**: `character_id`, `location_id`, `creature_id`, etc. (used for API endpoints)
- **Entity IDs**: `entity_id` (universal ID used for posts, connections, attributes)

Most tools use type-specific IDs, but **connections and posts require entity IDs**. When you retrieve any entity, it includes both IDs in the response.

### Update by Name

All update tools search by name first (case-insensitive), then update by ID. This makes it easier to work conversationally:
```
"Update the character named 'Aria' to have age 25"
```

### Privacy Settings

The `is_private` parameter controls visibility:
- `false` (default): Visible to all campaign members
- `true`: Only visible to admin members

### HTML Content

The `entry` parameter accepts HTML content for rich formatting:
```html
<p>This is a <strong>bold</strong> description.</p>
<ul>
  <li>Item one</li>
  <li>Item two</li>
</ul>
```

## Error Handling

The server provides detailed error messages:
- **Missing environment variables**: "ERROR: KANKA_API_TOKEN environment variable not set!"
- **Entity not found**: "Character 'Name' not found in campaign."
- **API errors**: "HTTP 404: {response details}"
- **Validation errors**: "Attitude must be between -100 and 100."

## Development

### Dependencies

- **httpx** (e0.28.1): Async HTTP client for Kanka API
- **mcp[cli]** (e1.16.0): Model Context Protocol SDK
- **python-dotenv** (e1.1.1): Environment variable management

### Adding New Tools

1. Create or modify entity file in `kanka/entities/`
2. Define tool function with `@mcp.tool()` decorator
3. Add comprehensive docstring with parameter descriptions
4. Import and register in `kanka/server.py`
5. Update this README with tool documentation

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

### Guidelines

- Follow existing code patterns and naming conventions
- Include comprehensive docstrings for all tools
- Test tools against a real Kanka campaign
- Update README documentation for new tools
- Do not include delete operations

## License

[MIT License](LICENSE) - feel free to use this in your own campaigns!

## Acknowledgments

- Built using the [Model Context Protocol](https://modelcontextprotocol.io/) by Anthropic
- Integrates with [Kanka](https://kanka.io), the amazing campaign management platform
- Powered by [FastMCP](https://github.com/jlowin/fastmcp) for simplified MCP server development

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/kanka-mcp/issues)
- **Kanka API Docs**: https://app.kanka.io/api-docs
- **MCP Documentation**: https://modelcontextprotocol.io/

---

**Happy campaign managing!**
