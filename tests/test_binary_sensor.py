"""The test for the calendar_event binary sensor platform."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.calendar_event.const import (
    ATTR_DESCRIPTION,
    CONF_CALENDAR_ENTITY_ID,
    CONF_COMPARISON_METHOD,
    CONF_SUMMARY,
    DOMAIN,
)

from . import setup_integration


@pytest.fixture
async def mock_calendar_entity(hass: HomeAssistant, entity_registry: er.EntityRegistry):
    """Create a mock calendar entity."""
    calendar_entity = entity_registry.async_get_or_create(
        "calendar",
        "test",
        "calendar_1",
        suggested_object_id="test_calendar",
    )

    # Set initial state
    hass.states.async_set(
        calendar_entity.entity_id,
        "off",
        {"message": "", "description": ""},
    )

    await hass.async_block_till_done()
    return calendar_entity


@pytest.mark.parametrize(
    (
        "comparison_method",
        "summary_text",
        "event_summary",
        "expected_match",
    ),
    [
        # Contains tests
        ("contains", "meeting", "Team Meeting", True),
        ("contains", "meeting", "Daily Standup", False),
        ("contains", "doctor", "Doctors Appointment", True),
        ("contains", "vacation", "Back from vacation", True),
        ("contains", "party", "Birthday celebration", False),
        # Starts with tests
        ("starts_with", "meeting", "Meeting with client", True),
        ("starts_with", "meeting", "Team Meeting", False),
        ("starts_with", "doctor", "Doctors visit", True),
        ("starts_with", "appointment", "Doctor Appointment", False),
        # Ends with tests
        ("ends_with", "meeting", "Daily Meeting", True),
        ("ends_with", "meeting", "Meeting with boss", False),
        ("ends_with", "appointment", "Doctor Appointment", True),
        ("ends_with", "visit", "Doctor visit", True),
        # Exactly tests
        ("exactly", "meeting", "Meeting", True),
        ("exactly", "meeting", "Team Meeting", False),
        ("exactly", "doctor appointment", "Doctor Appointment", True),
        ("exactly", "vacation", "Vacation time", False),
    ],
)
async def test_binary_sensor_matching_criteria(
    hass: HomeAssistant,
    mock_calendar_entity: er.RegistryEntry,
    comparison_method: str,
    summary_text: str,
    event_summary: str,
    expected_match: bool,
) -> None:
    """Test binary sensor with different matching criteria."""

    # Create config entry
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            "name": f"Test {comparison_method}",
            CONF_CALENDAR_ENTITY_ID: mock_calendar_entity.entity_id,
            CONF_SUMMARY: summary_text,
            CONF_COMPARISON_METHOD: comparison_method,
        },
        title=f"Test {comparison_method}",
    )

    with patch(
        "custom_components.calendar_event.binary_sensor.CalendarEventBinarySensor._get_event_matching_summary"
    ) as mock_get_events:
        if expected_match:
            mock_get_events.return_value = {
                "summary": event_summary,
                "description": "Test event description",
            }
        else:
            mock_get_events.return_value = None

        await setup_integration(hass, config_entry)

        # Get the binary sensor entity - normalize the name for entity ID
        entity_name = f"Test {comparison_method}".lower().replace(" ", "_")
        binary_sensor_entity_id = f"binary_sensor.{entity_name}"

        # Set calendar to active state to trigger event checking
        hass.states.async_set(
            mock_calendar_entity.entity_id,
            "on",
            {"message": event_summary, "description": "Test description"},
        )
        await hass.async_block_till_done()

        # Check binary sensor state
        binary_sensor_state = hass.states.get(binary_sensor_entity_id)
        assert binary_sensor_state is not None

        if expected_match:
            assert binary_sensor_state.state == "on"
            assert (
                binary_sensor_state.attributes.get(ATTR_DESCRIPTION)
                == "Test event description"
            )
        else:
            assert binary_sensor_state.state == "off"
            assert binary_sensor_state.attributes.get(ATTR_DESCRIPTION) == ""


async def test_binary_sensor_no_events(
    hass: HomeAssistant,
    mock_calendar_entity: er.RegistryEntry,
) -> None:
    """Test binary sensor when no events are found."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            "name": "Test No Events",
            CONF_CALENDAR_ENTITY_ID: mock_calendar_entity.entity_id,
            CONF_SUMMARY: "meeting",
            CONF_COMPARISON_METHOD: "contains",
        },
        title="Test No Events",
    )

    with patch(
        "custom_components.calendar_event.binary_sensor.CalendarEventBinarySensor._get_event_matching_summary"
    ) as mock_get_events:
        mock_get_events.return_value = None

        await setup_integration(hass, config_entry)

        binary_sensor_entity_id = "binary_sensor.test_no_events"

        # Set calendar to active state
        hass.states.async_set(
            mock_calendar_entity.entity_id,
            "on",
            {"message": "", "description": ""},
        )
        await hass.async_block_till_done()

        # Check binary sensor state
        binary_sensor_state = hass.states.get(binary_sensor_entity_id)
        assert binary_sensor_state is not None
        assert binary_sensor_state.state == "off"
        assert binary_sensor_state.attributes.get(ATTR_DESCRIPTION) == ""


async def test_binary_sensor_calendar_unavailable(
    hass: HomeAssistant,
    mock_calendar_entity: er.RegistryEntry,
) -> None:
    """Test binary sensor when calendar entity is unavailable."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            "name": "Test Unavailable",
            CONF_CALENDAR_ENTITY_ID: mock_calendar_entity.entity_id,
            CONF_SUMMARY: "meeting",
            CONF_COMPARISON_METHOD: "contains",
        },
        title="Test Unavailable",
    )

    with patch(
        "custom_components.calendar_event.binary_sensor.CalendarEventBinarySensor._get_event_matching_summary"
    ) as mock_get_events:
        mock_get_events.return_value = None

        await setup_integration(hass, config_entry)

        binary_sensor_entity_id = "binary_sensor.test_unavailable"

        # Set calendar to unavailable (remove it from the state registry)
        hass.states.async_remove(mock_calendar_entity.entity_id)
        await hass.async_block_till_done()

        # Check binary sensor state
        binary_sensor_state = hass.states.get(binary_sensor_entity_id)
        assert binary_sensor_state is not None
        assert binary_sensor_state.state == "off"
        assert binary_sensor_state.attributes.get(ATTR_DESCRIPTION) == ""


async def test_binary_sensor_state_change_listener(
    hass: HomeAssistant,
    mock_calendar_entity: er.RegistryEntry,
) -> None:
    """Test that binary sensor responds to calendar state changes."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            "name": "Test State Change",
            CONF_CALENDAR_ENTITY_ID: mock_calendar_entity.entity_id,
            CONF_SUMMARY: "meeting",
            CONF_COMPARISON_METHOD: "contains",
        },
        title="Test State Change",
    )

    with patch(
        "custom_components.calendar_event.binary_sensor.CalendarEventBinarySensor._get_event_matching_summary"
    ) as mock_get_events:
        # Initially no events
        mock_get_events.return_value = None

        await setup_integration(hass, config_entry)

        binary_sensor_entity_id = "binary_sensor.test_state_change"

        # Initially calendar is off
        binary_sensor_state = hass.states.get(binary_sensor_entity_id)
        assert binary_sensor_state.state == "off"

        # Now mock finding a matching event
        mock_get_events.return_value = {
            "summary": "Team Meeting",
            "description": "Weekly team sync",
        }

        # Change calendar to active state
        hass.states.async_set(
            mock_calendar_entity.entity_id,
            "on",
            {"message": "Team Meeting", "description": "Weekly team sync"},
        )
        await hass.async_block_till_done()

        # Check binary sensor is now on
        binary_sensor_state = hass.states.get(binary_sensor_entity_id)
        assert binary_sensor_state.state == "on"
        assert (
            binary_sensor_state.attributes.get(ATTR_DESCRIPTION) == "Weekly team sync"
        )

        # Mock no events again
        mock_get_events.return_value = None

        # Change calendar back to off
        hass.states.async_set(
            mock_calendar_entity.entity_id,
            "off",
            {"message": "", "description": ""},
        )
        await hass.async_block_till_done()

        # Check binary sensor is now off
        binary_sensor_state = hass.states.get(binary_sensor_entity_id)
        assert binary_sensor_state.state == "off"


async def test_binary_sensor_default_comparison_method(
    hass: HomeAssistant,
    mock_calendar_entity: er.RegistryEntry,
) -> None:
    """Test that default comparison method is 'contains'."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            "name": "Test Default",
            CONF_CALENDAR_ENTITY_ID: mock_calendar_entity.entity_id,
            CONF_SUMMARY: "meeting",
            # No CONF_COMPARISON_METHOD specified
        },
        title="Test Default",
    )

    with patch(
        "custom_components.calendar_event.binary_sensor.CalendarEventBinarySensor._get_event_matching_summary"
    ) as mock_get_events:
        mock_get_events.return_value = {
            "summary": "Team Meeting",
            "description": "Default test",
        }

        await setup_integration(hass, config_entry)

        binary_sensor_entity_id = "binary_sensor.test_default"

        # Set calendar to active state
        hass.states.async_set(
            mock_calendar_entity.entity_id,
            "on",
            {"message": "Team Meeting", "description": "Default test"},
        )
        await hass.async_block_till_done()

        # Check binary sensor matches with default 'contains' logic
        binary_sensor_state = hass.states.get(binary_sensor_entity_id)
        assert binary_sensor_state is not None
        assert binary_sensor_state.state == "on"
        assert binary_sensor_state.attributes.get(ATTR_DESCRIPTION) == "Default test"


# Test the actual matching logic directly
@pytest.mark.parametrize(
    (
        "comparison_method",
        "summary_text",
        "event_summary",
        "expected_match",
    ),
    [
        # Contains tests
        ("contains", "meeting", "Team Meeting", True),
        ("contains", "MEET", "team meeting", True),  # Case insensitive
        ("contains", "meeting", "Daily Standup", False),
        # Starts with tests
        ("starts_with", "meeting", "Meeting with client", True),
        ("starts_with", "MEETING", "meeting with client", True),  # Case insensitive
        ("starts_with", "meeting", "Team Meeting", False),
        # Ends with tests
        ("ends_with", "meeting", "Daily Meeting", True),
        ("ends_with", "MEETING", "daily meeting", True),  # Case insensitive
        ("ends_with", "meeting", "Meeting with boss", False),
        # Exactly tests
        ("exactly", "meeting", "Meeting", True),
        ("exactly", "MEETING", "meeting", True),  # Case insensitive
        ("exactly", "meeting", "Team Meeting", False),
    ],
)
def test_matches_criteria_logic(
    comparison_method: str,
    summary_text: str,
    event_summary: str,
    expected_match: bool,
) -> None:
    """Test the matching criteria logic directly."""
    from custom_components.calendar_event.binary_sensor import CalendarEventBinarySensor

    # Create a mock sensor to test the matching logic
    sensor = CalendarEventBinarySensor(
        hass=None,
        config_entry=None,
        name="Test",
        unique_id="test",
        calendar_entity_id="calendar.test",
        summary=summary_text,
        comparison_method=comparison_method,
    )

    result = sensor._matches_criteria(event_summary)
    assert result == expected_match


async def test_binary_sensor_disabled_no_call_later(
    hass: HomeAssistant,
    mock_calendar_entity: er.RegistryEntry,
) -> None:
    """Test that disabled binary sensor does not schedule periodic updates."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            "name": "Test Disabled",
            CONF_CALENDAR_ENTITY_ID: mock_calendar_entity.entity_id,
            CONF_SUMMARY: "meeting",
            CONF_COMPARISON_METHOD: "contains",
        },
        title="Test Disabled",
    )

    with patch(
        "custom_components.calendar_event.binary_sensor.CalendarEventBinarySensor._get_event_matching_summary"
    ) as mock_get_events:
        mock_get_events.return_value = {
            "summary": "Team Meeting",
            "description": "Test event description",
        }

        # Mock the call_later method to track if it's called
        with patch.object(hass.loop, "call_later") as mock_call_later:
            await setup_integration(hass, config_entry)

            binary_sensor_entity_id = "binary_sensor.test_disabled"

            # Get the binary sensor entity from the entity registry and disable it
            entity_registry = er.async_get(hass)
            entity_entry = entity_registry.async_get(binary_sensor_entity_id)
            assert entity_entry is not None

            # Disable the entity
            entity_registry.async_update_entity(
                entity_entry.entity_id, disabled_by=er.RegistryEntryDisabler.USER
            )
            await hass.async_block_till_done()

            # Reset the mock to clear any previous calls
            mock_call_later.reset_mock()

            # Set calendar to active state to trigger potential call_later
            hass.states.async_set(
                mock_calendar_entity.entity_id,
                "on",
                {"message": "Team Meeting", "description": "Test description"},
            )
            await hass.async_block_till_done()

            # Verify that call_later was NOT called for the disabled entity
            mock_call_later.assert_not_called()


async def test_binary_sensor_enabled_schedules_call_later(
    hass: HomeAssistant,
    mock_calendar_entity: er.RegistryEntry,
) -> None:
    """Test that enabled binary sensor schedules periodic updates when calendar is on."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            "name": "Test Enabled",
            CONF_CALENDAR_ENTITY_ID: mock_calendar_entity.entity_id,
            CONF_SUMMARY: "meeting",
            CONF_COMPARISON_METHOD: "contains",
        },
        title="Test Enabled",
    )

    with patch(
        "custom_components.calendar_event.binary_sensor.CalendarEventBinarySensor._get_event_matching_summary"
    ) as mock_get_events:
        mock_get_events.return_value = {
            "summary": "Team Meeting",
            "description": "Test event description",
        }

        # Mock the call_later method to track if it's called
        with patch.object(hass.loop, "call_later") as mock_call_later:
            await setup_integration(hass, config_entry)

            binary_sensor_entity_id = "binary_sensor.test_enabled"

            # Verify the entity is enabled by default
            entity_registry = er.async_get(hass)
            entity_entry = entity_registry.async_get(binary_sensor_entity_id)
            assert entity_entry is not None
            assert not entity_entry.disabled

            # Reset the mock to clear any previous calls
            mock_call_later.reset_mock()

            # Set calendar to active state to trigger call_later
            hass.states.async_set(
                mock_calendar_entity.entity_id,
                "on",
                {"message": "Team Meeting", "description": "Test description"},
            )
            await hass.async_block_till_done()

            # Verify that call_later WAS called for the enabled entity
            mock_call_later.assert_called_once()

            # Verify the call_later was scheduled with correct parameters
            call_args = mock_call_later.call_args
            assert len(call_args[0]) == 2  # delay and callback
            delay = call_args[0][0]
            assert isinstance(delay, (int, float))
            assert 0 < delay <= 60  # Should be between 0 and 60 seconds


async def test_binary_sensor_cancels_call_later_when_disabled(
    hass: HomeAssistant,
    mock_calendar_entity: er.RegistryEntry,
) -> None:
    """Test that binary sensor cancels call_later when entity is disabled during runtime."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            "name": "Test Cancel",
            CONF_CALENDAR_ENTITY_ID: mock_calendar_entity.entity_id,
            CONF_SUMMARY: "meeting",
            CONF_COMPARISON_METHOD: "contains",
        },
        title="Test Cancel",
    )

    with patch(
        "custom_components.calendar_event.binary_sensor.CalendarEventBinarySensor._get_event_matching_summary"
    ) as mock_get_events:
        mock_get_events.return_value = {
            "summary": "Team Meeting",
            "description": "Test event description",
        }

        await setup_integration(hass, config_entry)

        binary_sensor_entity_id = "binary_sensor.test_cancel"

        # Get the entity registry
        entity_registry = er.async_get(hass)
        entity_entry = entity_registry.async_get(binary_sensor_entity_id)
        assert entity_entry is not None

        # Create a mock handle to track cancellation
        mock_handle = MagicMock()

        with patch.object(
            hass.loop, "call_later", return_value=mock_handle
        ) as mock_call_later:
            # Set calendar to active state to trigger call_later
            hass.states.async_set(
                mock_calendar_entity.entity_id,
                "on",
                {"message": "Team Meeting", "description": "Test description"},
            )
            await hass.async_block_till_done()

            # Verify call_later was called and handle was stored
            mock_call_later.assert_called_once()

            # Reset mock to clear call
            mock_call_later.reset_mock()

            # Now disable the entity
            entity_registry.async_update_entity(
                entity_entry.entity_id, disabled_by=er.RegistryEntryDisabler.USER
            )
            await hass.async_block_till_done()

            # Trigger another calendar state change
            hass.states.async_set(
                mock_calendar_entity.entity_id,
                "on",
                {"message": "Another Meeting", "description": "Test description 2"},
            )
            await hass.async_block_till_done()

            # Verify the previous handle was cancelled and no new call_later was scheduled
            mock_handle.cancel.assert_called_once()
            mock_call_later.assert_not_called()
