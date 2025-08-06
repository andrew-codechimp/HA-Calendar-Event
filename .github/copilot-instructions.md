# GitHub Copilot Instructions for HA-Calendar-Event

## Project Overview
This is a Home Assistant custom integration that creates binary sensors monitoring calendar events. The integration provides "helper" entities that turn on when calendar events match specific summary text criteria.

## Architecture & Key Components

### Core Integration Structure
- **`custom_components/calendar_event/`** - Main integration package
- **`__init__.py`** - Integration setup, version validation, platform registration
- **`binary_sensor.py`** - Binary sensor platform that monitors calendar entities
- **`config_flow.py`** - Schema-based config flow using `SchemaConfigFlowHandler`
- **`const.py`** - Constants defined from `manifest.json` + configuration keys
- **`translations/`** - Multi-language UI strings for config flow

### State Monitoring Pattern
Binary sensors use **event-driven state monitoring**:
```python
# In binary_sensor.py - key pattern for state listeners
self.async_on_remove(
    self._hass.bus.async_listen(
        EVENT_STATE_CHANGED, self._calendar_state_changed
    )
)
```
Sensors check calendar entity's `message` attribute against configured `summary` text using case-insensitive partial matching.

### Configuration Schema Pattern
- **Config flow**: Uses `SchemaConfigFlowHandler` with `OPTIONS_SCHEMA.extend()` pattern
- **Required fields**: `calendar_entity` (entity selector), `summary` (text), `name` (text)
- **Data access**: Use `config_entry.data[CONST_KEY]` for required fields, `.get()` for optional
- **Constants**: All config keys defined in `const.py` (e.g., `CONF_CALENDAR_ENTITY`, `CONF_SUMMARY`)

## Development Workflows

### Local Development
```bash
scripts/develop    # Starts HA with integration loaded on :8123
scripts/lint       # Runs ruff linting with --fix
scripts/setup      # Installs all dependencies
```

### Testing
```bash
pytest tests/                                                    # All tests
pytest --cov-report term-missing --cov=custom_components.calendar_event tests  # With coverage
pytest tests/test_binary_sensor.py -k test_state_sensor          # Specific test
```

### Key Development Files
- **`config/configuration.yaml`** - Test HA config with debug logging enabled
- **`.vscode/tasks.json`** - VS Code task for running HA (port 8123)
- **`pyproject.toml`** - Ruff, pytest, and poetry configuration

## Code Patterns & Conventions

### Constant Usage
Always use constants from `const.py` for configuration keys:
```python
from .const import CONF_CALENDAR_ENTITY, CONF_SUMMARY, ATTR_DESCRIPTION
# Use CONF_CALENDAR_ENTITY, not "calendar_entity"
```

### Translation Structure
Translation files use nested `config.step.user.data` and `options.step.init.data` structure with `data_description` for field help text. All descriptions end with periods.

### Entity Attributes
Binary sensors include calendar event `description` as an attribute using `ATTR_DESCRIPTION` constant for the key.

### Async Patterns
- Use `@callback` decorator for event handlers
- Call `self.async_write_ha_state()` after state changes
- Handle `None` states gracefully when monitored entities are unavailable

## Integration Testing Notes
Tests use `MockConfigEntry` with `options` field containing config data. Entity registry and label registry fixtures are used extensively for testing entity relationships.

## Build & Release
- **GitHub Actions**: Lint, test, HACS/Hassfest validation on push/PR
- **Release**: Auto-generates ZIP with version updates from Git tags
- **HACS**: Configured via `hacs.json` with ZIP release strategy
