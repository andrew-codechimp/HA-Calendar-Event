"""Test repairs for calendar_event integration."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.calendar_event.const import DOMAIN, ISSUE_MISSING_CALENDAR_ENTITY


async def test_repair_issue_created_for_missing_calendar_entity(
    hass: HomeAssistant,
) -> None:
    """Test that a repair issue is created when calendar entity is missing."""
    
    # Create a config entry with a non-existent calendar entity
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        options={
            "calendar_entity_id": "calendar.nonexistent", 
            "summary": "test"
        },
        title="Test Calendar Event",
    )
    config_entry.add_to_hass(hass)
    
    # Setup should fail and create a repair issue
    assert not await hass.config_entries.async_setup(config_entry.entry_id)
    
    # Check that a repair issue was created
    issue_registry = ir.async_get(hass)
    issue = issue_registry.async_get_issue(
        DOMAIN, f"{ISSUE_MISSING_CALENDAR_ENTITY}_{config_entry.entry_id}"
    )
    
    assert issue is not None
    assert issue.translation_key == "missing_calendar_entity"
    assert issue.is_fixable is True
    assert issue.severity == ir.IssueSeverity.ERROR


async def test_repair_issue_cleaned_up_when_entry_unloaded(
    hass: HomeAssistant,
) -> None:
    """Test that repair issues are cleaned up when config entry is unloaded."""
    
    # Create a config entry with a non-existent calendar entity
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        options={
            "calendar_entity_id": "calendar.nonexistent", 
            "summary": "test"
        },
        title="Test Calendar Event",
    )
    config_entry.add_to_hass(hass)
    
    # Setup should fail and create a repair issue
    assert not await hass.config_entries.async_setup(config_entry.entry_id)
    
    # Verify repair issue exists
    issue_registry = ir.async_get(hass)
    issue = issue_registry.async_get_issue(
        DOMAIN, f"{ISSUE_MISSING_CALENDAR_ENTITY}_{config_entry.entry_id}"
    )
    assert issue is not None
    
    # Remove the config entry
    await hass.config_entries.async_remove(config_entry.entry_id)
    
    # Verify repair issue is cleaned up
    issue = issue_registry.async_get_issue(
        DOMAIN, f"{ISSUE_MISSING_CALENDAR_ENTITY}_{config_entry.entry_id}"
    )
    assert issue is None
