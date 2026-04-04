"""Constants for MyEngie integration."""

DOMAIN = "myengie"
DEFAULT_UPDATE_INTERVAL = 3600  # 1 hour
MINIMUM_UPDATE_INTERVAL = 300  # 5 minutes

# Account data keys
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# Data keys for coordinator
ATTR_BALANCE = "balance"
ATTR_GAS_INDEX = "gas_index"
ATTR_NOTIFICATIONS = "notifications"
ATTR_BANNERS = "banners"

# Sensor device classes
DEFAULT_ICON_BALANCE = "mdi:currency-eur"
DEFAULT_ICON_GAS = "mdi:gauge"
DEFAULT_ICON_NOTIFICATIONS = "mdi:bell"
