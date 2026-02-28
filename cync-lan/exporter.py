#!/usr/bin/env python3
"""Companion FastAPI export server for the Cync LAN HA add-on."""
import random
import string
from pathlib import Path

import requests
import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

CYNC_API_BASE = "https://api.gelighting.com/v2/"
CORP_ID       = "1007d2ad150c4000"
CONFIG_PATH   = Path("/data/cync_mesh.yaml")
TIMEOUT       = 10

app = FastAPI(title="Cync LAN Exporter", version="1.0.0")


def _random_resource() -> str:
    return "".join(random.choices(string.ascii_lowercase, k=16))


class OtpRequest(BaseModel):
    email: str


class VerifyOtpRequest(BaseModel):
    email: str
    password: str
    otp: str


def _send_otp(email: str) -> None:
    r = requests.post(
        f"{CYNC_API_BASE}two_factor/email/verifycode",
        json={"corp_id": CORP_ID, "email": email, "local_lang": "en-us"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()


def _authenticate(email: str, password: str, otp: str) -> tuple[str, str]:
    r = requests.post(
        f"{CYNC_API_BASE}user_auth/two_factor",
        json={
            "corp_id": CORP_ID,
            "email": email,
            "password": password,
            "two_factor": otp,
            "resource": _random_resource(),
        },
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    return data["access_token"], data["user_id"]


def _get_devices(token: str, user_id: str) -> list:
    r = requests.get(
        f"{CYNC_API_BASE}user/{user_id}/subscribe/devices",
        headers={"Access-Token": token},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def _get_properties(token: str, product_id: str, device_id: str) -> dict | None:
    """Returns None when the property endpoint is not available for this product (404)."""
    r = requests.get(
        f"{CYNC_API_BASE}product/{product_id}/device/{device_id}/property",
        headers={"Access-Token": token},
        timeout=TIMEOUT,
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def _mesh_to_config(meshes: list) -> dict:
    """Convert cloud mesh data to cync-lan YAML config format."""
    conf = {}
    for mesh in meshes:
        if not mesh.get("name") or "properties" not in mesh:
            continue
        if "bulbsArray" not in mesh.get("properties", {}):
            continue
        entry = {k: mesh[k] for k in ("access_key", "id", "mac") if k in mesh}
        entry["devices"] = {}
        for bulb in mesh["properties"]["bulbsArray"]:
            required = ("deviceID", "displayName", "mac", "deviceType", "wifiMac", "firmwareVersion")
            if any(k not in bulb for k in required):
                continue
            dev_id = int(str(bulb["deviceID"])[-3:])
            entry["devices"][dev_id] = {
                "name":     str(bulb["displayName"]),
                "mac":      str(bulb["mac"]),
                "wifi_mac": str(bulb["wifiMac"]),
                "type":     int(bulb["deviceType"]),
                "fw":       str(bulb["firmwareVersion"]),
            }
        conf[mesh["name"]] = entry
    return {"account data": conf}


_SETUP_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Cync LAN Setup</title>
  <style>
    body { font-family: sans-serif; max-width: 480px; margin: 40px auto; padding: 0 16px; color: #333; }
    h1 { font-size: 1.4rem; margin-bottom: 4px; }
    h2 { font-size: 1rem; color: #555; margin: 24px 0 8px; }
    input { display: block; width: 100%; box-sizing: border-box; padding: 8px; margin-bottom: 8px;
            border: 1px solid #ccc; border-radius: 4px; font-size: 0.95rem; }
    button { padding: 8px 20px; background: #03a9f4; color: #fff; border: none;
             border-radius: 4px; cursor: pointer; font-size: 0.95rem; }
    button:disabled { background: #aaa; cursor: not-allowed; }
    #result { margin-top: 20px; padding: 10px; border-radius: 4px; font-size: 0.9rem;
              white-space: pre-wrap; word-break: break-word; display: none; }
    #result.ok  { background: #e8f5e9; border: 1px solid #a5d6a7; }
    #result.err { background: #ffebee; border: 1px solid #ef9a9a; }
    hr { border: none; border-top: 1px solid #eee; margin: 24px 0; }
  </style>
</head>
<body>
  <h1>Cync LAN Device Setup</h1>
  <p>Use this page to export your Cync account devices to the add-on. Complete both steps in order.</p>

  <hr>
  <h2>Step 1 — Request OTP email</h2>
  <input id="email1" type="email" placeholder="your@email.com" autocomplete="email">
  <button id="btn1" onclick="sendOtp()">Send OTP</button>

  <hr>
  <h2>Step 2 — Verify OTP and export devices</h2>
  <input id="email2" type="email" placeholder="your@email.com" autocomplete="email">
  <input id="password" type="password" placeholder="Cync account password" autocomplete="current-password">
  <input id="otp" type="text" placeholder="OTP code from email" maxlength="8" inputmode="numeric">
  <button id="btn2" onclick="verifyOtp()">Verify &amp; Export</button>

  <div id="result"></div>

  <script>
    function showResult(msg, ok) {
      const el = document.getElementById('result');
      el.textContent = msg;
      el.className = ok ? 'ok' : 'err';
      el.style.display = 'block';
    }

    async function sendOtp() {
      const email = document.getElementById('email1').value.trim();
      if (!email) { showResult('Please enter your email address.', false); return; }
      const btn = document.getElementById('btn1');
      btn.disabled = true;
      try {
        const res = await fetch('api/send_otp_request', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({email})
        });
        const data = await res.json();
        if (res.ok) {
          showResult('OTP sent — check your email, then complete Step 2.', true);
          document.getElementById('email2').value = email;
        } else {
          showResult('Error: ' + (data.detail || JSON.stringify(data)), false);
        }
      } catch (e) {
        showResult('Request failed: ' + e, false);
      } finally {
        btn.disabled = false;
      }
    }

    async function verifyOtp() {
      const email    = document.getElementById('email2').value.trim();
      const password = document.getElementById('password').value;
      const otp      = document.getElementById('otp').value.trim();
      if (!email || !password || !otp) { showResult('Please fill in all fields.', false); return; }
      const btn = document.getElementById('btn2');
      btn.disabled = true;
      showResult('Exporting devices — this may take a few seconds...', true);
      try {
        const res = await fetch('api/verify_otp', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({email, password, otp})
        });
        const data = await res.json();
        if (res.ok) {
          showResult(data.message + '\\n\\nRestart the add-on to apply the new device list.', true);
        } else {
          showResult('Error: ' + (data.detail || JSON.stringify(data)), false);
        }
      } catch (e) {
        showResult('Request failed: ' + e, false);
      } finally {
        btn.disabled = false;
      }
    }
  </script>
</body>
</html>"""


@app.get("/setup", response_class=HTMLResponse)
async def setup_page():
    return _SETUP_HTML


@app.get("/api/healthcheck")
async def healthcheck():
    return {"status": "ok"}


@app.post("/api/send_otp_request")
async def send_otp_request(body: OtpRequest):
    try:
        _send_otp(body.email)
    except requests.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Cync cloud error: {exc}")
    return {"status": "ok", "message": "OTP sent — check your email"}


@app.post("/api/verify_otp")
async def verify_otp(body: VerifyOtpRequest):
    try:
        token, user_id = _authenticate(body.email, body.password, body.otp)
        meshes = _get_devices(token, user_id)
        for mesh in meshes:
            mesh["properties"] = _get_properties(token, mesh["product_id"], mesh["id"])
        config = _mesh_to_config(meshes)
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CONFIG_PATH.open("w") as fh:
            fh.write("# Generated by Cync LAN HA add-on exporter\n")
            fh.write(yaml.dump(config))
    except requests.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Cync cloud error: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"status": "ok", "message": "Exported to /data/cync_mesh.yaml — restart the add-on"}


@app.get("/api/devices")
async def list_devices():
    if not CONFIG_PATH.exists():
        return {"account data": {}}
    return yaml.safe_load(CONFIG_PATH.read_text()) or {}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=23778)
