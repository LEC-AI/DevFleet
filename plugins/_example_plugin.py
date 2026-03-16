"""
Example Claude DevFleet Plugin — rename to remove the underscore prefix to activate.

This shows how to:
1. Add custom MCP tools (available to any connected MCP client)
2. Add lifecycle hooks (run before/after dispatch, completion, etc.)

To create your own plugin:
1. Copy this file to plugins/my_plugin.py (no underscore prefix)
2. Implement your register() function
3. Restart DevFleet — your plugin loads automatically

Plugins can import anything from the backend (db, models, etc.)
and any pip-installed package.
"""


def register(registry):
    """Called by Claude DevFleet at startup. Use registry to add tools and hooks."""

    # ── Example: Custom MCP tool ──
    # This tool becomes available to any MCP client connected to DevFleet

    @registry.tool(
        name="hello_world",
        description="A simple example plugin tool that echoes back a greeting.",
        input_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name to greet"},
            },
            "required": ["name"],
        },
    )
    async def hello_world(args: dict) -> dict:
        return {"message": f"Hello from Claude DevFleet plugin, {args['name']}!"}

    # ── Example: Post-completion hook ──
    # Runs after any mission completes successfully.
    # Use for notifications (Slack, email), logging, or triggering external systems.

    # @registry.hook("post_complete")
    # async def notify_on_complete(mission: dict, report: dict):
    #     # Example: Send a Slack notification
    #     # import httpx
    #     # await httpx.AsyncClient().post(SLACK_WEBHOOK, json={
    #     #     "text": f"Mission '{mission['title']}' completed! Files changed: {report['files_changed']}"
    #     # })
    #     pass

    # ── Example: Pre-dispatch hook ──
    # Runs before an agent is dispatched. Can modify dispatch options.
    # Use for: adding custom tools, enforcing policies, injecting context.

    # @registry.hook("pre_dispatch")
    # async def enforce_budget(mission: dict, options: dict) -> dict:
    #     # Cap budget at $1 for all missions
    #     if options.get("max_budget_usd", 999) > 1.0:
    #         options["max_budget_usd"] = 1.0
    #     return options
