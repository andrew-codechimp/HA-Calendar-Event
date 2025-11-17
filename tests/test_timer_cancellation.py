"""Test timer cancellation when binary sensor is disabled."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.calendar_event.binary_sensor import CalendarEventBinarySensor

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import RegistryEntry


@pytest.mark.asyncio
async def test_timer_cancelled_when_entity_disabled_directly(
    hass: HomeAssistant,
) -> None:
    """Test that pending timers are cancelled when entity is disabled."""

    # Create a mock config entry
    config_entry = MockConfigEntry(
        domain="calendar_event",
        options={
            "calendar_entity": "calendar.test",
            "summary": "Test",
            "name": "Test",
        },
    )

    # Create the entity
    entity = CalendarEventBinarySensor(
        hass=hass,
        config_entry=config_entry,
        name="Test",
        unique_id="test_id",
        calendar_entity_id="calendar.test",
        summary="Test",
        comparison_method="contains",
    )

    # Create a mock handle for the timer
    mock_handle = MagicMock()
    entity._call_later_handle = mock_handle

    # Mock registry entry as disabled
    mock_registry_entry = MagicMock(spec=RegistryEntry)
    mock_registry_entry.disabled_by = "user"

    with patch.object(entity, "registry_entry", mock_registry_entry):
        # Simulate the entity registry update callback
        mock_event = MagicMock()
        entity._entity_registry_updated(mock_event)

        # Verify the timer was cancelled
        mock_handle.cancel.assert_called_once()
        assert entity._call_later_handle is None


@pytest.mark.asyncio
async def test_timer_not_scheduled_when_disabled(hass: HomeAssistant) -> None:
    """Test that no timers are scheduled when entity is disabled."""

    # Create a mock config entry
    config_entry = MockConfigEntry(
        domain="calendar_event",
        options={
            "calendar_entity": "calendar.test",
            "summary": "Test",
            "name": "Test",
        },
    )

    # Create the entity
    entity = CalendarEventBinarySensor(
        hass=hass,
        config_entry=config_entry,
        name="Test",
        unique_id="test_id",
        calendar_entity_id="calendar.test",
        summary="Test",
        comparison_method="contains",
    )

    # Mock registry entry as disabled
    mock_registry_entry = MagicMock(spec=RegistryEntry)
    mock_registry_entry.disabled_by = "user"

    with (
        patch.object(entity, "registry_entry", mock_registry_entry),
        patch.object(hass.loop, "call_later") as mock_call_later,
    ):
        # Try to update state when disabled
        await entity._update_state()

        # Verify no timer was scheduled
        mock_call_later.assert_not_called()


@pytest.mark.asyncio
async def test_timer_cancelled_in_state_changed_when_disabled(
    hass: HomeAssistant,
) -> None:
    """Test that timers are cancelled in state changed callback when disabled."""

    # Create a mock config entry
    config_entry = MockConfigEntry(
        domain="calendar_event",
        options={
            "calendar_entity": "calendar.test",
            "summary": "Test",
            "name": "Test",
        },
    )

    # Create the entity
    entity = CalendarEventBinarySensor(
        hass=hass,
        config_entry=config_entry,
        name="Test",
        unique_id="test_id",
        calendar_entity_id="calendar.test",
        summary="Test",
        comparison_method="contains",
    )

    # Create a mock handle for the timer
    mock_handle = MagicMock()
    entity._call_later_handle = mock_handle

    # Mock registry entry as disabled
    mock_registry_entry = MagicMock(spec=RegistryEntry)
    mock_registry_entry.disabled_by = "user"

    with patch.object(entity, "registry_entry", mock_registry_entry):
        # Create a mock event for the calendar entity state change
        mock_event = MagicMock()
        mock_event.data = {"entity_id": "calendar.test"}

        # Call the state changed callback
        await entity._state_changed(mock_event)

        # Verify the timer was cancelled
        mock_handle.cancel.assert_called_once()
        assert entity._call_later_handle is None
