# MyEngie Romania - Home Assistant Integration

**Version:** 0.1.0

A custom Home Assistant integration for MyEngie Romania (ENGIE Romania customer portal) that provides access to:
- Gas/Electricity consumption data
- Current account balance
- Invoice information
- Notification status
- Installation details

## Features

### Current Features
- ✅ Authentication via Auth0
- ✅ Gas consumption index tracking
- ✅ Account balance monitoring
- ✅ Unread notifications count
- ✅ Installation information retrieval
- ✅ Invoice history and details (with 10-invoice history)
- ✅ Invoice status tracking (paid/pending)
- ✅ Latest invoice details (amount, date, due date)
- ✅ Payment status monitoring
- ✅ Pending payments tracking

### Planned Features
- 📋 Electricity consumption (when available)
- 📋 Consumption charts and statistics
- 📋 Automatic index submission
- 📋 Payment reminders
- 📋 Multi-account support

## Installation

### Via HACS (Recommended)

1. Ensure [HACS](https://hacs.xyz/) is installed
2. Add this repository as a custom repository in HACS:
   - URL: `https://github.com/andreisarbu/ha-myEngie`
   - Category: Integration
3. Search for "MyEngie" and install
4. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/myengie` folder to your `custom_components` directory:
   ```bash
   cp -r custom_components/myengie ~/.homeassistant/custom_components/
   ```
2. Restart Home Assistant

## Configuration

### Via UI (Recommended)

1. Go to **Settings** → **Devices & Services** → **Integrations**
2. Click **Create Integration** and search for "MyEngie"
3. Enter your ENGIE Romania credentials:
   - **Username:** Your email or username
   - **Password:** Your ENGIE account password
4. Click **Submit**

### Via YAML (Optional)

Add to your `configuration.yaml`:

```yaml
myengie:
  username: your_email@example.com
  password: your_password
```

Then restart Home Assistant.

## Available Sensors

After setup, the integration creates the following sensors:

| Sensor | Description | Unit | Icon |
|--------|-------------|------|------|
| `sensor.myengie_balance` | Current account balance | RON | 💶 |
| `sensor.myengie_gas_index` | Current gas consumption index | - | 📊 |
| `sensor.myengie_unread_notifications` | Number of unread notifications | - | 🔔 |
| `sensor.myengie_consumption_details` | Summary with 9+ attributes | - | 📈 |
| `sensor.myengie_account_status` | Account status (Up to Date/Pending) | - | ✓ |
| `sensor.myengie_invoice_count` | Total invoice count | - | 📄 |
| `sensor.myengie_pending_payments` | Total pending payment amount | RON | ⚠️ |
| `sensor.myengie_latest_invoice` | Latest invoice amount & details | RON | 📋 |
| `sensor.myengie_invoice_history` | Invoice history with statistics | - | 📁 |

## API Information

### Authentication
- **Provider:** Auth0
- **Base URL:** `https://gwss.engie.ro/myservices/`
- **Token Type:** Bearer JWT

### Key Endpoints
- `GET /v2/app_status` - Application status
- `POST /v1/invoices/ballance-details` - Balance and invoice details
- `GET /v1/index/{poc_number}` - Gas/electricity index data
- `GET /v1/notifications/unread-number` - Unread notifications count
- `POST /v1/widgets/ballance` - Balance widget data

### Account Information Retrieved
- POC (Point of Connection) number
- Installation number
- POD (Point of Delivery)
- Provider account ID
- Gas index and history
- Current balance
- Invoice data

## Troubleshooting

### Authentication Issues
- Verify your ENGIE credentials are correct
- Ensure your account is active and not blocked
- Check if your email has been verified with ENGIE
- **Account Lockout:** Too many failed attempts may temporarily lock your account
- **Username Format:** Use your full email address as registered with ENGIE

### Debug Authentication
Use the included debug script to test authentication outside of Home Assistant:

```bash
cd /path/to/ha-myEngie
python3 debug_auth.py
```

This will help identify if the issue is with credentials or the integration.

### No Data Available
- Check Home Assistant logs for error messages
- Verify internet connection
- Ensure ENGIE servers are accessible from your network

### Update Interval
- Default update interval: 1 hour
- Minimum update interval: 5 minutes
- Data is cached to avoid excessive API calls

## Privacy & Security

This integration:
- ✅ Does not store passwords in plain text
- ✅ Uses OAuth2/Auth0 for secure authentication
- ✅ Only requests necessary data from ENGIE API
- ✅ Complies with GDPR for personal data handling

**Important:** Never share your credentials or configuration files that contain them.

## Support

For issues, feature requests, or contributions:
- GitHub Issues: [ha-myEngie Issues](https://github.com/andreisarbu/ha-myEngie/issues)
- GitHub Discussions: [ha-myEngie Discussions](https://github.com/andreisarbu/ha-myEngie/discussions)

## Development

### Project Structure

```
custom_components/myengie/
├── __init__.py           # Main integration setup
├── api.py                # API client
├── config_flow.py        # Configuration UI flow
├── const.py              # Constants
├── sensor.py             # Sensor entities
├── manifest.json         # Integration metadata
├── strings.json          # UI translations (template)
└── translations/
    └── en.json           # English translations
```

### Dependencies
- `auth0-python` - Auth0 authentication
- `aiohttp` - Async HTTP client (included with Home Assistant)

### Testing
To test the integration locally:

1. Copy to custom_components
2. Restart Home Assistant
3. Add via Integrations UI
4. Check Home Assistant logs: `tail -f config/home-assistant.log`

## Documentation

Comprehensive documentation available in the [`/docs`](docs/) folder:
- [Quick Reference Guide](docs/QUICK_REFERENCE.md) - Quick setup and usage
- [Implementation Details](docs/IMPLEMENTATION.md) - Technical implementation
- [Invoice History Features](docs/INVOICE_HISTORY.md) - Invoice tracking
- [Using Invoice Sensors](docs/USING_INVOICE_SENSORS.md) - Templates and automations
- [API Reference](docs/API_REFERENCE.md) - API endpoints and responses
- [Development Guide](docs/DEVELOPMENT.md) - For contributors

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This is an unofficial integration and is not affiliated with or endorsed by ENGIE Romania. Use at your own risk. Always follow ENGIE's terms of service when using this integration.

## Links

- [ENGIE Romania Website](https://www.engie.ro)
- [Home Assistant Developer Docs](https://developers.home-assistant.io)
- [HACS Documentation](https://hacs.xyz)

---

**Last Updated:** April 2026
**Maintainer:** Andrei Sarbu
