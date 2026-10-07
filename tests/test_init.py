"""Tests for calendar_event lifecycle and source registry changes."""

import pytest
from custom_components.calendar_event import async_migrate_entry
from custom_components.calendar_event.const import (
    CONF_CALENDAR_ENTITY_ID,
    CONF_MATCH,
    CONF_MATCH_ATTRIBUTE,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from . import setup_integration
from .const import ENTITY_ID, SOURCE_ENTITY_ID


@pytest.mark.usefixtures("source_calendar")
async def test_setup_and_remove(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test one entity is created, reload preserves its identity, and removal cleans it up."""
    await setup_integration(hass, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.LOADED
    entities = er.async_entries_for_config_entry(
        entity_registry, mock_config_entry.entry_id
    )
    assert len(entities) == 1
    assert entities[0].entity_id == ENTITY_ID
    assert entities[0].unique_id == mock_config_entry.entry_id
    assert await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert entity_registry.async_get(ENTITY_ID).id == entities[0].id
    assert await hass.config_entries.async_remove(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID) is None
    assert entity_registry.async_get(ENTITY_ID) is None
    assert entity_registry.async_get(SOURCE_ENTITY_ID) is not None


@pytest.mark.usefixtures("source_calendar")
async def test_unload(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Test unloading unsubscribes source state listeners."""
    await setup_integration(hass, mock_config_entry)
    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
    previous = hass.states.get(ENTITY_ID)
    assert previous.state == "unavailable"
    hass.states.async_set(SOURCE_ENTITY_ID, "off")
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID) == previous


@pytest.mark.usefixtures("source_calendar")
async def test_source_removed(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test removing a required source removes the helper entry and entity."""
    await setup_integration(hass, mock_config_entry)
    entity_registry.async_remove(SOURCE_ENTITY_ID)
    await hass.async_block_till_done()
    assert hass.config_entries.async_get_entry(mock_config_entry.entry_id) is None
    assert entity_registry.async_get(ENTITY_ID) is None
    assert hass.states.get(ENTITY_ID) is None


@pytest.mark.usefixtures("source_calendar")
async def test_source_renamed(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test renaming a source updates the stored reference and reloads the helper."""
    await setup_integration(hass, mock_config_entry)
    renamed = f"{SOURCE_ENTITY_ID}_renamed"
    entity_registry.async_update_entity(SOURCE_ENTITY_ID, new_entity_id=renamed)
    await hass.async_block_till_done()
    assert (
        er.async_validate_entity_id(
            entity_registry, mock_config_entry.options[CONF_CALENDAR_ENTITY_ID]
        )
        == renamed
    )
    assert mock_config_entry.state is ConfigEntryState.LOADED


async def test_unknown_source_registry_id(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test an unresolved registry ID produces a setup error."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={
            **mock_config_entry.options,
            CONF_CALENDAR_ENTITY_ID: "missing-registry-id",
        },
    )
    assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR


@pytest.mark.usefixtures("source_calendar")
async def test_options_reload(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test saving options reloads the helper with the new settings."""
    await setup_integration(hass, mock_config_entry)
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    options = {
        key: value for key, value in mock_config_entry.options.items() if key != "name"
    }
    options.update({CONF_MATCH: "Changed match"})
    await hass.config_entries.options.async_configure(result["flow_id"], options)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert dict(mock_config_entry.options) == {
        "name": mock_config_entry.title,
        **options,
    }


@pytest.mark.parametrize(
    ("version", "legacy", "match", "expected"),
    [
        pytest.param(1, "Legacy Meeting", None, "Legacy Meeting", id="legacy-summary"),
        pytest.param(
            1, "Old match", "Current match", "Current match", id="existing-match"
        ),
        pytest.param(2, None, "Current match", "Current match", id="current"),
    ],
)
async def test_migrate(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    version: int,
    legacy: str | None,
    match: str | None,
    expected: str,
) -> None:
    """Test migration converts legacy summary and preserves an existing match."""
    mock_config_entry.add_to_hass(hass)
    options = dict(mock_config_entry.options)
    options.pop(CONF_MATCH)
    options.update(
        {
            key: value
            for key, value in {"summary": legacy, CONF_MATCH: match}.items()
            if value is not None
        }
    )
    hass.config_entries.async_update_entry(
        mock_config_entry, version=version, options=options
    )
    assert await async_migrate_entry(hass, mock_config_entry)
    assert mock_config_entry.version == 2
    assert mock_config_entry.options[CONF_MATCH] == expected
    assert mock_config_entry.options[CONF_MATCH_ATTRIBUTE] == "summary"
    assert mock_config_entry.data == {}
