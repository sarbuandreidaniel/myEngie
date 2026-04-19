# MyEngie Integration Implementation Status

## Completed (Version 0.1.0)

### 1. ✅ Auth0 OAuth2 Authentication (`auth.py`)
- **Created:** Complete Auth0 authentication manager
- **Features:**
  - Username/password authentication flow
  - Resource Owner Password Grant implementation
  - Automatic token refresh mechanism
  - Token expiry tracking with 5-minute buffer
  - Secure token storage and retrieval
  - Error handling and logging

- **Key Classes:**
  - `Auth0Manager`: Handles all Auth0 interactions
  - Methods:
    - `authenticate()`: Initial authentication with credentials
    - `refresh_access_token()`: Automatic token refresh
    - `is_token_expired()`: Check token status
    - `get_token()`: Retrieve current token
    - `clear_tokens()`: Cleanup on logout

### 2. ✅ API Client Enhancement (`api.py`)
- **Updated:** Full integration with Auth0Manager
- **Features:**
  - Bearer token authentication now uses auth manager
  - Automatic token refresh on 401 responses
  - Request retry logic after token refresh
  - Comprehensive error handling
  - All 8 API endpoints fully implemented:
    - `get_app_status()`: Application status
    - `get_unread_notifications()`: Notification count
    - `get_balance_details()`: Balance and invoices
    - `get_index_data()`: Gas/electricity consumption
    - `get_balance_widget()`: Balance widget data
    - `get_notifications_banner()`: System banners
    - `get_invitations()`: User invitations
    - `get_banners()`: Marketing banners

### 3. ✅ Configuration Flow (`config_flow.py`)
- **Updated:** Credential validation with Auth0
- **Features:**
  - Username/password input fields
  - Real Auth0 credential validation
  - Unique user ID tracking
  - Error messages for failed authentication
  - Support for YAML imports
  - Async validation process

### 4. ✅ Coordinator Data Fetching (`__init__.py`)
- **Enhanced:** Full data fetching implementation
- **Features:**
  - `MyEngieDataUpdateCoordinator` class
  - Automatic authentication on first run
  - Periodic data updates (default: 1 hour)
  - Data aggregation from all API endpoints:
    - Account balance
    - Gas consumption index
    - Notification count
    - Invoice list and count
    - Pending payments
    - Next reading dates
    - Account status (up-to-date flag)
  - Error handling with UpdateFailed
  - Graceful degradation if some endpoints fail
  - Session cleanup on shutdown

### 5. ✅ Additional Sensors (`sensor.py`)
- **Added:** 7 total sensors (3 base + 4 new)
- **Base Sensors:**
  1. `MyEngieBalanceSensor` - Account balance in RON
  2. `MyEngieGasIndexSensor` - Current meter reading (kWh)
  3. `MyEngieNotificationsSensor` - Unread notification count

- **New Consumption & Invoice Sensors:**
  4. `MyEngieConsumptionDetailsSensor` - Detailed consumption info with attributes:
     - Gas index
     - Balance
     - Current notifications
     - Invoice count
     - Pending payments count
     - Account status
     - Next reading dates

  5. `MyEngieUpToDateStatusSensor` - Account payment status:
     - "Up to Date" or "Pending Payments"
     - Used for automations

  6. `MyEngieInvoiceCountSensor` - Total invoice count with attributes:
     - List of last 5 invoices
     - Invoice dates and amounts

  7. `MyEngiePendingPaymentsSensor` - Total pending amount in RON with attributes:
     - Pending payment count
     - Detailed payment information
     - Due dates

### 6. ✅ Localization Files
- **Updated:** strings.json and en.json
- **Added translations for:**
  - Configuration prompts
  - Error messages
  - New sensor names
  - Data field descriptions

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Home Assistant Config Entry                                       │
│ (Username + Password)                                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ MyEngieDataUpdateCoordinator                                      │
│ ├─ Authenticate with Auth0Manager                               │
│ ├─ Fetch from API endpoints                                     │
│ ├─ Aggregate all data                                           │
│ └─ Update sensors every 1 hour                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
    Auth0Manager     MyEngieAPI      Session Manager
    ├─Authenticate   ├─Get Balance   ├─Create/Manage
    ├─Token Refresh  ├─Get Index     └─Cleanup
    └─Token Cache    ├─Get Invoices
                     └─Get Status
                         │
                         ▼
        ┌────────────────────────────────────────────┐
        │ Sensor Entities                             │
        ├─ Balance Sensor (RON)                      │
        ├─ Gas Index Sensor (kWh)                    │
        ├─ Notifications Sensor (count)              │
        ├─ Consumption Details Sensor (attributes)   │
        ├─ Account Status Sensor (Up-to-date)        │
        ├─ Invoice Count Sensor (count)              │
        └─ Pending Payments Sensor (RON)             │
        └────────────────────────────────────────────┘
```

---

## Available Entities

### Sensors

| Entity ID | Name | Unit | Type | Icon |
|-----------|------|------|------|------|
| `sensor.myengie_balance` | Balance | RON | Monetary | 💶 |
| `sensor.myengie_gas_index` | Gas Index | kWh | Gauge | 📊 |
| `sensor.myengie_unread_notifications` | Notifications | count | Integer | 🔔 |
| `sensor.myengie_consumption_details` | Consumption Details | text | Informational | 📈 |
| `sensor.myengie_account_status` | Account Status | text | Enum | ✓ |
| `sensor.myengie_invoice_count` | Invoice Count | count | Integer | 📄 |
| `sensor.myengie_pending_payments` | Pending Payments | RON | Monetary | ⚠️ |

### Sensor Attributes

Each sensor provides additional attributes:

**Gas Index Sensor:**
- `next_read_start`: Next reading period start date
- `next_read_end`: Next reading period end date

**Consumption Details Sensor:**
- `gas_index`: Current meter reading
- `balance`: Account balance
- `notifications`: Unread count
- `invoice_count`: Total invoices
- `pending_payments`: Count of pending
- `is_up_to_date`: Boolean status
- `next_read_start`: Reading period start
- `next_read_end`: Reading period end

**Invoice Count Sensor:**
- `invoices`: Array of last 5 invoices with:
  - `date`: Invoice date
  - `amount`: Invoice amount
  - `status`: Invoice status

**Pending Payments Sensor:**
- `pending_count`: Number of pending payments
- `payments`: Array of pending payments with:
  - `amount`: Payment amount
  - `due_date`: When payment is due
  - `description`: Payment description

---

## Authentication Details

### Auth0 Configuration
- **Domain:** auth.engie.ro
- **Client ID:** iTSW5r2awGCwSdkGDx66h76wiTnbNZgy
- **Grant Type:** Resource Owner Password Grant
- **Realm:** MyEngieUsers
- **Scopes:** openid, profile, email, offline_access
- **Audience:** https://myservices.engie.ro

### Token Lifecycle
1. User provides credentials during setup
2. Auth0Manager authenticates and gets access token + refresh token
3. Access token used for all API requests (default expiry: 1 hour)
4. Token automatically refreshed when:
   - Less than 5 minutes remaining
   - API returns 401 Unauthorized
   - Next coordinator update occurs
5. Refresh token persists for offline access

---

## Data Fetching Strategy

### Update Interval
- **Default:** 3600 seconds (1 hour)
- **Minimum:** 300 seconds (5 minutes)
- **Configuration:** Via `const.py`

### API Calls Per Update
- Typically makes 6-8 API calls per update cycle
- Gracefully handles partial failures
- Falls back to cached data if endpoints fail
- Logs all errors for debugging

### Data Aggregation
```python
{
    "balance": float,              # Account balance in RON
    "gas_index": int,              # Current meter reading
    "notifications": int,          # Unread count
    "invoices": [{...}],           # Invoice list
    "pending": [{...}],            # Pending payments
    "next_read_dates": {...},      # Reading period
    "balance_details": {...},      # Balance widget data
    "banners": [{...}],            # System banners
    "index_history": [],           # Historical data
    "is_up_to_date": bool,         # Payment status
    "invoice_count": int,          # Total invoices
}
```

---

## Error Handling

### Authentication Errors
- Invalid credentials: Shown to user in config flow
- Token expired: Automatic refresh
- Refresh failed: UpdateFailed exception

### API Errors
- 401 Unauthorized: Token refresh + retry
- 403 Forbidden: Log error, continue with cached data
- 404 Not Found: Skip endpoint, continue
- 500 Server Error: UpdateFailed with retry next cycle

### Network Errors
- Connection timeout: UpdateFailed with exception
- DNS resolution: UpdateFailed with exception
- SSL/TLS: UpdateFailed with exception

---

## Testing Checklist

- [x] Auth0 authentication with valid credentials
- [x] Auth0 authentication with invalid credentials
- [x] Token refresh mechanism
- [x] API endpoint integration
- [x] Data aggregation and parsing
- [x] Sensor entity creation
- [x] Sensor attribute population
- [x] Error handling and recovery
- [x] Config flow validation
- [ ] Multi-account support (future)
- [ ] UI display of sensor data
- [ ] Automation triggers
- [ ] Energy dashboard integration

---

## Known Limitations

1. **Single Account:** Currently supports one account per integration instance
2. **No Index Submission:** Cannot submit meter readings (read-only)
3. **Limited Account Selection:** Doesn't auto-detect user accounts from API
4. **No Historical Charts:** Doesn't fetch detailed consumption history yet
5. **Manual Configuration:** Requires manual entry of credentials

---

## Next Phase Tasks

### Phase 2: Multi-Account Support
- [ ] Account discovery from API
- [ ] Per-account sensor entities
- [ ] Account selection in config flow

### Phase 3: Services & Automations
- [ ] Service: Submit meter reading
- [ ] Service: Get invoice PDF
- [ ] Service: Request technical service
- [ ] Automation: High consumption alert
- [ ] Automation: New invoice notification

### Phase 4: Advanced Features
- [ ] Consumption analytics
- [ ] Cost estimation
- [ ] Trend analysis
- [ ] Energy dashboard integration
- [ ] Mobile card UI

---

## Testing Instructions

### Manual Testing
1. Copy integration to `~/.homeassistant/custom_components/myengie`
2. Restart Home Assistant
3. Go to Settings → Devices & Services
4. Add new integration, search for "MyEngie"
5. Enter valid ENGIE Romania credentials
6. Verify sensors appear and update

### Debug Logging
Add to `configuration.yaml`:
```yaml
logger:
  logs:
    custom_components.myengie: debug
    custom_components.myengie.auth: debug
    custom_components.myengie.api: debug
```

### Troubleshooting
- Check logs for "Auth0 authentication"
- Verify ENGIE account is active
- Confirm internet connection
- Test credentials on my.engie.ro first

---

## File Summary

| File | Status | Changes |
|------|--------|---------|
| `__init__.py` | ✅ Complete | Full coordinator implementation |
| `api.py` | ✅ Complete | Auth manager integration |
| `auth.py` | ✅ New | Auth0 authentication |
| `config_flow.py` | ✅ Complete | Credential validation |
| `sensor.py` | ✅ Complete | 7 sensors with attributes |
| `const.py` | ✅ Complete | Constants and config |
| `manifest.json` | ✅ Complete | Updated dependencies |
| `strings.json` | ✅ Complete | UI translations |
| `translations/en.json` | ✅ Complete | English translations |

---

## Version History

### v0.1.0 (Current)
- ✅ Auth0 authentication
- ✅ API integration
- ✅ Data coordinator
- ✅ 7 sensors
- ✅ Configuration flow
- ✅ Error handling

### v0.0.1 (Initial Scaffold)
- Basic project structure
- Placeholder files

---

**Last Updated:** April 4, 2026
**Implementation Status:** 75% Complete
**Next Milestone:** Multi-account support
