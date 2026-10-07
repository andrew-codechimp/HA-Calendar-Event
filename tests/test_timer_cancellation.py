"""Tests for calendar polling cancellation and disabled entities."""

import asyncio
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from custom_components.calendar_event.binary_sensor import CalendarEventBinarySensor
from custom_components.calendar_event.const import DOMAIN
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import Event, HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er

from . import setup_integration
from .const import DEFAULT_NAME, ENTITY_ID, SOURCE_ENTITY_ID


@pytest.fixture
def disabled_sensor(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> Generator[CalendarEventBinarySensor]:
    """Construct a sensor with a real disabled entity registry entry."""
    entry = entity_registry.async_get_or_create(
        "binary_sensor",
        DOMAIN,
        "disabled-test",
        suggested_object_id="disabled_test",
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    sensor = CalendarEventBinarySensor(
        hass,
        mock_config_entry,
        DEFAULT_NAME,
        entry.unique_id,
        SOURCE_ENTITY_ID,
        "Meeting",
        "summary",
        "contains",
    )
    with patch.object(sensor, "registry_entry", entry):
        yield sensor


async def test_disabled_update(
    hass: HomeAssistant, disabled_sensor: CalendarEventBinarySensor
) -> None:
    """Test a disabled update cancels its pending timer without fetching events."""
    timer = hass.loop.call_later(60, lambda: None)
    disabled_sensor._call_later_handle = timer
    with patch("homeassistant.core.ServiceRegistry.async_call") as service:
        await disabled_sensor._update_state()
    service.assert_not_awaited()
    assert timer.cancelled()
    assert disabled_sensor._call_later_handle is None


@pytest.mark.parametrize("callback", ["_entity_registry_updated", "_state_changed"])
async def test_disabled_callbacks(
    hass: HomeAssistant, disabled_sensor: CalendarEventBinarySensor, callback: str
) -> None:
    """Test disabled callbacks cancel both a timer and an in-flight event request."""
    timer = hass.loop.call_later(60, lambda: None)
    gate = asyncio.Event()
    task = hass.async_create_task(gate.wait())
    disabled_sensor._call_later_handle = timer
    disabled_sensor._update_task = task
    getattr(disabled_sensor, callback)(
        Event(EVENT_STATE_CHANGED, {"entity_id": SOURCE_ENTITY_ID})
    )
    with pytest.raises(asyncio.CancelledError):
        await task
    assert timer.cancelled()
    assert disabled_sensor._call_later_handle is None
    assert disabled_sensor._update_task is None


@pytest.mark.usefixtures("source_calendar")
async def test_unload_cancels_polling(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_get_events: AsyncMock
) -> None:
    """Test unloading cancels the active polling timer."""
    hass.states.async_set(SOURCE_ENTITY_ID, "on")
    await setup_integration(hass, mock_config_entry)
    sensor = hass.data["binary_sensor"].get_entity(ENTITY_ID)
    timer = sensor._call_later_handle
    assert timer is not None
    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert timer.cancelled()
    assert sensor._call_later_handle is None
    assert sensor._update_task is None


@pytest.mark.usefixtures("source_calendar")
async def test_calendar_changes_during_request(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_get_events: AsyncMock
) -> None:
    """Test polling is not rescheduled from a calendar state that changed during a request."""

    async def stop_calendar(call: ServiceCall) -> dict[str, dict[str, list[object]]]:
        hass.states.async_set(SOURCE_ENTITY_ID, "off")
        return {SOURCE_ENTITY_ID: {"events": []}}

    mock_get_events.side_effect = stop_calendar
    hass.states.async_set(SOURCE_ENTITY_ID, "on")
    await setup_integration(hass, mock_config_entry)
    sensor = hass.data["binary_sensor"].get_entity(ENTITY_ID)
    assert sensor._call_later_handle is None
    assert hass.states.get(ENTITY_ID).state == "off"
