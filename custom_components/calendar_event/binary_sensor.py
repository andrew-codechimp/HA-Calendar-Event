"""Binary sensor platform for calendar_event."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    ATTR_DESCRIPTION,
    CONF_CALENDAR_ENTITY_ID,
    CONF_SUMMARY,
)


async def config_entry_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener, called when the config entry options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Initialize Calendar Event config entry."""

    name: str | None = config_entry.options.get("name")
    calendar_entity: str = config_entry.options[CONF_CALENDAR_ENTITY_ID]
    summary: str = config_entry.options[CONF_SUMMARY]
    unique_id = config_entry.entry_id

    config_entry.async_on_unload(
        config_entry.add_update_listener(config_entry_update_listener)
    )

    async_add_entities(
        [
            CalendarEventBinarySensor(
                hass,
                config_entry,
                name,
                unique_id,
                calendar_entity,
                summary,
            )
        ]
    )


class CalendarEventBinarySensor(BinarySensorEntity):
    """Representation of a Calendar Event sensor."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_translation_key = "calendar_event"

    _state_dict: dict[str, str] = {}

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        name: str | None,
        unique_id: str | None,
        calendar_entity_id: str,
        summary: str,
    ) -> None:
        """Initialize the Calendar Event sensor."""
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._calendar_entity_id = calendar_entity_id
        self._summary = summary
        self._hass = hass
        self._config_entry = config_entry

        self._attr_is_on = False
        self._attr_extra_state_attributes = {}

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""
        await super().async_added_to_hass()

        # Add state listener for the calendar entity
        self.async_on_remove(
            self._hass.bus.async_listen(
                EVENT_STATE_CHANGED, self._calendar_state_changed
            )
        )

        # Check initial state
        await self._update_state()

    @callback
    async def _calendar_state_changed(self, event: Event) -> None:
        """Handle calendar entity state changes."""
        if event.data.get("entity_id") == self._calendar_entity_id:
            await self._update_state()

    async def _update_state(self) -> None:
        """Update the binary sensor state based on calendar events."""

        calendar_state = self._hass.states.get(self._calendar_entity_id)

        if calendar_state is None:
            self._attr_is_on = False
            self._attr_extra_state_attributes.update(
                {
                    ATTR_DESCRIPTION: None,
                }
            )
            self.async_write_ha_state()
            return

        # Fetch all events for the calendar entity using the get_events service
        now = datetime.now()
        end_date_time = (now + timedelta(hours=1)).isoformat()

        events = await self._hass.services.async_call(
            "calendar",
            "get_events",
            {
                "entity_id": self._calendar_entity_id,
                "end_date_time": end_date_time,
            },
            blocking=True,
            return_response=True,
        )

        print(events)

        # {
        #     "calendar.system": {
        #         "events": [
        #             {
        #                 "start": "2025-08-06T17:00:00+01:00",
        #                 "end": "2025-08-06T23:00:00+01:00",
        #                 "summary": "Evening",
        #                 "description": "It's evening",
        #             }
        #         ]
        #     }
        # }

        # TODO: This will be on if there's an existing event, so we don't get a new event
        # need to create a polling mechanism to check for new events

        calendar_events = events.get(self._calendar_entity_id, {}).get("events", [])
        for event in calendar_events:
            # Check if the event summary matches the configured summary (case-insensitive, partial match)
            if not isinstance(event, dict):
                continue
            if self._summary.lower() in event.get("summary", "").lower():
                self._attr_is_on = True
                self._attr_extra_state_attributes.update(
                    {
                        ATTR_DESCRIPTION: event.get("description", ""),
                    }
                )
                break
            else:
                self._attr_is_on = False
                self._attr_extra_state_attributes.update(
                    {
                        ATTR_DESCRIPTION: None,
                    }
                )

        self.async_write_ha_state()
