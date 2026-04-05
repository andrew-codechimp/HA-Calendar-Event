"""Binary sensor platform for calendar_event."""

from __future__ import annotations

from asyncio import Task, TimerHandle
from datetime import timedelta

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_entity_registry_updated_event
from homeassistant.util import dt as dt_util
from homeassistant.util.dt import utcnow

from .const import (
    ATTR_DESCRIPTION,
    ATTR_LOCATION,
    ATTR_SUMMARY,
    CONF_CALENDAR_ENTITY_ID,
    CONF_COMPARISON_METHOD,
    CONF_MATCH,
    CONF_MATCH_ATTRIBUTE,
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
    match: str = config_entry.options[CONF_MATCH]
    match_attribute: str = config_entry.options.get(CONF_MATCH_ATTRIBUTE, "summary")
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
                match,
                match_attribute,
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

    _unrecorded_attributes = frozenset(
        {
            ATTR_SUMMARY,
            ATTR_DESCRIPTION,
            ATTR_LOCATION,
        }
    )

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        name: str | None,
        unique_id: str | None,
        calendar_entity_id: str,
        match: str,
        match_attribute: str,
        comparison_method: str,
    ) -> None:
        """Initialize the Calendar Event sensor."""
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._calendar_entity_id = calendar_entity_id
        self._match = match
        self._match_attribute = match_attribute
        self._comparison_method = comparison_method
        self._hass = hass
        self._config_entry = config_entry

        self._attr_is_on = False
        self._attr_extra_state_attributes = {}
        self._call_later_handle: TimerHandle | None = None
        self._update_task: Task | None = None

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

        self._schedule_update()

    @callback
    def _entity_registry_updated(self, event: Event) -> None:
        """Handle entity registry update."""
        # Cancel any pending timers and tasks if the entity is disabled
        if not self.enabled:
            self._cancel_call_later()
            self._cancel_update_task()

    def _cancel_call_later(self) -> None:
        """Cancel any pending call_later."""
        if self._call_later_handle is not None:
            self._call_later_handle.cancel()
            self._call_later_handle = None

    def _cancel_update_task(self) -> None:
        """Cancel any in-progress update task."""
        if self._update_task is not None:
            self._update_task.cancel()
            self._update_task = None

    def _schedule_update(self) -> None:
        """Cancel any pending update and schedule a fresh one."""
        self._cancel_call_later()
        self._cancel_update_task()
        self._update_task = self._hass.async_create_task(self._update_state())

    async def async_will_remove_from_hass(self) -> None:
        """Handle entity removal."""
        self._cancel_call_later()
        self._cancel_update_task()
        await super().async_will_remove_from_hass()

    @callback
    def _state_changed(self, event: Event) -> None:
        """Handle calendar entity state changes."""
        if event.data.get("entity_id") == self._calendar_entity_id:
            # Only update state if the entity is enabled
            if self.enabled:
                self._schedule_update()
            else:
                # Cancel any pending timers and tasks if disabled
                self._cancel_call_later()
                self._cancel_update_task()

    async def _update_state(self) -> None:
        """Update the binary sensor state based on calendar events."""

        # Don't update if the entity is disabled
        if not self.enabled:
            self._cancel_call_later()
            return

        calendar_state = self._hass.states.get(self._calendar_entity_id)

        if calendar_state is None or calendar_state.state == "off":
            self._attr_is_on = False
            self._attr_extra_state_attributes.update(
                {
                    ATTR_SUMMARY: "",
                    ATTR_DESCRIPTION: "",
                    ATTR_LOCATION: "",
                }
            )
            self.async_write_ha_state()
            return

        event = await self._get_event_matching_summary()
        if event:
            self._attr_is_on = True
            self._attr_extra_state_attributes.update(
                {
                    ATTR_SUMMARY: event.get("summary", ""),
                    ATTR_DESCRIPTION: event.get("description", ""),
                    ATTR_LOCATION: event.get("location", ""),
                }
            )
        else:
            self._attr_is_on = False
            self._attr_extra_state_attributes.update(
                {
                    ATTR_SUMMARY: "",
                    ATTR_DESCRIPTION: "",
                    ATTR_LOCATION: "",
                }
            )

        self.async_write_ha_state()

        self._cancel_call_later()

        # Re-read calendar state after the await to avoid scheduling based on stale data
        current_calendar_state = self._hass.states.get(self._calendar_entity_id)
        # Schedule next update only if calendar is still on and entity is enabled
        if (
            current_calendar_state is not None
            and current_calendar_state.state == "on"
            and self.enabled
        ):
            now = utcnow()
            seconds_until_next_minute = 60 - now.second
            self._call_later_handle = self._hass.loop.call_later(
                seconds_until_next_minute,
                self._schedule_update,
            )

    def _matches_criteria(self, event_field: str) -> bool:
        """Check if event summary matches the configured criteria."""
        event_field_lower = event_field.casefold()
        match_lower = self._match.casefold()

        if self._comparison_method == "contains":
            return match_lower in event_field_lower
        if self._comparison_method == "starts_with":
            return event_field_lower.startswith(match_lower)
        if self._comparison_method == "ends_with":
            return event_field_lower.endswith(match_lower)
        if self._comparison_method == "exactly":
            return event_field_lower == match_lower
        # Default to contains if unknown criteria
        return match_lower in event_field_lower

    async def _get_event_matching_summary(self) -> dict | None:  # noqa: PLR0911, PLR0912
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
            start = event.get("start")
            if not isinstance(start, str):
                continue
            try:
                start_dt = dt_util.parse_datetime(start)
                if start_dt is None:
                    continue
                start_dt = dt_util.as_utc(start_dt)
            except (ValueError, TypeError):
                continue
            if start_dt <= utcnow():
                summary = event.get("summary")
                description = event.get("description")
                location = event.get("location")

                if self._match_attribute == "any":
                    if any(
                        self._matches_criteria(attr)
                        for attr in [summary, description, location]
                        if isinstance(attr, str)
                    ):
                        return event
                elif (
                    (
                        self._match_attribute == "summary"
                        and isinstance(summary, str)
                        and self._matches_criteria(summary)
                    )
                    or (
                        self._match_attribute == "description"
                        and isinstance(description, str)
                        and self._matches_criteria(description)
                    )
                    or (
                        self._match_attribute == "location"
                        and isinstance(location, str)
                        and self._matches_criteria(location)
                    )
                ):
                    return event
        return None
