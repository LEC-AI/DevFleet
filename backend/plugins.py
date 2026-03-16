"""
Claude DevFleet Plugin System — Drop-in extensibility.

Developers can extend DevFleet by:
1. Dropping Python files into `plugins/` directory
2. Each plugin registers MCP tools, hooks, or custom dispatch logic
3. Plugins are auto-loaded at startup

Plugin structure:
    plugins/
      my_plugin.py          # Single-file plugin
      my_complex_plugin/    # Package plugin
        __init__.py
        ...

Each plugin must define a `register(registry)` function:

    def register(registry):
        @registry.tool("my_tool", description="Does something", input_schema={...})
        async def my_tool(args: dict) -> dict:
            return {"result": "hello"}

        @registry.hook("pre_dispatch")
        async def before_dispatch(mission: dict, options: dict) -> dict:
            # Modify options before dispatch
            return options

        @registry.hook("post_complete")
        async def after_complete(mission: dict, report: dict):
            # React to mission completion (e.g., notify Slack, update Jira)
            pass
"""

import importlib
import importlib.util
import logging
import os
import sys
from pathlib import Path
from typing import Callable, Optional

import mcp.types as types

log = logging.getLogger("devfleet.plugins")


class PluginRegistry:
    """Registry that plugins use to register tools, hooks, and extensions."""

    def __init__(self):
        self._tools: list[types.Tool] = []
        self._tool_handlers: dict[str, Callable] = {}
        self._hooks: dict[str, list[Callable]] = {
            "pre_dispatch": [],
            "post_complete": [],
            "post_fail": [],
            "pre_plan": [],
            "post_plan": [],
        }
        self._loaded_plugins: list[str] = []

    def tool(self, name: str, description: str, input_schema: dict):
        """Decorator to register an MCP tool from a plugin.

        Usage:
            @registry.tool("my_tool", description="...", input_schema={...})
            async def my_tool(args: dict) -> dict:
                return {"result": ...}
        """
        def decorator(func: Callable):
            tool_def = types.Tool(
                name=name,
                description=f"[Plugin] {description}",
                inputSchema=input_schema,
            )
            self._tools.append(tool_def)
            self._tool_handlers[name] = func
            log.info(f"Plugin tool registered: {name}")
            return func
        return decorator

    def hook(self, event: str):
        """Decorator to register a lifecycle hook.

        Events:
            pre_dispatch  — Before an agent is dispatched. Receives (mission, options). Return modified options.
            post_complete — After a mission completes. Receives (mission, report).
            post_fail     — After a mission fails. Receives (mission, session).
            pre_plan      — Before AI planner runs. Receives (prompt). Return modified prompt.
            post_plan     — After planner creates project. Receives (project, missions).

        Usage:
            @registry.hook("post_complete")
            async def notify_slack(mission: dict, report: dict):
                await send_slack_message(f"Mission {mission['title']} done!")
        """
        def decorator(func: Callable):
            if event not in self._hooks:
                self._hooks[event] = []
            self._hooks[event].append(func)
            log.info(f"Plugin hook registered: {event} -> {func.__name__}")
            return func
        return decorator

    @property
    def tools(self) -> list[types.Tool]:
        return self._tools

    @property
    def tool_handlers(self) -> dict[str, Callable]:
        return self._tool_handlers

    @property
    def loaded_plugins(self) -> list[str]:
        return self._loaded_plugins


# Global registry
registry = PluginRegistry()


def _plugins_dir() -> Path:
    """Resolve plugins directory — next to backend/ or via env var."""
    custom = os.environ.get("DEVFLEET_PLUGINS_DIR")
    if custom:
        return Path(custom)
    devfleet_root = Path(__file__).parent.parent
    return devfleet_root / "plugins"


def load_plugins():
    """Discover and load all plugins from the plugins/ directory."""
    plugins_path = _plugins_dir()

    if not plugins_path.exists():
        log.info(f"No plugins directory at {plugins_path}, skipping")
        return

    # Add to sys.path so plugins can import each other
    plugins_str = str(plugins_path)
    if plugins_str not in sys.path:
        sys.path.insert(0, plugins_str)

    loaded = 0
    for entry in sorted(plugins_path.iterdir()):
        name = None
        try:
            if entry.is_file() and entry.suffix == ".py" and not entry.name.startswith("_"):
                name = entry.stem
                spec = importlib.util.spec_from_file_location(f"devfleet_plugin_{name}", entry)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)

                if hasattr(mod, "register"):
                    mod.register(registry)
                    registry._loaded_plugins.append(name)
                    loaded += 1
                    log.info(f"Plugin loaded: {name}")
                else:
                    log.warning(f"Plugin {name} has no register() function, skipping")

            elif entry.is_dir() and (entry / "__init__.py").exists():
                name = entry.name
                spec = importlib.util.spec_from_file_location(
                    f"devfleet_plugin_{name}",
                    entry / "__init__.py",
                    submodule_search_locations=[str(entry)],
                )
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)

                if hasattr(mod, "register"):
                    mod.register(registry)
                    registry._loaded_plugins.append(name)
                    loaded += 1
                    log.info(f"Plugin loaded: {name} (package)")
                else:
                    log.warning(f"Plugin {name} has no register() function, skipping")

        except Exception:
            log.exception(f"Failed to load plugin: {name or entry}")

    log.info(f"Loaded {loaded} plugin(s), {len(registry.tools)} custom tool(s)")


async def run_hooks(event: str, *args, **kwargs):
    """Run all hooks registered for an event. Returns modified first arg if applicable."""
    hooks = registry._hooks.get(event, [])
    result = args[0] if args else None

    for hook_fn in hooks:
        try:
            ret = await hook_fn(*args, **kwargs)
            # For pre_* hooks, allow modifying the input
            if event.startswith("pre_") and ret is not None:
                result = ret
                # Update args for next hook in chain
                args = (result,) + args[1:]
        except Exception:
            log.exception(f"Plugin hook {event}:{hook_fn.__name__} failed")

    return result
