"""Binary sensor platform for calendar_event."""

from __future__ import annotations

from asyncio import TimerHandle
from datetime import timedelta

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.util.dt import utcnow
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_entity_registry_updated_event
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.components.binary_sensor import BinarySensorEntity

from .const import (
    CONF_SUMMARY,
    ATTR_DESCRIPTION,
    CONF_COMPARISON_METHOD,
    CONF_CALENDAR_ENTITY_ID,
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
    comparison_method: str = config_entry.options.get(
        CONF_COMPARISON_METHOD, "contains"
    )
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
                comparison_method,
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
        comparison_method: str,
    ) -> None:
        """Initialize the Calendar Event sensor."""
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._calendar_entity_id = calendar_entity_id
        self._summary = summary
        self._comparison_method = comparison_method
        self._hass = hass
        self._config_entry = config_entry

        self._attr_is_on = False
        self._attr_extra_state_attributes = {}
        self._call_later_handle: TimerHandle | None = None

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""
        await super().async_added_to_hass()

        # Add state listener for the calendar entity
        self.async_on_remove(
            self._hass.bus.async_listen(EVENT_STATE_CHANGED, self._state_changed)  # type: ignore[arg-type]
        )

        # Track entity registry updates to detect when entity is disabled/enabled
        self.async_on_remove(
            async_track_entity_registry_updated_event(
                self._hass,
                self.entity_id,
                self._entity_registry_updated,  # type: ignore[arg-type]
            )
        )

        await self._update_state()

    @callback
    def _entity_registry_updated(self, event: Event) -> None:
        """Handle entity registry update."""
        # Cancel any pending timers if the entity is disabled
        if not self.enabled:
            self._cancel_call_later()

    def _cancel_call_later(self) -> None:
        """Cancel any pending call_later."""
        if self._call_later_handle is not None:
            self._call_later_handle.cancel()
            self._call_later_handle = None

    async def async_will_remove_from_hass(self) -> None:
        """Handle entity removal."""
        self._cancel_call_later()
        await super().async_will_remove_from_hass()

    @callback
    async def _state_changed(self, event: Event) -> None:
        """Handle calendar entity state changes."""
        if event.data.get("entity_id") == self._calendar_entity_id:
            # Only update state if the entity is enabled
            if self.enabled:
                await self._update_state()
            else:
                # Cancel any pending timers if disabled
                self._cancel_call_later()

    async def _update_state(self) -> None:
        """Update the binary sensor state based on calendar events."""

        # Don't update if the entity is disabled
        if not self.enabled:
            self._cancel_call_later()
            return

        calendar_state = self._hass.states.get(self._calendar_entity_id)

        if calendar_state is None:
            self._attr_is_on = False
            self._attr_extra_state_attributes.update(
                {
                    ATTR_DESCRIPTION: "",
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
                    ATTR_DESCRIPTION: "",
                }
            )

        self.async_write_ha_state()

        self._cancel_call_later()

        # Schedule next update only if calendar is on and entity is enabled
        if calendar_state.state == "on" and self.enabled:
            now = utcnow()
            seconds_until_next_minute = 60 - now.second
            self._call_later_handle = self._hass.loop.call_later(
                seconds_until_next_minute,
                lambda: self._hass.async_create_task(self._update_state()),
            )

    def _matches_criteria(self, event_summary: str) -> bool:
        """Check if event summary matches the configured criteria."""
        event_summary_lower = event_summary.casefold()
        summary_lower = self._summary.casefold()

        if self._comparison_method == "contains":
            return summary_lower in event_summary_lower
        if self._comparison_method == "starts_with":
            return event_summary_lower.startswith(summary_lower)
        if self._comparison_method == "ends_with":
            return event_summary_lower.endswith(summary_lower)
        if self._comparison_method == "exactly":
            return event_summary_lower == summary_lower
        # Default to contains if unknown criteria
        return summary_lower in event_summary_lower

    async def _get_event_matching_summary(self) -> dict | None:
        """Check if the summary is in the calendar events."""

        # Fetch all events for the calendar entity using the get_events service
        now = utcnow()
        end_date_time = (now + timedelta(hours=1)).isoformat()

        try:
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
        except HomeAssistantError:
            # The service call can fail when the calendar is not available
            return None

        if not isinstance(events, dict):
            return None

        calendar_data = events.get(self._calendar_entity_id, {})
        if not isinstance(calendar_data, dict):
            return None

        calendar_events = calendar_data.get("events", [])
        if not isinstance(calendar_events, list):
            return None
        for event in calendar_events:
            if not isinstance(event, dict):
                continue
            summary = event.get("summary", "")
            if isinstance(summary, str) and self._matches_criteria(summary):
                return event

        return None
