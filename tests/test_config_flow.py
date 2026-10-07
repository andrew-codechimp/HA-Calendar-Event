"""Tests for Calendar Event config and options flows."""

from unittest.mock import AsyncMock

import pytest
from custom_components.calendar_event.const import (
    CONF_CALENDAR_ENTITY_ID,
    CONF_COMPARISON_METHOD,
    CONF_MATCH,
    CONF_MATCH_ATTRIBUTE,
    DOMAIN,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .const import DEFAULT_NAME, SOURCE_ENTITY_ID


@pytest.mark.parametrize("method", ["contains", "starts_with", "ends_with", "exactly"])
@pytest.mark.parametrize("attribute", ["summary", "description", "location", "any"])
async def test_user_flow(
    hass: HomeAssistant, mock_setup_entry: AsyncMock, method: str, attribute: str
) -> None:
    """Test every matching method and field can be configured."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    options = {
        CONF_NAME: DEFAULT_NAME,
        CONF_CALENDAR_ENTITY_ID: SOURCE_ENTITY_ID,
        CONF_MATCH: "Meeting",
        CONF_MATCH_ATTRIBUTE: attribute,
        CONF_COMPARISON_METHOD: method,
    }
    result = await hass.config_entries.flow.async_configure(result["flow_id"], options)
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["version"] == 2
    assert result["title"] == DEFAULT_NAME
    assert result["data"] == {}
    assert result["options"] == options
    mock_setup_entry.assert_awaited_once()


@pytest.mark.usefixtures("mock_setup_entry")
async def test_defaults(hass: HomeAssistant) -> None:
    """Test missing optional choices default to contains and summary."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: DEFAULT_NAME,
            CONF_CALENDAR_ENTITY_ID: SOURCE_ENTITY_ID,
            CONF_MATCH: "Meeting",
        },
    )
    assert result["options"][CONF_MATCH_ATTRIBUTE] == "summary"
    assert result["options"][CONF_COMPARISON_METHOD] == "contains"
    await hass.async_block_till_done()


async def test_options(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Test saved values are suggested and changes preserve the helper's name."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert {
        key.schema: key.description["suggested_value"]
        for key in result["data_schema"].schema
    } == {
        key: value
        for key, value in mock_config_entry.options.items()
        if key != CONF_NAME
    }
    options = {
        CONF_CALENDAR_ENTITY_ID: "calendar.other",
        CONF_MATCH: "Office",
        CONF_MATCH_ATTRIBUTE: "location",
        CONF_COMPARISON_METHOD: "exactly",
    }
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], options
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options == {CONF_NAME: DEFAULT_NAME, **options}
    assert mock_config_entry.title == DEFAULT_NAME
    assert mock_config_entry.data == {}


async def test_source_selector(hass: HomeAssistant) -> None:
    """Test only calendar entities are offered as sources."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["data_schema"].schema[CONF_CALENDAR_ENTITY_ID].config["domain"] == [
        "calendar"
    ]
