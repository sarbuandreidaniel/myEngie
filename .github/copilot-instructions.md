# Copilot Instructions

## API Integration Testing

Any new API endpoint added to `custom_components/myengie/api.py` **must** be tested using `debug_auth.py` before being considered complete.

### Steps
1. Add the method to `MyEngieAPI` in `api.py`
2. Add a corresponding test block in `debug_auth.py` following the existing numbered pattern (e.g. `# 13. get_new_endpoint`)
3. Run the script: `/Users/andreisarbu/Code/ha-myEngie/.venv/bin/python debug_auth.py`
4. Confirm the endpoint returns `✅` and inspect the response structure
5. Use the real response structure to implement sensor parsing in `sensor.py`

### Credentials
Stored in `.env` (git-ignored). The script loads them automatically via `python-dotenv`.

---

## Translations

When adding a new key to `custom_components/myengie/translations/en.json`, **also add a matching entry** to `custom_components/myengie/translations/en.context.json`.

The context entry should be a plain-English sentence describing what the string is used for (e.g. where it appears in the UI, what it communicates to the user). This improves machine translation quality for all other languages.

### Example
```json
"entity.sensor.my_new_sensor.name": "Home Assistant sensor name showing the current value of X in unit Y"
```

If the context entry is missing, the translate workflow will still work but will print a warning.
