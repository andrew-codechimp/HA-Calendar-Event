"""Constants for calendar_event."""

from logging import Logger, getLogger

from homeassistant.const import Platform

LOGGER: Logger = getLogger(__package__)

MIN_HA_VERSION = "2025.7"

CONFIG_VERSION = 1

PLATFORMS = [Platform.BINARY_SENSOR]

CONF_CALENDAR_ENTITY_ID = "calendar_entity_id"
CONF_SUMMARY = "summary"
CONF_COMPARISON_METHOD = "comparison_method"

ATTR_DESCRIPTION = "description"
