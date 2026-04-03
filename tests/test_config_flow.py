"""Test calendar_event config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from custom_components.calendar_event.const import (
    CONF_CALENDAR_ENTITY_ID,
    CONF_COMPARISON_METHOD,
    CONF_MATCH,
    CONF_MATCH_ATTRIBUTE,
    DOMAIN,
)

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


@pytest.mark.parametrize(
    (
        "name",
        "calendar_entity_id",
        "summary",
        "match_attribute",
        "comparison_method",
    ),
    [
        (
            "Test Calendar Event",
            "calendar.my_calendar",
            "Meeting",
            "summary",
            "contains",
        ),
        (
            "Another Test",
            "calendar.work_calendar",
            "Doctor",
            "summary",
            "starts_with",
        ),
        (
            "Third Test",
            "calendar.personal",
            "Appointment",
            "summary",
            "ends_with",
        ),
        (
            "Exact Match Test",
            "calendar.events",
            "Birthday Party",
            "summary",
            "exactly",
        ),
    ],
)
async def test_config_flow(
    hass: HomeAssistant,
    name: str,
    calendar_entity_id: str,
    summary: str,
    match_attribute: str,
    comparison_method: str,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test the config flow."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: name,
            CONF_CALENDAR_ENTITY_ID: calendar_entity_id,
            CONF_MATCH: summary,
            CONF_MATCH_ATTRIBUTE: match_attribute,
            CONF_COMPARISON_METHOD: comparison_method,
        },
    )

    await hass.async_block_till_done()

    assert result.get("type") is FlowResultType.CREATE_ENTRY
    assert result.get("version") == 2
    assert result.get("title") == name

    assert result.get("options") == {
        CONF_NAME: name,
        CONF_CALENDAR_ENTITY_ID: calendar_entity_id,
        CONF_MATCH: summary,
        CONF_MATCH_ATTRIBUTE: match_attribute,
        CONF_COMPARISON_METHOD: comparison_method,
    }

    assert len(mock_setup_entry.mock_calls) == 1


async def test_options_flow(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test the options flow."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    # Create a config entry
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            CONF_NAME: "Original Name",
            CONF_CALENDAR_ENTITY_ID: "calendar.original",
            CONF_MATCH: "Original Summary",
            CONF_MATCH_ATTRIBUTE: "summary",
            CONF_COMPARISON_METHOD: "contains",
        },
        title="Original Name",
    )
    config_entry.add_to_hass(hass)

    # Start the options flow
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "init"

    # Configure the options
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_CALENDAR_ENTITY_ID: "calendar.updated",
            CONF_MATCH: "Updated Summary",
            CONF_MATCH_ATTRIBUTE: "summary",
            CONF_COMPARISON_METHOD: "starts_with",
        },
    )

    await hass.async_block_till_done()

    assert result.get("type") is FlowResultType.CREATE_ENTRY
    assert result.get("data") == {
        CONF_NAME: "Original Name",
        CONF_CALENDAR_ENTITY_ID: "calendar.updated",
        CONF_MATCH: "Updated Summary",
        CONF_MATCH_ATTRIBUTE: "summary",
        CONF_COMPARISON_METHOD: "starts_with",
    }
