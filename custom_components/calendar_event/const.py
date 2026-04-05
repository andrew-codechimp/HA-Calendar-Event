"""Constants for calendar_event."""

from logging import Logger, getLogger

from homeassistant.const import Platform

LOGGER: Logger = getLogger(__package__)

MIN_HA_VERSION = "2025.12"

DOMAIN = "calendar_event"
CONFIG_VERSION = 1

PLATFORMS = [Platform.BINARY_SENSOR]

CONF_CALENDAR_ENTITY_ID = "calendar_entity_id"
CONF_MATCH = "match"
CONF_COMPARISON_METHOD = "comparison_method"
CONF_MATCH_ATTRIBUTE = "match_attribute"

ATTR_DESCRIPTION = "description"
ATTR_LOCATION = "location"
ATTR_SUMMARY = "summary"
