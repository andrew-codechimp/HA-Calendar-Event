"""Custom integration to provide calendar_event helpers for Home Assistant.

For more details about this integration, please refer to
https://github.com/andrew-codechimp/HA-Calendar-Event
"""

from __future__ import annotations

import voluptuous as vol
from awesomeversion.awesomeversion import AwesomeVersion
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import __version__ as HA_VERSION  # noqa: N812
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.helper_integration import async_handle_source_entity_changes
from homeassistant.helpers.issue_registry import (
    IssueSeverity,
    async_create_issue,
    async_delete_issue,
)
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_CALENDAR_ENTITY_ID,
    DOMAIN,
    ISSUE_MISSING_CALENDAR_ENTITY,
    LOGGER,
    MIN_HA_VERSION,
    PLATFORMS,
)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(
    hass: HomeAssistant,  # pylint: disable=unused-argument
    config: ConfigType,  # pylint: disable=unused-argument
) -> bool:
    """Integration setup."""

    if AwesomeVersion(HA_VERSION) < AwesomeVersion(MIN_HA_VERSION):  # pragma: no cover
        msg = (
            "This integration requires at least Home Assistant version "
            f" {MIN_HA_VERSION}, you are running version {HA_VERSION}."
            " Please upgrade Home Assistant to continue using this integration."
        )
        LOGGER.critical(msg)
        return False

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up calendar_event from a config entry."""

    entity_registry = er.async_get(hass)

    try:
        _ = er.async_validate_entity_id(
            entity_registry, entry.options[CONF_CALENDAR_ENTITY_ID]
        )
    except vol.Invalid:
        async_create_issue(
            hass,
            DOMAIN,
            f"{ISSUE_MISSING_CALENDAR_ENTITY}_{entry.entry_id}",
            is_fixable=True,
            severity=IssueSeverity.ERROR,
            translation_key="missing_calendar_entity",
            translation_placeholders={
                "calendar_entity": entry.options[CONF_CALENDAR_ENTITY_ID],
                "entry_title": entry.title or "Calendar Event",
            },
            data={"entry_id": entry.entry_id},
        )

        return False

    # Clean up any existing repair issues since the entity is now valid
    async_delete_issue(
        hass, DOMAIN, f"{ISSUE_MISSING_CALENDAR_ENTITY}_{entry.entry_id}"
    )

    def set_source_entity_id_or_uuid(source_entity_id: str) -> None:
        hass.config_entries.async_update_entry(
            entry,
            options={**entry.options, CONF_CALENDAR_ENTITY_ID: source_entity_id},
        )
        # Clean up repair issue when entity is updated
        async_delete_issue(
            hass, DOMAIN, f"{ISSUE_MISSING_CALENDAR_ENTITY}_{entry.entry_id}"
        )

    async def source_entity_removed() -> None:
        # The source entity has been removed, create a repair issue for the removed calendar entity.
        async_create_issue(
            hass,
            DOMAIN,
            f"{ISSUE_MISSING_CALENDAR_ENTITY}_{entry.entry_id}",
            is_fixable=True,
            severity=IssueSeverity.ERROR,
            translation_key="missing_calendar_entity",
            translation_placeholders={
                "calendar_entity": entry.options[CONF_CALENDAR_ENTITY_ID],
                "entry_title": entry.title or "Calendar Event",
            },
            data={"entry_id": entry.entry_id},
        )

    entry.async_on_unload(
        async_handle_source_entity_changes(
            hass,
            helper_config_entry_id=entry.entry_id,
            set_source_entity_id_or_uuid=set_source_entity_id_or_uuid,
            source_device_id=None,
            source_entity_id_or_uuid=entry.options[CONF_CALENDAR_ENTITY_ID],
            source_entity_removed=source_entity_removed,
        )
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(config_entry_update_listener))

    return True


async def config_entry_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener, called when the config entry options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    # Clean up any repair issues when unloading the entry
    async_delete_issue(
        hass, DOMAIN, f"{ISSUE_MISSING_CALENDAR_ENTITY}_{entry.entry_id}"
    )

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
