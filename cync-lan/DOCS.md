# Cync LAN Add-on Documentation

## How It Works

Cync/GE smart devices normally phone home to Cync's cloud servers (`xlink.cn`).
This add-on intercepts those connections locally by:

1. **DNS redirect** — your router/DNS server resolves `xlink.cn` to your Home Assistant IP.
2. **TLS proxy** — the add-on listens on port **23779** and accepts the device's SSL connection.
   A self-signed certificate is generated on first start and stored in `/data/certs/` so it
   survives add-on updates.
3. **MQTT publish** — device state changes are published to your MQTT broker with full
   Home Assistant auto-discovery support.
4. **FastAPI export UI** — available via the HA sidebar panel (ingress on port 23778).

---

## Prerequisites

- A working **MQTT broker** accessible from Home Assistant (e.g. the Mosquitto add-on).
- Control over your **local DNS** (router, Pi-hole, AdGuard, etc.).

---

## DNS Redirect Setup

You must redirect the hostname `xlink.cn` (and ideally `*.xlink.cn`) to your
Home Assistant IP address on your local network.

### Pi-hole / AdGuard Home

Add a custom DNS record:
```
xlink.cn → <your-HA-IP>
```

### DD-WRT / OpenWrt (dnsmasq)

Add to your dnsmasq custom config:
```
address=/xlink.cn/<your-HA-IP>
```

### Windows hosts file (testing only)

```
<your-HA-IP>  xlink.cn
```

> After redirecting DNS, power-cycle your Cync devices so they re-connect to your
> local server instead of the cloud.

---

## First-Time Device Export (OTP Workflow)

Before devices will send data, you must export your device list and auth token from
the Cync cloud once. Use the FastAPI export server accessible via the sidebar panel.

> **Tip:** Click **Open Web UI** on the add-on info page to open the interactive
> Swagger API browser (FastAPI `/docs`) directly — no proxy, no auth headers needed.
> You can run all steps below from there.

1. Open the **Cync LAN** panel in your HA sidebar.
2. Navigate to `/api/send_otp_request`:
   ```
   POST /api/send_otp_request
   Content-Type: application/json

   {"email": "your@email.com"}
   ```
   This triggers Cync to send a one-time password to your email.

3. Navigate to `/api/verify_otp`:
   ```
   POST /api/verify_otp
   Content-Type: application/json

   {"email": "your@email.com", "password": "your-cync-password", "otp": "123456"}
   ```
   On success, your device list and auth token are saved to `/data/` automatically.

4. Restart the add-on. Your devices should appear in MQTT and HA within a minute.

### API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/healthcheck` | GET | Service liveness check (used by ingress) |
| `/api/send_otp_request` | POST | Trigger OTP email from Cync cloud |
| `/api/verify_otp` | POST | Submit email, password, and OTP; saves device config to `/data/cync_mesh.yaml` |
| `/api/devices` | GET | List discovered devices |

---

## MQTT Integration

Once running, the add-on publishes Home Assistant MQTT discovery messages so devices
appear automatically in HA. No manual MQTT configuration needed beyond pointing the
add-on at your broker.

Default topics (configurable via add-on options):
- Device state: `cync_lan/<device_id>/state`
- Discovery: `homeassistant/light/<device_id>/config`

---

## Configuration Reference

| Option | Default | Description |
|---|---|---|
| `mqtt_host` | `homeassistant.local` | MQTT broker hostname |
| `mqtt_port` | `1883` | MQTT broker port |
| `mqtt_user` | _(blank)_ | MQTT username (optional) |
| `mqtt_pass` | _(blank)_ | MQTT password (optional) |
| `mqtt_topic` | `cync_lan` | Root MQTT topic prefix |
| `hass_topic` | `homeassistant` | HA MQTT discovery topic prefix |
| `mqtt_conn_delay` | `10` | MQTT reconnect delay in seconds |
| `cmd_broadcasts` | `2` | Wi-Fi command broadcast count |
| `max_tcp_conn` | `8` | Max simultaneous device TCP connections |
| `tcp_whitelist` | _(blank)_ | Comma-separated IP allowlist (blank = allow all) |
| `debug` | `false` | Enable debug logging |
| `raw_debug` | `false` | Enable raw packet logging |

---

## Troubleshooting

### Devices not connecting

- Verify DNS redirect is working: `nslookup xlink.cn` should return your HA IP.
- Check that port **23779** is not blocked by a firewall on your HA host.
- Look at the add-on log for TLS handshake errors.

### MQTT messages not appearing

- Confirm the MQTT broker hostname/port is reachable from the add-on.
- Try enabling **Debug Logging** and checking the log output.
- Verify the Mosquitto (or other) broker add-on is running.

### Panel shows a blank page or error

- The FastAPI export server may still be starting. Wait 10–15 seconds and refresh.
- Check the add-on log for Python errors.
- Make sure you have completed the OTP export workflow (devices must be exported first).

### Certificate issues

- The self-signed cert is stored in `/data/certs/`. Delete `server.pem` and `server.key`
  then restart the add-on to regenerate it.
- Note: regenerating the cert requires power-cycling all Cync devices so they pick up
  the new certificate.

### Resetting completely

Stop the add-on, delete the contents of `/data/` via SSH, then restart. This clears
the cert, device list, and auth token — you will need to redo the OTP export.
