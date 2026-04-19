# Using Invoice Sensors in Home Assistant

## Available Invoice Sensors

### 1. Latest Invoice (`sensor.myengie_latest_invoice`)

Get the latest invoice information directly:

```yaml
# In automations or templates
state: "{{ states('sensor.myengie_latest_invoice') }}"
amount: "{{ states('sensor.myengie_latest_invoice') | float(0) }}"
due_date: "{{ state_attr('sensor.myengie_latest_invoice', 'due_date') }}"
invoice_number: "{{ state_attr('sensor.myengie_latest_invoice', 'invoice_number') }}"
```

### 2. Invoice History (`sensor.myengie_invoice_history`)

Access comprehensive invoice data:

```yaml
total_count: "{{ states('sensor.myengie_invoice_history') }}"
average: "{{ state_attr('sensor.myengie_invoice_history', 'average_amount') }}"
paid: "{{ state_attr('sensor.myengie_invoice_history', 'paid_count') }}"
pending: "{{ state_attr('sensor.myengie_invoice_history', 'pending_count') }}"
```

### 3. Invoice Count (`sensor.myengie_invoice_count`)

Quick reference to total invoices:

```yaml
total: "{{ states('sensor.myengie_invoice_count') }}"
```

### 4. Pending Payments (`sensor.myengie_pending_payments`)

Track outstanding amounts:

```yaml
total_pending: "{{ states('sensor.myengie_pending_payments') }}"
pending_count: "{{ state_attr('sensor.myengie_pending_payments', 'pending_count') }}"
```

## Template Examples

### Simple Invoice Info Display

```yaml
sensor:
  - platform: template
    sensors:
      latest_invoice_info:
        friendly_name: "Latest Invoice"
        value_template: >
          {{ states('sensor.myengie_latest_invoice') | float(0) | round(2) }} RON
        entity_picture_template: "mdi:receipt"
```

### Invoice Due Days Calculator

```yaml
sensor:
  - platform: template
    sensors:
      invoice_due_days:
        friendly_name: "Days Until Due"
        value_template: >
          {% set due = state_attr('sensor.myengie_latest_invoice', 'due_date') %}
          {% if due %}
            {%- set due_dt = as_datetime(due) %}
            {%- set days = (due_dt - now()).days %}
            {{ days }}
          {% else %}
            Unknown
          {% endif %}
        unit_of_measurement: "days"
```

### Invoice Payment Status

```yaml
sensor:
  - platform: template
    sensors:
      invoice_payment_status:
        friendly_name: "Invoice Status"
        value_template: >
          {% set status = state_attr('sensor.myengie_latest_invoice', 'status') %}
          {% set due_dt = as_datetime(state_attr('sensor.myengie_latest_invoice', 'due_date')) %}
          {% set now = now() %}
          
          {% if status == "Paid" %}
            ✅ Paid
          {% elif now > due_dt %}
            ⚠️ Overdue
          {% elif (due_dt - now).days <= 3 %}
            ⏰ Due Soon
          {% else %}
            📋 Pending
          {% endif %}
        icon_template: >
          {% set status = state_attr('sensor.myengie_latest_invoice', 'status') %}
          {% if status == "Paid" %}
            mdi:check-circle
          {% elif status == "Overdue" %}
            mdi:alert-circle
          {% else %}
            mdi:calendar-clock
          {% endif %}
```

### Monthly Spending Trend

```yaml
sensor:
  - platform: template
    sensors:
      myengie_average_invoice:
        friendly_name: "Average Monthly Bill"
        value_template: >
          {{ state_attr('sensor.myengie_invoice_history', 'average_amount') | float(0) | round(2) }}
        unit_of_measurement: "RON"
        icon_template: "mdi:chart-line"
```

### Account Balance Status

```yaml
sensor:
  - platform: template
    sensors:
      account_balance_status:
        friendly_name: "Balance Status"
        value_template: >
          {% set balance = states('sensor.myengie_balance') | float(0) %}
          {% set pending = states('sensor.myengie_pending_payments') | float(0) %}
          
          {% if balance < 0 %}
            ❌ Negative Balance
          {% elif pending > 0 %}
            ⚠️ Has Pending Payments
          {% else %}
            ✅ Healthy
          {% endif %}
```

## Lovelace Card Examples

### Invoice Summary Card

```yaml
type: entities
title: 📋 Invoice Information
entities:
  - entity: sensor.myengie_latest_invoice
    name: Latest Invoice Amount
  - entity: sensor.myengie_invoice_count
    name: Total Invoices
  - entity: sensor.myengie_pending_payments
    name: Pending Amount
  - entity: sensor.myengie_account_status
    name: Account Status
```

### Markdown Card with Recent Invoices

```yaml
type: markdown
title: Recent Invoice History
content: >
  {% set history = state_attr('sensor.myengie_invoice_history', 'history') %}
  
  | Date | Amount | Status | Due |
  |------|--------|--------|-----|
  {% for inv in history[:5] %}
  | {{ inv.date }} | {{ inv.amount }} RON | {{ inv.status }} | {{ inv.due_date }} |
  {% endfor %}
```

### Custom Invoice Status Card

```yaml
type: custom:stack-in-card
mode: vertical
cards:
  - type: gauge
    title: Latest Invoice
    entity: sensor.myengie_latest_invoice
    min: 0
    max: 300
    needle: true
    
  - type: button
    entity: sensor.myengie_latest_invoice
    name: View Invoice Details
    state_color: true
```

### Statistics Card

```yaml
type: custom:mini-graph-card
entities:
  - entity: sensor.myengie_invoice_count
    name: Total Invoices
hours_to_show: 168
points_per_hour: 0.25
show:
  title: true
  labels: true
```

## Conditional Actions

### Send Notification When Invoice Due in 3 Days

```yaml
automation:
  - alias: "Invoice payment due soon"
    trigger:
      - platform: template
        value_template: >
          {%- set due = as_datetime(state_attr('sensor.myengie_latest_invoice', 'due_date')) %}
          {%- set now = now() %}
          {%- set days_diff = (due - now).days %}
          {{ days_diff == 3 }}
    action:
      - service: notify.mobile_app_<device>
        data:
          title: "💳 Invoice Due in 3 Days"
          message: >
            Amount: {{ states('sensor.myengie_latest_invoice') }} RON
            Invoice: {{ state_attr('sensor.myengie_latest_invoice', 'invoice_number') }}
            Due: {{ state_attr('sensor.myengie_latest_invoice', 'due_date') }}
          data:
            tag: "invoice_alert_{{ state_attr('sensor.myengie_latest_invoice', 'invoice_number') }}"
```

### Create Persistent Notification on Pending Payment

```yaml
automation:
  - alias: "Pending payment notification"
    trigger:
      - platform: numeric_state
        entity_id: sensor.myengie_pending_payments
        above: 0
    action:
      - service: persistent_notification.create
        data:
          title: "⚠️ ENGIE Pending Payment"
          message: >
            You have {{ state_attr('sensor.myengie_invoice_history', 'pending_count') }} pending invoices
            Total: {{ states('sensor.myengie_pending_payments') }} RON
          notification_id: "engie_pending"
```

### Log Invoice Changes

```yaml
automation:
  - alias: "Log invoice updates"
    trigger:
      - platform: state
        entity_id: sensor.myengie_invoice_count
    action:
      - service: logger.log
        data:
          level: INFO
          message: >
            Invoice count changed to {{ trigger.to_state.state }}.
            Latest: {{ states('sensor.myengie_latest_invoice') }} RON
            Average: {{ state_attr('sensor.myengie_invoice_history', 'average_amount') }} RON
```

## Script Examples

### Check Current Balance and Pending

```yaml
script:
  check_engie_status:
    sequence:
      - service: persistent_notification.create
        data:
          title: "MyEngie Status Report"
          message: >
            **Account Balance:** {{ states('sensor.myengie_balance') }} RON
            **Account Status:** {{ states('sensor.myengie_account_status') }}
            **Latest Invoice:** {{ states('sensor.myengie_latest_invoice') }} RON ({{ state_attr('sensor.myengie_latest_invoice', 'status') }})
            **Pending Payments:** {{ states('sensor.myengie_pending_payments') }} RON
            **Total Invoices:** {{ states('sensor.myengie_invoice_count') }}
            **Avg Invoice:** {{ state_attr('sensor.myengie_invoice_history', 'average_amount') }} RON
```

### Generate Monthly Report

```yaml
script:
  generate_monthly_report:
    sequence:
      - variables:
          latest_amount: "{{ states('sensor.myengie_latest_invoice') | float(0) }}"
          average_amount: "{{ state_attr('sensor.myengie_invoice_history', 'average_amount') | float(0) }}"
          total_paid: "{{ state_attr('sensor.myengie_invoice_history', 'paid_count') | int(0) * average_amount }}"
          
      - service: persistent_notification.create
        data:
          title: "📊 Monthly ENGIE Report"
          message: >
            **Latest Invoice:** {{ latest_amount }} RON
            **Monthly Average:** {{ average_amount }} RON
            **Estimated Total Paid:** {{ total_paid | round(2) }} RON
            **Invoice Count:** {{ states('sensor.myengie_invoice_count') }}
            **Paid:** {{ state_attr('sensor.myengie_invoice_history', 'paid_count') }}
            **Pending:** {{ state_attr('sensor.myengie_invoice_history', 'pending_count') }}
```

## Tips & Tricks

### Avoid Template Errors
Always use defaults when accessing attributes:

```yaml
# ✅ Good - Provides default
{{ state_attr('sensor.myengie_latest_invoice', 'due_date') | default('N/A') }}

# ❌ Bad - May show "None"
{{ state_attr('sensor.myengie_latest_invoice', 'due_date') }}
```

### Format Currency Values

```yaml
# Display as currency
{{ states('sensor.myengie_latest_invoice') | float(0) | round(2) | string }} RON

# In currency format
{{ "%.2f"|format(states('sensor.myengie_latest_invoice') | float(0)) }} RON
```

### Date Calculations

```yaml
# Days until due
{% set due = as_datetime(state_attr('sensor.myengie_latest_invoice', 'due_date')) %}
{{ (due - now()).days }} days

# Formatted date
{{ as_datetime(state_attr('sensor.myengie_latest_invoice', 'due_date')).strftime('%d %b %Y') }}
```

### Array Iteration

```yaml
# Get latest 3 invoices
{% for inv in state_attr('sensor.myengie_invoice_history', 'history')[:3] %}
  - {{ inv.date }}: {{ inv.amount }} RON
{% endfor %}
```

## Stability Notes

✅ Sensors update every hour automatically
✅ Data is cached between updates
✅ Templates are evaluated each HA cycle
✅ No performance impact from templates
✅ Safe to use in high-frequency automations
