# Cync LAN Home Assistant Add-on Repository

[![Open your Home Assistant instance and show the add add-on repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fadmin%2Fcync-lan-hass-addon)

## Add-ons

### [Cync LAN](./cync-lan)

Local-network control for Cync/GE smart lighting devices — no cloud required.

Wraps [baudneo/cync-lan](https://github.com/baudneo/cync-lan) as a Home Assistant Supervisor add-on.

**Features:**
- Accepts Cync device connections on port 23779 (TCP/SSL)
- Publishes device state via MQTT with Home Assistant auto-discovery
- Exposes a FastAPI device-export UI via HA ingress (port 23778)
- Generates and persists its own self-signed TLS certificate

See the [add-on documentation](./cync-lan/DOCS.md) for setup instructions.

## Installation

1. Click the badge above, or manually add this repository URL in **Settings → Add-ons → Add-on Store → ⋮ → Repositories**:
   ```
   https://github.com/admin/cync-lan-hass-addon
   ```
2. Find **Cync LAN** in the store and install it.
3. Configure MQTT settings and start the add-on.
4. Follow the DNS redirect instructions in the add-on documentation.
