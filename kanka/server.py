from mcp.server.fastmcp import FastMCP
import sys
from .client import KANKA_API_TOKEN, KANKA_CAMPAIGN_ID
from .entities.characters import register_character_tools
from .entities.journals import register_journal_tools
from .entities.quests import register_quest_tools
from .entities.organizations import register_organization_tools

# Initialize FastMCP server
mcp = FastMCP("kanka")

# Register all entity tools
register_character_tools(mcp)
register_journal_tools(mcp)
register_quest_tools(mcp)
register_organization_tools(mcp)

def main():
    # Check if required env vars are set
    if not KANKA_API_TOKEN:
        print("ERROR: KANKA_API_TOKEN environment variable not set!", file=sys.stderr)
        return
    if not KANKA_CAMPAIGN_ID:
        print("ERROR: KANKA_CAMPAIGN_ID environment variable not set!", file=sys.stderr)
        return
    
    # Initialize and run the server
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()