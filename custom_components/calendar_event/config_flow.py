"""Config flow for calendar_event integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

import voluptuous as vol
from homeassistant.helpers import selector
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaConfigFlowHandler,
    SchemaFlowFormStep,
)

from .const import (
    CONF_CALENDAR_ENTITY_ID,
    CONF_COMPARISON_METHOD,
    CONF_SUMMARY,
    DOMAIN,
)

_COMPARISON_METHODS = ["contains", "starts_with", "ends_with", "exactly"]

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CALENDAR_ENTITY_ID): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="calendar")
        ),
        vol.Required(CONF_SUMMARY): selector.TextSelector(),
        vol.Required(
            CONF_COMPARISON_METHOD, default="contains"
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=_COMPARISON_METHODS,
                mode="dropdown",
                translation_key=CONF_COMPARISON_METHOD,
            ),
        ),
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required("name"): selector.TextSelector(),
    }
).extend(OPTIONS_SCHEMA.schema)


CONFIG_FLOW = {
    "user": SchemaFlowFormStep(CONFIG_SCHEMA),
}

OPTIONS_FLOW = {
    "init": SchemaFlowFormStep(OPTIONS_SCHEMA),
}


class ConfigFlowHandler(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config or options flow for calendar_event."""

    config_flow = CONFIG_FLOW
    options_flow = OPTIONS_FLOW

    VERSION = 1
    MINOR_VERSION = 1

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""
        return cast(str, options["name"]) if "name" in options else ""
