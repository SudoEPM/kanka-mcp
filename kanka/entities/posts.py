from mcp.server.fastmcp import FastMCP
from ..client import make_kanka_request, create_kanka_entity, update_kanka_entity

def register_post_tools(mcp: FastMCP):
    """Register all post-related tools with the MCP server."""

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
Tags: {len(post.get('tags', []))} tag(s)
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
Tags: {post.get('tags', [])}
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
