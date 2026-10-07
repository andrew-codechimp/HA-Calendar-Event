"""Fixtures for Calendar Event tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from custom_components.calendar_event.const import (
    CONF_CALENDAR_ENTITY_ID,
    CONF_COMPARISON_METHOD,
    CONF_MATCH,
    CONF_MATCH_ATTRIBUTE,
    DOMAIN,
)
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.syrupy import HomeAssistantSnapshotExtension
from syrupy.assertion import SnapshotAssertion

from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, SupportsResponse
from homeassistant.helpers import entity_registry as er

from .const import DEFAULT_NAME, SOURCE_ENTITY_ID


@pytest.fixture
def snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Use the Home Assistant snapshot serializer."""
    return snapshot.use_extension(HomeAssistantSnapshotExtension)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations in Home Assistant."""


@pytest.fixture(autouse=True)
def freeze_setup_time(freezer: FrozenDateTimeFactory) -> None:
    """Keep entity timestamps and scheduled callbacks stable."""
    freezer.move_to("2026-07-01T12:00:00+00:00")


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Mock integration setup when testing flows in isolation."""
    with patch(
        "custom_components.calendar_event.async_setup_entry", return_value=True
    ) as mock_setup:
        yield mock_setup


@pytest.fixture
def mock_config_entry(request: pytest.FixtureRequest) -> MockConfigEntry:
    """Create a helper entry with default options and optional overrides."""
    return MockConfigEntry(
        domain=DOMAIN,
        version=2,
        minor_version=1,
        entry_id="helper-entry",
        title=DEFAULT_NAME,
        data={},
        options={
            CONF_NAME: DEFAULT_NAME,
            CONF_CALENDAR_ENTITY_ID: SOURCE_ENTITY_ID,
            CONF_MATCH: "Meeting",
            CONF_MATCH_ATTRIBUTE: "summary",
            CONF_COMPARISON_METHOD: "contains",
            **getattr(request, "param", {}),
        },
    )


@pytest.fixture
def source_calendar(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> er.RegistryEntry:
    """Register a calendar source with no active event."""
    entity = entity_registry.async_get_or_create(
        "calendar", "test", "calendar", suggested_object_id="my_calendar"
    )
    hass.states.async_set(entity.entity_id, "off")
    return entity


@pytest.fixture
def mock_get_events(hass: HomeAssistant) -> AsyncMock:
    """Register the calendar action with a controllable event response."""
    handler = AsyncMock(return_value={SOURCE_ENTITY_ID: {"events": []}})
    hass.services.async_register(
        "calendar", "get_events", handler, supports_response=SupportsResponse.ONLY
    )
    return handler
