"""The test for the calendar_event binary sensor platform."""

from unittest.mock import patch

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
