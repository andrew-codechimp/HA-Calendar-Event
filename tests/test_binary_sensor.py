"""Tests for event matching, malformed responses, and calendar updates."""

from unittest.mock import AsyncMock, patch

import pytest
from custom_components.calendar_event.const import (
    ATTR_DESCRIPTION,
    ATTR_LOCATION,
    ATTR_SUMMARY,
    CONF_COMPARISON_METHOD,
    CONF_MATCH_ATTRIBUTE,
)
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from . import advance_time, setup_integration
from .const import ENTITY_ID, SOURCE_ENTITY_ID

pytestmark = pytest.mark.usefixtures("source_calendar")

EVENT = {
    "start": "2026-07-01T11:00:00+00:00",
    "summary": "Team Meeting",
    "description": "Weekly planning",
    "location": "Office",
}


async def test_entity(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test entity metadata and initial empty event attributes."""
    await setup_integration(hass, mock_config_entry)
    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize(
    ("method", "summary", "expected"),
    [
        pytest.param("contains", "Team MEETING", "on", id="contains-casefold"),
        pytest.param("contains", "Appointment", "off", id="contains-miss"),
        pytest.param("starts_with", "Meeting at noon", "on", id="prefix"),
        pytest.param("starts_with", "Team Meeting", "off", id="prefix-miss"),
        pytest.param("ends_with", "Team meeting", "on", id="suffix"),
        pytest.param("ends_with", "Meeting at noon", "off", id="suffix-miss"),
        pytest.param("exactly", "MEETING", "on", id="exact"),
        pytest.param("exactly", "Team Meeting", "off", id="exact-miss"),
        pytest.param("unexpected", "Team Meeting", "on", id="legacy-fallback"),
    ],
)
async def test_matching_methods(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_get_events: AsyncMock,
    method: str,
    summary: str,
    expected: str,
) -> None:
    """Test case-insensitive matching and the fallback for a legacy method."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={**mock_config_entry.options, CONF_COMPARISON_METHOD: method},
    )
    mock_get_events.return_value = {
        SOURCE_ENTITY_ID: {"events": [{**EVENT, "summary": summary}]}
    }
    hass.states.async_set(SOURCE_ENTITY_ID, "on")
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == expected
    call = mock_get_events.call_args.args[0]
    assert call.data == {
        "entity_id": SOURCE_ENTITY_ID,
        "end_date_time": "2026-07-01T13:00:00+00:00",
    }


@pytest.mark.parametrize(
    ("mock_config_entry", "event", "expected"),
    [
        pytest.param({CONF_MATCH_ATTRIBUTE: "summary"}, EVENT, "on", id="summary"),
        pytest.param(
            {CONF_MATCH_ATTRIBUTE: "description"},
            {**EVENT, "description": "Meeting notes"},
            "on",
            id="description",
        ),
        pytest.param(
            {CONF_MATCH_ATTRIBUTE: "location"},
            {**EVENT, "location": "Meeting room"},
            "on",
            id="location",
        ),
        pytest.param(
            {CONF_MATCH_ATTRIBUTE: "any"},
            {**EVENT, "summary": None, "description": "Meeting notes"},
            "on",
            id="any-description",
        ),
        pytest.param(
            {CONF_MATCH_ATTRIBUTE: "any"},
            {**EVENT, "summary": "Appointment", "location": "Meeting room"},
            "on",
            id="any-location",
        ),
        pytest.param(
            {CONF_MATCH_ATTRIBUTE: "any"},
            {"start": EVENT["start"], "summary": None},
            "off",
            id="no-text",
        ),
        pytest.param(
            {}, {**EVENT, "start": "2026-07-01T12:01:00+00:00"}, "off", id="future"
        ),
        pytest.param(
            {}, {**EVENT, "start": "2026-07-01T12:00:00+00:00"}, "on", id="starts-now"
        ),
        pytest.param(
            {},
            {"start": EVENT["start"], "summary": "Meeting"},
            "on",
            id="missing-optional-fields",
        ),
    ],
    indirect=["mock_config_entry"],
)
async def test_event_fields(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_get_events: AsyncMock,
    event: dict[str, str | None],
    expected: str,
) -> None:
    """Test all matching fields, event start times, and missing optional fields."""
    mock_get_events.return_value = {SOURCE_ENTITY_ID: {"events": [event]}}
    hass.states.async_set(SOURCE_ENTITY_ID, "on")
    await setup_integration(hass, mock_config_entry)
    assert hass.states.get(ENTITY_ID).state == expected


@pytest.mark.parametrize(
    "response",
    [
        pytest.param(None, id="none"),
        pytest.param([], id="not-a-dict"),
        pytest.param({}, id="calendar-missing"),
        pytest.param({SOURCE_ENTITY_ID: []}, id="invalid-calendar-data"),
        pytest.param({SOURCE_ENTITY_ID: {"events": {}}}, id="invalid-event-list"),
        pytest.param({SOURCE_ENTITY_ID: {"events": []}}, id="empty"),
        pytest.param(
            {
                SOURCE_ENTITY_ID: {
                    "events": [None, {}, {"start": 42}, {"start": "invalid"}]
                }
            },
            id="invalid-events",
        ),
    ],
)
async def test_malformed_responses(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, response: object
) -> None:
    """Test malformed external action responses leave the helper off."""
    hass.states.async_set(SOURCE_ENTITY_ID, "on")
    with patch("homeassistant.core.ServiceRegistry.async_call", return_value=response):
        await setup_integration(hass, mock_config_entry)
    state = hass.states.get(ENTITY_ID)
    assert state.state == "off"
    assert state.attributes[ATTR_SUMMARY] == ""
    assert state.attributes[ATTR_DESCRIPTION] == ""
    assert state.attributes[ATTR_LOCATION] == ""


async def test_service_error(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_get_events: AsyncMock
) -> None:
    """Test a calendar action failure clears the helper and recovers on a later update."""
    mock_get_events.side_effect = HomeAssistantError("Calendar unavailable")
    hass.states.async_set(SOURCE_ENTITY_ID, "on")
    await setup_integration(hass, mock_config_entry)
    assert hass.states.get(ENTITY_ID).state == "off"
    mock_get_events.side_effect = None
    mock_get_events.return_value = {SOURCE_ENTITY_ID: {"events": [EVENT]}}
    hass.states.async_set(SOURCE_ENTITY_ID, "on", {"report": 1})
    await hass.async_block_till_done()
    state = hass.states.get(ENTITY_ID)
    assert state.state == "on"
    assert state.attributes[ATTR_SUMMARY] == EVENT["summary"]
    assert state.attributes[ATTR_DESCRIPTION] == EVENT["description"]
    assert state.attributes[ATTR_LOCATION] == EVENT["location"]


async def test_calendar_off_and_missing(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_get_events: AsyncMock
) -> None:
    """Test stopping and removing an active calendar clears attributes and skips fetching."""
    mock_get_events.return_value = {SOURCE_ENTITY_ID: {"events": [EVENT]}}
    hass.states.async_set(SOURCE_ENTITY_ID, "on")
    await setup_integration(hass, mock_config_entry)
    assert hass.states.get(ENTITY_ID).state == "on"
    mock_get_events.reset_mock()
    hass.states.async_set(SOURCE_ENTITY_ID, "off")
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == "off"
    assert hass.states.get(ENTITY_ID).attributes[ATTR_SUMMARY] == ""
    hass.states.async_remove(SOURCE_ENTITY_ID)
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == "off"
    mock_get_events.assert_not_awaited()


async def test_minute_updates(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_get_events: AsyncMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test active calendars are rechecked at the next minute without a source change."""
    hass.states.async_set(SOURCE_ENTITY_ID, "on")
    await setup_integration(hass, mock_config_entry)
    assert hass.states.get(ENTITY_ID).state == "off"
    mock_get_events.return_value = {SOURCE_ENTITY_ID: {"events": [EVENT]}}
    await advance_time(hass, freezer, 59)
    assert mock_get_events.await_count == 1
    await advance_time(hass, freezer, 1)
    assert mock_get_events.await_count == 2
    assert hass.states.get(ENTITY_ID).state == "on"


@pytest.mark.parametrize("exception", [ValueError, TypeError])
async def test_invalid_start_conversion(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_get_events: AsyncMock,
    exception: type[Exception],
) -> None:
    """Test date conversion errors skip a malformed event."""
    mock_get_events.return_value = {SOURCE_ENTITY_ID: {"events": [EVENT]}}
    hass.states.async_set(SOURCE_ENTITY_ID, "on")
    with patch(
        "custom_components.calendar_event.binary_sensor.dt_util.parse_datetime",
        side_effect=exception,
    ):
        await setup_integration(hass, mock_config_entry)
    assert hass.states.get(ENTITY_ID).state == "off"
