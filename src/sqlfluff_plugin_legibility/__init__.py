"""SQLFluff plugin hooks for legibility rules."""

from typing import Any

from sqlfluff.core.config import load_config_resource
from sqlfluff.core.plugin import hookimpl
from sqlfluff.core.rules import BaseRule, ConfigInfo


@hookimpl
def get_rules() -> list[type[BaseRule]]:
    """Return the plugin rules."""
    from sqlfluff_plugin_legibility.rules import (
        Rule_Legibility_L001,
        Rule_Legibility_L002,
    )

    return [Rule_Legibility_L001, Rule_Legibility_L002]


@hookimpl
def load_default_config() -> dict[str, Any]:
    """Load default rule configuration."""
    return load_config_resource(
        package="sqlfluff_plugin_legibility",
        file_name="plugin_default_config.cfg",
    )


@hookimpl
def get_configs_info() -> dict[str, ConfigInfo]:
    """Describe the plugin configuration."""
    return {
        "comment_matchers": {
            "definition": "Comma-separated regexes that allow individual comments.",
        },
        "comment_prefix_identifiers": {
            "definition": "Comma-separated identifiers allowed at a comment's start.",
        },
        "comment_suffix_identifiers": {
            "definition": "Comma-separated identifiers allowed at a comment's end.",
        },
        "directive_matchers": {
            "definition": "Comma-separated regexes that identify machine directives.",
        },
    }
