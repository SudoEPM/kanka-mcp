from mcp.server.fastmcp import FastMCP
from ..client import make_kanka_request

async def _fetch_all_pages(endpoint: str) -> tuple[list[dict] | None, str | None]:
    """Walk every page of a Kanka list endpoint.

    Returns (rows, None) on success, or (None, error_message) if any page
    request returns an error response.
    """
    rows: list[dict] = []
    page = 1
    while True:
        sep = "&" if "?" in endpoint else "?"
        data = await make_kanka_request(f"{endpoint}{sep}page={page}")
        if not data:
            return None, f"Unable to fetch {endpoint}."
        if "error" in data:
            return None, data["error"]
        if "data" not in data:
            return None, f"Unexpected response shape from {endpoint}."
        rows.extend(data["data"])
        meta = data.get("meta") or {}
        last_page = meta.get("last_page") or page
        if page >= last_page:
            break
        page += 1
    return rows, None

async def fetch_entity_type_map() -> tuple[dict[int, str], str | None]:
    """Return ({entity_type_id: code}, error_message_or_None) across all pages."""
    rows, err = await _fetch_all_pages("entity_types")
    if err:
        return {}, err
    return {et["id"]: et["code"] for et in (rows or [])}, None

def register_status_tools(mcp: FastMCP):
    """Register all status-related tools with the MCP server."""

    @mcp.tool()
    async def get_all_statuses(entity_type: str = None) -> str:
        """List the campaign's category_statuses (valid values for the status_id field).

        Each status is scoped to one entity type via category_id, which matches the
        entity_type id (e.g. category_id=20 → creature). Pass the entity_type arg
        to filter to a single type.

        Args:
            entity_type: Optional. Singular entity type code, e.g. "creature",
                "character", "location", "quest", "race", "item", "organisation".
        """
        statuses, err = await _fetch_all_pages("category_statuses")
        if err:
            return f"Error: {err}"
        if not statuses:
            return "No statuses found."

        entity_type_map, et_err = await fetch_entity_type_map()
        if et_err:
            return f"Error fetching entity_types: {et_err}"

        if entity_type:
            wanted = entity_type.lower().strip()
            target_cat_id = next(
                (k for k, v in entity_type_map.items() if v == wanted), None
            )
            if target_cat_id is None:
                known = ", ".join(sorted(set(entity_type_map.values())))
                return f"Unknown entity type '{entity_type}'. Known types: {known}"
            statuses = [s for s in statuses if s.get("category_id") == target_cat_id]
            if not statuses:
                return f"No statuses defined for '{entity_type}'."

        by_category: dict[int, list] = {}
        for s in statuses:
            by_category.setdefault(s.get("category_id"), []).append(s)

        lines = ["Available statuses:"]
        for cat_id in sorted(by_category):
            code = entity_type_map.get(cat_id, f"category_id={cat_id}")
            lines.append(f"\n{code}:")
            for s in by_category[cat_id]:
                default = " (default)" if s.get("is_default") else ""
                lines.append(f"  status_id={s.get('id')}: {s.get('key')}{default}")

        return "\n".join(lines)

    @mcp.tool()
    async def get_statuses_for(entity_type: str) -> str:
        """List campaign statuses available for a single entity type.

        Convenience wrapper around get_all_statuses with a required filter.

        Args:
            entity_type: Singular entity type code, e.g. "creature", "character".
        """
        return await get_all_statuses(entity_type=entity_type)
