"""Binary sensor platform for calendar_event."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_UNIQUE_ID,
    EVENT_STATE_CHANGED,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
    AddEntitiesCallback,
)
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    ATTR_DESCRIPTION,
    CONF_CALENDAR_ENTITY,
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

    name: str | None = config_entry.data.get("name")
    calendar_entity: str = config_entry.data[CONF_CALENDAR_ENTITY]
    summary: str = config_entry.data[CONF_SUMMARY]
    unique_id = config_entry.entry_id

    config_entry.async_on_unload(
        config_entry.add_update_listener(config_entry_update_listener)
    )

    async_add_entities(
        [
            CalendarEventBinarySensor(
                hass,
                name,
                unique_id,
                calendar_entity,
                summary,
            )
        ]
    )


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the calendar event sensor."""
    name: str | None = config.get(CONF_NAME)
    calendar_entity: str = config[CONF_CALENDAR_ENTITY]
    summary: str = config[CONF_SUMMARY]
    unique_id = config.get(CONF_UNIQUE_ID)

    async_add_entities(
        [
            CalendarEventBinarySensor(
                hass,
                name,
                unique_id,
                calendar_entity,
                summary,
            )
        ]
    )


class CalendarEventBinarySensor(BinarySensorEntity):
    """Representation of a Calendar Event sensor."""

    _attr_icon = "mdi:tag"
    _attr_should_poll = False

    _state_dict: dict[str, str] = {}

    def __init__(
        self,
        hass: HomeAssistant,
        name: str | None,
        unique_id: str | None,
        calendar_entity: str,
        summary: str,
    ) -> None:
        """Initialize the Calendar Event sensor."""
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._calendar_entity = calendar_entity
        self._summary = summary
        self._hass = hass

        self._unit_of_measurement_mismatch = False

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
        if event.data.get("entity_id") == self._calendar_entity:
            await self._update_state()

    async def _update_state(self) -> None:
        """Update the binary sensor state based on calendar events."""
        calendar_state = self._hass.states.get(self._calendar_entity)

        if calendar_state is None:
            self._attr_is_on = False
            self._attr_extra_state_attributes.update(
                {
                    ATTR_DESCRIPTION: None,
                }
            )
            self.async_write_ha_state()
            return

        # Check if the current calendar event's message/summary matches our target summary
        message = str(calendar_state.attributes.get("message", ""))
        description = calendar_state.attributes.get("description", "")

        # Set binary sensor to on if the message matches the configured summary
        self._attr_is_on = self._summary.lower() in message.lower()

        # Update attributes with the description from the calendar entity
        self._attr_extra_state_attributes.update(
            {
                ATTR_DESCRIPTION: description,
            }
        )

        self.async_write_ha_state()
