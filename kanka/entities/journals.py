from mcp.server.fastmcp import FastMCP
from ..client import make_kanka_request, create_kanka_entity, update_kanka_entity

def format_journal_summary(journal: dict) -> str:
    """Format a journal into a readable summary."""
    return f"""
Name: {journal.get('name', 'Unknown')}
ID: {journal.get('id', 'N/A')}
Entity ID: {journal.get('entity_id', 'N/A')}
Type: {journal.get('type') or 'None'}
Date: {journal.get('date') or 'No date'}
Author ID: {journal.get('author_id') or 'None'}
Calendar Date: {journal.get('calendar_year')}/{journal.get('calendar_month')}/{journal.get('calendar_day') if journal.get('calendar_year') else 'Not set'}
Parent Journal ID: {journal.get('journal_id') or 'None'}
Tags: {len(journal.get('tags', []))} tag(s)
Is Private: {'Yes' if journal.get('is_private') else 'No'}
"""

def format_journal_detail(journal: dict) -> str:
    """Format a journal's full details."""
    calendar_info = ""
    if journal.get('calendar_year'):
        calendar_info = f"\nCalendar Date: Year {journal.get('calendar_year')}, Month {journal.get('calendar_month')}, Day {journal.get('calendar_day')}"
        if journal.get('calendar_event_length'):
            calendar_info += f" (Duration: {journal.get('calendar_event_length')} days)"
    
    return f"""
Name: {journal.get('name', 'Unknown')}
ID: {journal.get('id', 'N/A')}
Entity ID: {journal.get('entity_id', 'N/A')}
Type: {journal.get('type') or 'None'}
Date: {journal.get('date') or 'No date'}
Author ID: {journal.get('author_id') or 'None'}
Parent Journal ID: {journal.get('journal_id') or 'None (Top-level journal)'}
{calendar_info}

Entry/Content:
{journal.get('entry', 'No content available.')}

Tags: {journal.get('tags', [])}
Is Private: {'Yes' if journal.get('is_private') else 'No'}
Created: {journal.get('created_at')}
Last Updated: {journal.get('updated_at')}
"""

def register_journal_tools(mcp: FastMCP):
    """Register all journal-related tools with the MCP server."""
    
    @mcp.tool()
    async def get_all_journals() -> str:
        """Get a list of all journals in the campaign.
        
        Returns a summary of all journals including their name, ID, type, and date info.
        """
        data = await make_kanka_request("journals")
        
        if not data:
            return "Unable to fetch journals."
        
        if "error" in data:
            return f"Error: {data['error']}"
        
        if "data" not in data or not data["data"]:
            return "No journals found in this campaign."
        
        journals = [format_journal_summary(journal) for journal in data["data"]]
        return "\n---\n".join(journals)

    @mcp.tool()
    async def get_journal(journal_id: int) -> str:
        """Get detailed information about a specific journal entry.
        
        Args:
            journal_id: The ID of the journal to retrieve
        """
        data = await make_kanka_request(f"journals/{journal_id}")
        
        if not data:
            return f"Unable to fetch journal with ID {journal_id}."
        
        if "error" in data:
            return f"Error: {data['error']}"
        
        if "data" not in data:
            return f"No journal found with ID {journal_id}."
        
        return format_journal_detail(data["data"])
    
    blah

    @mcp.tool()
    async def create_journal(
        name: str,
        entry: str = "",
        journal_type: str = "",
        date: str = "",
        author_id: int = None,
        journal_id: int = None,
        tags: list[int] = None,
        is_private: bool = False,
        tooltip: str = ""
    ) -> str:
        """Create a new journal in the campaign.

        Args:
            name: The journal's title (required)
            entry: HTML content of the journal
            journal_type: Journal type/category (e.g., "Session", "Log")
            date: Session or event date as a string
            author_id: Entity ID of the journal's author
            journal_id: Parent journal ID for creating sub-journals
            tags: List of tag IDs to apply to this journal
            is_private: Whether the journal is only visible to admins
            tooltip: Hover text for the journal (premium feature)
        """
        journal_data = {
            "name": name,
            "entry": entry,
            "type": journal_type,
            "date": date,
            "is_private": is_private,
            "tooltip": tooltip
        }

        # Only include optional ID fields if provided
        if author_id is not None:
            journal_data["author_id"] = author_id
        if journal_id is not None:
            journal_data["journal_id"] = journal_id

        # Add tags if provided
        if tags is not None and len(tags) > 0:
            journal_data["tags"] = tags
            journal_data["save_tags"] = True

        # Remove empty string values to keep the request clean
        journal_data = {k: v for k, v in journal_data.items() if v != ""}

        result = await create_kanka_entity("journals", journal_data)

        if not result:
            return "Failed to create journal."

        if "error" in result:
            return f"Error creating journal: {result['error']}"

        if "data" in result:
            journal = result["data"]
            return f"""
Successfully created journal!

Name: {journal.get('name')}
Journal ID: {journal.get('id')}
Entity ID: {journal.get('entity_id')}
Type: {journal.get('type') or 'None'}
Date: {journal.get('date') or 'None'}
Author ID: {journal.get('author_id') or 'None'}
Parent Journal ID: {journal.get('journal_id') or 'None (Top-level)'}
Tags: {len(journal.get('tags', []))} tag(s)
Visibility: {'Private' if journal.get('is_private') else 'Public'}

The journal has been added to your campaign.
"""

        return "Journal created, but unexpected response format."

    @mcp.tool()
    async def update_journal(
        journal_name: str,
        entry: str = None,
        journal_type: str = None,
        date: str = None,
        author_id: int = None,
        journal_id: int = None,
        tags: list[int] = None,
        is_private: bool = None,
        tooltip: str = None
    ) -> str:
        """Update an existing journal by name.

        First searches for the journal by name, then updates the specified fields.
        Only provided fields will be updated - others remain unchanged.

        Args:
            journal_name: The name of the journal to update (used for search)
            entry: HTML content of the journal
            journal_type: Journal type/category
            date: Session or event date as a string
            author_id: Entity ID of the journal's author
            journal_id: Parent journal ID
            tags: List of tag IDs to apply to this journal (replaces existing tags)
            is_private: Whether the journal is only visible to admins
            tooltip: Hover text for the journal (premium feature)
        """
        # First, search for the journal by name
        journals_data = await make_kanka_request("journals")

        if not journals_data or "data" not in journals_data:
            return f"Unable to search for journal '{journal_name}'."

        if "error" in journals_data:
            return f"Error searching for journal: {journals_data['error']}"

        # Find journal with matching name (case-insensitive)
        target_journal = None
        for journal in journals_data["data"]:
            if journal.get("name", "").lower() == journal_name.lower():
                target_journal = journal
                break

        if not target_journal:
            return f"Journal '{journal_name}' not found in campaign."

        journal_id_to_update = target_journal["id"]

        # Build update data with only provided values
        update_data = {}
        if entry is not None:
            update_data["entry"] = entry
        if journal_type is not None:
            update_data["type"] = journal_type
        if date is not None:
            update_data["date"] = date
        if author_id is not None:
            update_data["author_id"] = author_id
        if journal_id is not None:
            update_data["journal_id"] = journal_id
        if is_private is not None:
            update_data["is_private"] = is_private
        if tooltip is not None:
            update_data["tooltip"] = tooltip
        if tags is not None:
            update_data["tags"] = tags
            update_data["save_tags"] = True

        if not update_data:
            return "No updates provided. Please specify at least one field to update."

        # Update the journal
        result = await update_kanka_entity(f"journals/{journal_id_to_update}", update_data)

        if not result:
            return f"Failed to update journal '{journal_name}'."

        if "error" in result:
            return f"Error updating journal: {result['error']}"

        if "data" in result:
            journal = result["data"]
            updated_fields = list(update_data.keys())
            return f"""
Successfully updated journal '{journal_name}'!

Name: {journal.get('name')}
Journal ID: {journal.get('id')}
Entity ID: {journal.get('entity_id')}
Type: {journal.get('type') or 'None'}
Date: {journal.get('date') or 'None'}
Author ID: {journal.get('author_id') or 'None'}
Parent Journal ID: {journal.get('journal_id') or 'None (Top-level)'}
Tags: {len(journal.get('tags', []))} tag(s)
Visibility: {'Private' if journal.get('is_private') else 'Public'}

Updated fields: {', '.join(updated_fields)}
"""

        return "Journal updated, but unexpected response format."

    @mcp.tool()
    async def create_session_recap(session_title: str, entry: str, tags: list[int] = None) -> str:
        """Create a new session recap post inside the Campaign 2 Recaps journal.

        This tool creates posts within the Campaign 2 Recaps journal (ID: 8112269).
        Posts appear as individual entries within the journal rather than as separate sub-journals.
        The post will always be positioned at the top (position 1) for newest-first ordering.

        Session titles should follow the format: "Session ## - Descriptive Title"
        For example: "Session 1 - The Beginning", "Session 43 - Into the Abyss"

        If unsure of the session number, ask for the session number before uploading.

        Args:
            session_title: The title/name of the session in format "Session ## - Title"
            entry: The HTML content of the session recap
            tags: Optional list of tag IDs to apply to this post
        """
        # Campaign 2 Recaps journal entity ID
        CAMPAIGN_2_JOURNAL_ENTITY_ID = 8112269

        post_data = {
            "name": session_title,
            "entry": entry,
            "entity_id": CAMPAIGN_2_JOURNAL_ENTITY_ID,
            "position": 1,
            "is_private": False
        }

        # Add tags if provided
        if tags is not None and len(tags) > 0:
            post_data["tags"] = tags
            post_data["save_tags"] = True
        
        result = await create_kanka_entity(f"entities/{CAMPAIGN_2_JOURNAL_ENTITY_ID}/posts", post_data)
        
        if not result:
            return "Failed to create session recap post."
        
        if "error" in result:
            return f"Error creating session recap post: {result['error']}"
        
        if "data" in result:
            post = result["data"]
            return f"""
Successfully created session recap post!

Name: {post.get('name')}
Post ID: {post.get('id')}
Entity ID: {post.get('entity_id')}
Position: {post.get('position')}
Visibility: {'Private' if post.get('is_private') else 'Public'}

The session recap post has been added to the Campaign 2 Recaps journal in the correct order.
"""
        
        return "Session recap post created, but unexpected response format."

    @mcp.tool()
    async def get_posts(entity_id: int) -> str:
        """Get all posts from an entity (journal, character, location, etc.).

        This retrieves all posts attached to an entity, ordered by position.
        Useful for viewing session recaps, character notes, or any entity posts.

        Args:
            entity_id: The entity ID to retrieve posts from
        """
        data = await make_kanka_request(f"entities/{entity_id}/posts")

        if not data:
            return f"Unable to fetch posts for entity {entity_id}."

        if "error" in data:
            return f"Error: {data['error']}"

        if "data" not in data or not data["data"]:
            return f"No posts found for entity {entity_id}."

        posts = data["data"]
        # Sort by position (ascending order)
        posts.sort(key=lambda p: p.get('position', 999999))

        formatted_posts = []
        for post in posts:
            post_info = f"""
Name: {post.get('name', 'Untitled')}
Post ID: {post.get('id')}
Position: {post.get('position')}
Visibility: {'Private' if post.get('is_private') else 'Public'}
Created: {post.get('created_at')}
Updated: {post.get('updated_at')}

Content Preview:
{post.get('entry', 'No content')[:200]}{'...' if len(post.get('entry', '')) > 200 else ''}
"""
            formatted_posts.append(post_info.strip())

        header = f"Found {len(posts)} post(s) for entity {entity_id}:\n"
        return header + "\n---\n".join(formatted_posts)

    @mcp.tool()
    async def get_post(entity_id: int, post_id: int) -> str:
        """Get detailed information about a specific post, including full content.

        Args:
            entity_id: The entity ID containing the post
            post_id: The ID of the post to retrieve
        """
        data = await make_kanka_request(f"entities/{entity_id}/posts/{post_id}")

        if not data:
            return f"Unable to fetch post {post_id} from entity {entity_id}."

        if "error" in data:
            return f"Error: {data['error']}"

        if "data" not in data:
            return f"No post found with ID {post_id} in entity {entity_id}."

        post = data["data"]
        return f"""
Name: {post.get('name', 'Untitled')}
Post ID: {post.get('id')}
Entity ID: {post.get('entity_id')}
Position: {post.get('position')}
Visibility: {'Private' if post.get('is_private') else 'Public'}
Created: {post.get('created_at')}
Updated: {post.get('updated_at')}

Full Content:
{post.get('entry', 'No content available.')}
"""

    @mcp.tool()
    async def create_post(
        entity_id: int,
        title: str,
        content: str,
        position: int = None,
        is_private: bool = False,
        tags: list[int] = None
    ) -> str:
        """Create a new post in any entity (journal, character, etc.).

        Args:
            entity_id: The entity ID to create the post in
            title: The title/name of the post
            content: The HTML content of the post
            position: Optional position for ordering (if None, will auto-calculate next position)
            is_private: Whether the post is private (admin-only)
            tags: Optional list of tag IDs to apply to this post
        """
        # If no position specified, calculate the next available position
        if position is None:
            posts_data = await make_kanka_request(f"entities/{entity_id}/posts")

            next_position = 1  # Default position if no posts exist
            if posts_data and "data" in posts_data and posts_data["data"]:
                # Find the highest position value among existing posts
                max_position = 0
                for post in posts_data["data"]:
                    post_position = post.get("position")
                    if post_position is not None and post_position > max_position:
                        max_position = post_position
                next_position = max_position + 1

            position = next_position

        post_data = {
            "name": title,
            "entry": content,
            "entity_id": entity_id,
            "position": position,
            "is_private": is_private
        }

        # Add tags if provided
        if tags is not None and len(tags) > 0:
            post_data["tags"] = tags
            post_data["save_tags"] = True
        
        result = await create_kanka_entity(f"entities/{entity_id}/posts", post_data)
        
        if not result:
            return "Failed to create post."
        
        if "error" in result:
            return f"Error creating post: {result['error']}"
        
        if "data" in result:
            post = result["data"]
            return f"""
Successfully created post!

Title: {post.get('name')}
Post ID: {post.get('id')}
Entity ID: {post.get('entity_id')}
Position: {post.get('position')}
Visibility: {'Private' if post.get('is_private') else 'Public'}

The post has been added to entity {entity_id}.
"""
        
        return "Post created, but unexpected response format."

    @mcp.tool()
    async def update_post(
        entity_id: int,
        post_id: int,
        title: str = None,
        content: str = None,
        position: int = None,
        is_private: bool = None,
        tags: list[int] = None
    ) -> str:
        """Update an existing post in any entity.

        Only provided fields will be updated - others remain unchanged.

        Args:
            entity_id: The entity ID containing the post
            post_id: The ID of the post to update
            title: New title/name for the post
            content: New HTML content for the post
            position: New position for ordering
            is_private: New privacy setting
            tags: New list of tag IDs to apply to this post (replaces existing tags)
        """
        # Build update data with only provided values
        update_data = {}
        if title is not None:
            update_data["name"] = title
        if content is not None:
            update_data["entry"] = content
        if position is not None:
            update_data["position"] = position
        if is_private is not None:
            update_data["is_private"] = is_private
        if tags is not None:
            update_data["tags"] = tags
            update_data["save_tags"] = True

        if not update_data:
            return "No updates provided. Please specify at least one field to update."

        # Always include entity_id in update data
        update_data["entity_id"] = entity_id
        
        result = await update_kanka_entity(f"entities/{entity_id}/posts/{post_id}", update_data)
        
        if not result:
            return f"Failed to update post {post_id}."
        
        if "error" in result:
            return f"Error updating post: {result['error']}"
        
        if "data" in result:
            post = result["data"]
            updated_fields = [k for k in update_data.keys() if k != "entity_id"]
            return f"""
Successfully updated post!

Title: {post.get('name')}
Post ID: {post.get('id')}
Entity ID: {post.get('entity_id')}
Position: {post.get('position')}
Visibility: {'Private' if post.get('is_private') else 'Public'}

Updated fields: {', '.join(updated_fields)}
"""
        
        return "Post updated, but unexpected response format."