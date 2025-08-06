"""Binary sensor platform for calendar_event."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import (
    EventStateChangedData,
    EventStateReportedData,
    async_track_entity_registry_updated_event,
    async_track_state_change_event,
    async_track_state_report_event,
)

from .const import ATTR_DESCRIPTION, CONF_CALENDAR_ENTITY_ID, CONF_SUMMARY, LOGGER


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
            self._hass.bus.async_listen(EVENT_STATE_CHANGED, self._state_changed)
        )

        await self._update_state()

    @callback
    async def _state_changed(self, event: Event) -> None:
        """Handle calendar entity state changes."""
        if event.data.get("entity_id") == self._calendar_entity_id:
            print(event)
            await self._update_state()

    async def _update_state(self) -> None:
        """Update the binary sensor state based on calendar events."""

        calendar_state = self._hass.states.get(self._calendar_entity_id)

        print(calendar_state)

        if calendar_state is None:
            self._attr_is_on = False
            self._attr_extra_state_attributes.update(
                {
                    ATTR_DESCRIPTION: None,
                }
            )
            self.async_write_ha_state()
            return

        event = await self._get_event_matching_summary()
        if event:
            self._attr_is_on = True
            self._attr_extra_state_attributes.update(
                {
                    ATTR_DESCRIPTION: event.get("description", ""),
                }
            )
        else:
            self._attr_is_on = False
            self._attr_extra_state_attributes.update(
                {
                    ATTR_DESCRIPTION: None,
                }
            )

        self.async_write_ha_state()

        # TODO: If state is on, then we need to check every minute in case our event is not the one that turned it on
        if calendar_state.state == "on":
            now = datetime.now()
            seconds_until_next_minute = 60 - now.second
            self._hass.loop.call_later(
                seconds_until_next_minute,
                lambda: self._hass.async_create_task(self._update_state()),
            )

    async def _get_event_matching_summary(self) -> Event | None:
        """Check if the summary is in the calendar events."""

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

        calendar_events = events.get(self._calendar_entity_id, {}).get("events", [])
        for event in calendar_events:
            if not isinstance(event, dict):
                continue
            if self._summary.lower() in event.get("summary", "").lower():
                return event

        return None
