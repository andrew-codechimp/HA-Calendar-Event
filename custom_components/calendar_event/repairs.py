"""Repairs for calendar_event integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import voluptuous as vol
from homeassistant import data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector
from homeassistant.helpers.issue_registry import async_delete_issue

from .const import CONF_CALENDAR_ENTITY_ID, DOMAIN, ISSUE_MISSING_CALENDAR_ENTITY

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry


class CalendarEntityMissingRepairFlow(RepairsFlow):
    """Handler for calendar entity missing repair flow."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the repair flow."""
        super().__init__()
        self.entry = entry

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the confirm step of the repair flow."""
        if user_input is not None:
            # Update the config entry with the new calendar entity
            new_options = {**self.entry.options}
            new_options[CONF_CALENDAR_ENTITY_ID] = user_input[CONF_CALENDAR_ENTITY_ID]
            
            self.hass.config_entries.async_update_entry(
                self.entry, options=new_options
            )
            
            # Clean up the repair issue since it's now fixed
            async_delete_issue(
                self.hass, DOMAIN, f"{ISSUE_MISSING_CALENDAR_ENTITY}_{self.entry.entry_id}"
            )
            
            return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({
                vol.Required(CONF_CALENDAR_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="calendar")
                ),
            }),
            description_placeholders={
                "calendar_entity": self.entry.options[CONF_CALENDAR_ENTITY_ID],
                "entry_title": self.entry.title or "Calendar Event",
            },
        )


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create flow."""
    if data and (entry_id := data.get("entry_id")):
        entry_id = cast(str, entry_id)
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry:
            return CalendarEntityMissingRepairFlow(entry)

    # Fallback to a basic confirm flow if entry not found
    from homeassistant.components.repairs.issue_handler import ConfirmRepairFlow

    return ConfirmRepairFlow()
