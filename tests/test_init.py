"""Test calendar_event setup process."""

from __future__ import annotations

from custom_components.calendar_event.const import (
    CONF_MATCH,
    DOMAIN,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    label_registry as lr,
)

from .const import DEFAULT_NAME


async def test_unload_entry(hass: HomeAssistant, loaded_entry: MockConfigEntry) -> None:
    """Test unload an entry."""

    assert loaded_entry.state is ConfigEntryState.LOADED
    assert await hass.config_entries.async_unload(loaded_entry.entry_id)
    await hass.async_block_till_done()
    assert loaded_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    label_registry: lr.LabelRegistry,
) -> None:
    """Test the setup of the helper PeriodicMinMax."""

    # Source entity device config entry
    source_config_entry = MockConfigEntry()
    source_config_entry.add_to_hass(hass)

    # Device entry of the source entity
    source_device_entry = device_registry.async_get_or_create(
        config_entry_id=source_config_entry.entry_id,
        identifiers={("sensor", "test_source")},
    )

    # Source entity registry
    source_entity = entity_registry.async_get_or_create(
        "calendar",
        "test",
        "source",
        config_entry=source_config_entry,
        device_id=source_device_entry.id,
        suggested_object_id="my_calendar",
    )

    await hass.async_block_till_done()
    assert entity_registry.async_get(source_entity.entity_id) is not None

    # Configure the configuration entry for calendar_event
    calendar_event_config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            "name": DEFAULT_NAME,
            "calendar_entity_id": source_entity.entity_id,
            "match": "Test Event",
            "comparison_method": "contains",
        },
        title=DEFAULT_NAME,
    )
    calendar_event_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(calendar_event_config_entry.entry_id)
    await hass.async_block_till_done()

    # Config entry reload
    await hass.config_entries.async_reload(calendar_event_config_entry.entry_id)
    await hass.async_block_till_done()

    # Remove the config entry
    assert await hass.config_entries.async_remove(calendar_event_config_entry.entry_id)
    await hass.async_block_till_done()


async def test_migrate_entry_summary_to_match(hass: HomeAssistant) -> None:
    """Test migration renames legacy summary option key to match."""
    from custom_components.calendar_event import async_migrate_entry

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        data={},
        options={
            "name": DEFAULT_NAME,
            "calendar_entity_id": "calendar.my_calendar",
            "summary": "Legacy Option Match",
            "comparison_method": "contains",
            "match_attribute": "summary",
        },
        title=DEFAULT_NAME,
    )
    config_entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, config_entry)

    assert config_entry.version == 2
    assert config_entry.options[CONF_MATCH] == "Legacy Option Match"
    assert "summary" not in config_entry.options
    assert config_entry.data == {}
