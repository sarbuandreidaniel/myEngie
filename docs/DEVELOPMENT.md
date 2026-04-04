# Development Guide for MyEngie Home Assistant Integration

## Overview

This document provides guidance for developers who want to extend or contribute to the MyEngie Home Assistant integration.

## Project Structure

```
custom_components/myengie/
├── __init__.py                  # Main integration setup and coordinator
├── api.py                       # MyEngie API client
├── config_flow.py              # Configuration UI flow and validation
├── const.py                    # Constants and configuration
├── sensor.py                   # Sensor entities
├── manifest.json               # Integration metadata
├── strings.json                # UI string templates
└── translations/
    └── en.json                 # English translations
```

## Core Components

### 1. API Client (`api.py`)

The `MyEngieAPI` class handles all communication with the MyEngie API.

**Key Methods:**
- `get_app_status()`: Check API availability
- `get_unread_notifications()`: Get notification count
- `get_balance_details()`: Fetch balance and invoices
- `get_index_data()`: Get consumption index
- `get_balance_widget()`: Get balance widget data
- `get_notifications_banner()`: Get system banners
- `get_invitations()`: Get user invitations
- `get_banners()`: Get marketing banners

**Authentication:**
- Uses Auth0 Bearer token
- Token obtained through Auth0 authentication flow
- Token included in all requests

**Error Handling:**
- Returns structured response with error flag
- Logs errors for debugging
- Returns empty data on failure

### 2. Configuration Flow (`config_flow.py`)

Handles user configuration through Home Assistant UI.

**Current Implementation:**
- `async_step_user()`: Collect username and password
- Basic validation of input
- Unique ID check to prevent duplicates
- Import step for YAML configuration

**Future Enhancements:**
- OAuth2 integration for more secure auth
- Account selection for multi-account support
- Advanced options (update interval, etc.)

### 3. Data Coordinator (`__init__.py`)

The `MyEngieDataUpdateCoordinator` manages data fetching and caching.

**Responsibilities:**
- Periodic data updates
- Error handling and retry logic
- Data caching between updates
- Coordination with Home Assistant

**Key Properties:**
- Username and password storage
- API client instance
- Account data cache
- Update interval (default: 1 hour)

### 4. Sensors (`sensor.py`)

Entity definitions for Home Assistant.

**Current Sensors:**
- `MyEngieBalanceSensor`: Account balance (RON)
- `MyEngieGasIndexSensor`: Gas consumption index
- `MyEngieNotificationsSensor`: Unread notifications count

**Entity Structure:**
- Inherits from `CoordinatorEntity` and `SensorEntity`
- Unique IDs for entity tracking
- Device info for grouping
- Update via coordinator

## Adding New Features

### Adding a New Sensor

1. **Add to API client** (`api.py`):
   ```python
   async def get_consumption_chart(self, account_id: str) -> Dict[str, Any]:
       """Get consumption chart data."""
       return await self._request(
           "GET",
           f"{API_BASE_URL}/v1/consumption/chart/{account_id}"
       )
   ```

2. **Add constant** (`const.py`):
   ```python
   ATTR_CONSUMPTION_CHART = "consumption_chart"
   ```

3. **Create sensor entity** (`sensor.py`):
   ```python
   class MyEngieConsumptionSensor(CoordinatorEntity, SensorEntity):
       """Sensor for consumption data."""
       _attr_name = "MyEngie Consumption"
       _attr_unit_of_measurement = "kWh"
       
       @property
       def native_value(self):
           if self.coordinator.data:
               return self.coordinator.data.get("consumption_chart")
           return None
   ```

4. **Add to setup** (`sensor.py`):
   ```python
   entities = [
       # ... existing sensors
       MyEngieConsumptionSensor(coordinator, config_entry),
   ]
   ```

5. **Update coordinator data fetch** (`__init__.py`):
   ```python
   async def _async_update_data(self) -> dict:
       try:
           # ... existing fetches
           consumption = await self.api.get_consumption_chart(account_id)
           return {
               "balance": balance,
               "consumption_chart": consumption,
               # ...
           }
       except Exception as err:
           raise UpdateFailed(f"Error: {err}")
   ```

### Adding a New Platform

Example: Adding a `binary_sensor` platform for installation status

1. Create `binary_sensor.py`:
   ```python
   """Binary sensor platform for MyEngie."""
   from homeassistant.components.binary_sensor import BinarySensorEntity
   from .const import DOMAIN
   
   async def async_setup_entry(hass, config_entry, async_add_entities):
       """Set up binary sensors."""
       coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
       entities = [
           MyEngieInstallationStatusSensor(coordinator, config_entry),
       ]
       async_add_entities(entities)
   ```

2. Update `__init__.py`:
   ```python
   PLATFORMS = ["sensor", "binary_sensor"]
   ```

### Implementing Authentication

The integration needs proper Auth0 authentication. Current implementation needs completion:

```python
async def authenticate(username: str, password: str) -> str:
    """Authenticate with Auth0 and return access token."""
    async with aiohttp.ClientSession() as session:
        data = {
            "client_id": "iTSW5r2awGCwSdkGDx66h76wiTnbNZgy",
            "audience": "https://myservices.engie.ro",
            "username": username,
            "password": password,
            "grant_type": "http://auth0.com/oauth/grant-type/passwordless/otp",
            "realm": "SMS",
            "scope": "openid profile email offline_access"
        }
        async with session.post(
            "https://auth.engie.ro/oauth/token",
            json=data
        ) as resp:
            if resp.status == 200:
                response = await resp.json()
                return response["access_token"]
            raise Exception("Authentication failed")
```

## Testing

### Unit Tests
Create `tests/` directory with test files:

```python
# tests/test_api.py
import pytest
from custom_components.myengie.api import MyEngieAPI

@pytest.mark.asyncio
async def test_get_app_status():
    """Test app status endpoint."""
    # Mock session and API
    api = MyEngieAPI(mock_session, "test_token")
    result = await api.get_app_status()
    assert not result["error"]
```

### Integration Testing
```bash
# Copy to config/custom_components
cp -r custom_components/myengie ~/.homeassistant/custom_components/

# Restart Home Assistant and add integration via UI
```

## Debugging

### Enable Debug Logging
Add to `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.myengie: debug
```

### Common Issues

1. **Token Expiration**: Tokens expire after 1 hour. Need to implement refresh token logic.
2. **Rate Limiting**: API may limit requests. Implement backoff strategy.
3. **Multi-Account**: Currently supports single account. Design needed for multiple accounts.

## Documentation

Update these files when making changes:
- `README.md`: User-facing documentation
- `docs/API_REFERENCE.md`: API endpoint documentation
- Code comments for complex logic

## Code Style

- Follow PEP 8 style guide
- Use type hints
- Include docstrings for all functions/classes
- Use logging for debugging

## Dependency Management

- Always check Home Assistant version compatibility
- Use standard Home Assistant patterns
- Minimize external dependencies
- Use aiohttp for async HTTP requests

## Security Considerations

- Never log credentials
- Use secure token storage
- Validate all user inputs
- Implement rate limiting
- Handle errors gracefully

## Performance Optimization

- Implement data caching
- Use coordinator for efficient updates
- Avoid blocking operations
- Batch API requests when possible

## Future Roadmap

- [ ] OAuth2 authentication
- [ ] Multi-account support
- [ ] Consumption analytics
- [ ] Automatic index submission
- [ ] Integration with energy dashboard
- [ ] Custom actions/services
- [ ] Notification actions
- [ ] Electricity data support

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Update documentation
6. Submit a pull request

## Resources

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Home Assistant Architecture](https://developers.home-assistant.io/docs/architecture_index/)
- [HACS Development](https://hacs.xyz/docs/developer/start)
- [Auth0 Documentation](https://auth0.com/docs)

## Support

For questions or issues with development:
- Open an issue on GitHub
- Join Home Assistant Discord community
- Check existing documentation

---

**Last Updated:** April 2026
