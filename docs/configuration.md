# Configuration

MADVID reads configuration with this priority:

CLI > project configuration > global configuration > defaults

Example global configuration:

```json
{
  "defaultDuration": 20,
  "defaultStyle": "minimal",
  "defaultOrientation": "landscape",
  "voice": false
}
```

Project-level config can live at `.madvid/config.json`.
