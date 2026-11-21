# Star Citizen's local telemetry API — an unofficial field reference (4.10 and 5.0)

**Status:** unofficial notes from my testing, as of the **5.0 PTU** (file version 5.0.202.10025, changelist 13248297) and **4.10.3 LIVE** (file version 4.10.201.48085, changelist 13220821). 
The game's `Game.log` and file properties show these file versions, not the patch name: 4.10.201.x is the 4.10.3 patch.

**Tested so far:** the 4.10.3 stream and the 5.0 stream, with the example reader below, and listing the 5.0 triggerable actions. 
**Not yet tested:** triggering actions. Those parts come from the 5.0 schema and the game client's own strings.

CIG has not documented this API yet, and anything here can change with a patch. 
The schema in `sc_telemetry_v1.proto` (beside this file) is CIG's own (message and field names and numbers are exactly as the game client declares them); the comments, these notes and the example program are not.

This repository is not affiliated with or endorsed by Cloud Imperium Games. 
This repository defers to CIG's official documentation as soon as it exists. 
The notes and the `.proto` will be updated as more is discovered, and the repository will be taken down if CIG asks.

Credit where it is due: the 4.10.2 schema, the environment switch and much of the field mapping were first published by Mallachi's Star Citizen Telemetry skill for Wingman AI (`Diftic/wingman-skills`, `TELEMETRY_REPORT.md`) and ShipBit's Wingman AI (PR #521).
This writeup adds the 5.0 changes and a second set of observations.

## What it is

The game client can host a small **gRPC** server that streams your ship's and your character's state, about 14–20 times a second, to programs on the same PC. 
The 5.0 schema also declares calls to **list and trigger a set of allowlisted game actions** (listing tested, triggering untested — see below).

|           |                                                                                                         |
| --------- | ------------------------------------------------------------------------------------------------------- |
| Address   | `127.0.0.1:2942` by default (your PC only)                                                              |
| Transport | gRPC over HTTP/2, plaintext, no token, no server reflection                                             |
| Service   | `sc.game.telemetry.v1.GameTelemetryService`                                                             |
| Stream    | `TelemetryStream(TelemetryStreamRequest {})` → `stream TelemetryStreamResponse` — send an empty request |
| 5.0 only  | `ListTriggerableActions` (tested) and `TriggerGameAction` (untested) — below                            |

Frames start only after you have spawned; none in menus or while loading.
With the server running, `Game.log` shows `Service 'sc.game.telemetry.v1.GameTelemetryService' registered` (and on 5.0 `Local services server is running on 127.0.0.1:2942`); each connected program logs `Client connected`.

## Reading it yourself

The server has reflection switched off, so a gRPC tool cannot discover the API on its own: it needs `sc_telemetry_v1.proto`. 
`read_telemetry.py` (beside this file) is a small Python example that connects and prints one line for every field whose value changed. On Windows, in the folder holding both files:

```
py -m pip install grpcio grpcio-tools
py -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. sc_telemetry_v1.proto
py read_telemetry.py
```

The second line generates `sc_telemetry_v1_pb2.py` and `sc_telemetry_v1_pb2_grpc.py` from the schema; run it again whenever the `.proto` changes.
Start the script after turning the API on (below); frames begin once you have spawned, and the script says so if none arrive within 15 seconds.
Output looks like this (values made up):

```
actor.vitals.heart_rate = 61.5
events.events.0.type = GAME_EVENT_TYPE_ACTOR_ENTER_SEAT
vehicle.state.lights_enabled = True
vehicle.state.lights_enabled = (not sent: default)
```

`py read_telemetry.py --list-actions` lists the actions the game lets tools trigger (5.0 only). 
The same `.proto` works with any gRPC library or tool, for example `grpcurl` with `-import-path . -proto sc_telemetry_v1.proto`.

## Turning it on

Every setting exists in three spellings: a config key (`a.b.c`), a command-line flag (`a-b-c`) and an environment variable (`A_B_C`).

| Build       | How                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 4.10.x      | Set the Windows user environment variable `GRPC_CLIENT_SERVER_ENABLED=true` (e.g. `setx GRPC_CLIENT_SERVER_ENABLED true`), then quit the RSI Launcher completely (tray icon too) and start it again — the game inherits the variable from the launcher. The console command below does nothing on 4.10.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| 5.0.202 PTU | **On by itself in my tests of 5.0.202.10025** (changelist 13248297): with no `USER.cfg` line and no environment variable, the game started the server and the stream worked — `Game.log` shows `Local services server is running on 127.0.0.1:2942`. Whether that is this build's default or something CIG switches on from its side is not known. If it is not on for you, add the line `server.game.telemetry.enabled = 1` to `USER.cfg` in the game's channel folder (for example `…\StarCitizen\PTU\USER.cfg`; create the file if it does not exist, and make sure it is not saved as `USER.cfg.txt`) and start the game; `Game.log` then lists `[User CFG ] server.game.telemetry.enabled=true` among the startup settings. That also worked on 10025. The setting's own description: "Serve game telemetry on the local services server. Turning it on starts that server; turning it off stops it if telemetry started it." The 4.10 variable is not needed. On the earlier 5.0.202.205 I got no frames: the console command did nothing, and the `SERVER_GAME_TELEMETRY_ENABLED` environment variable never appeared in the startup settings, so it does not seem to be read. |

Other settings found in the client (descriptions are the client's own strings):

| Setting | Builds | Description |
|---|---|---|
| `grpc.client.server.enabled` | 4.10, 5.0 | "Boolean telling whether grpc services are hosted" |
| `grpc.client.server.address` | 4.10, 5.0.201 | default `127.0.0.1:2942` (replaced by `.port` in 5.0.202) |
| `grpc.client.server.port` | 5.0.202 | "Port the client-hosted gRPC server binds to, 1024 to 65535" |
| `grpc.client.server.external` | 5.0.202 | "Bind to 0.0.0.0 to accept connections from other computers, instead of 127.0.0.1 for this computer only" — the client then logs that "other computers on the network can read telemetry and trigger game actions". There is no authentication, so think twice before turning this on. |
| `server.game.telemetry.stream.interval.ms` | 4.10, 5.0 | "Per-client stream write interval in milliseconds (50 = ~20Hz). Clamped to >= 1." |
| `server.game.telemetry.test.data` | 4.10, 5.0 | "Force telemetry to use synthetic test data instead of real game state" |
| `server.game.telemetry.generate.without.clients` | 4.10, 5.0 | "Generate telemetry frames even without connected clients" |
| `server.game.telemetry.trigger.actions.enabled` | 5.0 | "Allow external clients to trigger whitelisted game actions via the telemetry RPC" |
| `server.game.telemetry.trigger.debounce.ms` | 5.0 | "Minimum interval (ms) between repeats of the same triggered action" |
| console `gt_trigger <action_id> [hold_ms]` | 5.0 | "Trigger a whitelisted telemetry game action by name" |

## What the stream carries

`TelemetryStreamResponse` has six parts: `vehicle` (3), `weapons` (4), `events` (5), `actor` (6), `force_feedback` (7) and `turret` (8). Highlights:

- **Vehicle** (`vehicle.state`): name, class, manufacturer, type; lights; doors (open/locked); the ten **warning lights** (`annunciators`: PWR, WPN, THR, SHLD, COOL, QDRV, RADR, PROX, HIT, MISL — each OFF, NOMINAL, MINOR or MAJOR, steady or flashing); flight state (landed; gear, VTOL and transformation as RETRACTED / DEPLOYING / DEPLOYED / RETRACTING); flight settings (coupled, ESP, G-safe, cruise, speed limiter, proximity assist, gravity and wind compensation, …, each with `enabled` and `active`); instruments (speed, hydrogen and quantum fuel, G-meter, boost, altitude, radar altitude, vertical speed, atmospheric density, heading); power (power plants, engines, weapons, coolers, life support, gravity generators, sensors, shield generators and emitters). **New in 5.0:** `shields` (overall `level` plus per-face values), `health`, and `master_mode` (NAVIGATION / SCM / STEALTH, plus `spooled`) — all seen in 5.0 frames (STEALTH not yet).
- **Weapons:** gimbal/HUD settings, preset index and name, each weapon (powered, ready to fire, in preset),
  countermeasures (type and count).
- **Events:** spawn, dead, enter seat, leave seat, respawn, downed.
- **Actor (you):** health, oxygen, hunger, thirst, body temperature (each current/max), heart rate, gravity, pressure, intoxication; on foot / EVA / seated; crew role; seat name; **aUEC balance**; outside temperature, radiation, breathable air.
- **Force feedback:** per-axis resistance and damping (angular and linear), gunfire, stick shaker.

## Triggering actions (5.0)

**Listing is tested; triggering is not.** On 5.0.202.10025, `ListTriggerableActions` returned **112 actions in 11 categories**: `player_emotes` 34, `spaceship_movement` 27, `seat_general` 17, `spaceship_power` 12, `spaceship_general` 11, `player` 4, `lights_controller` 3, and one each in `spaceship_docking`, `spaceship_quantum`, `spaceship_radar` and `spaceship_target_hailing`. Only one is holdable: `v_invoke_ping` (`spaceship_radar`). No `TriggerGameAction` call has been made; everything below about triggering comes from the 5.0 schema and the strings in the game client.

- `ListTriggerableActions({})` → a list of `{ action_name, category, holdable }`.
- `TriggerGameAction({ action_name, hold_ms? })` → `{ status, message }`, where status is OK, UNKNOWN_ACTION, MAP_INACTIVE, RATE_LIMITED, FAILED, HOLD_NOT_ALLOWED or FILTERED.
- From the client's own checks: the allowlist holds digital (button) actions only — it refuses "an axis/analog action"; a holdable action must respond to both press and release; names are case-sensitive; the names are the game's action-map names (a built-in test uses `v_fire_weapon_group_1` in `spaceship_movement`), the same ones as in your keybinding profile.
- Triggering presumably needs `server.game.telemetry.trigger.actions.enabled` on.

## What one 5.0 session showed (5.0.202.10025, about 8 minutes, ~9,700 frames)

- Average rate ~19 frames/s, much closer to the 20 Hz default than 4.10.
- `shields.level` runs from 0 to 1 and changes continuously (hundreds of distinct values in that session); the per-face values change with it.
- `health` read 1 (full) while seated; `master_mode` showed NAVIGATION and SCM, and `spooled` went true.
- ENTER_SEAT and LEAVE_SEAT each arrive as one event in one frame; after leaving the seat the vehicle block is gone again.
- The first frames after spawning briefly carry an `external_temperature` of −273.15 °C before the real value.

## What one 4.10.3 session showed (39 minutes, ~33,700 frames)

- Average rate ~14 frames/s (the setting's default is 20 Hz).
- Sitting in the pilot seat makes the whole vehicle block appear in one frame with an ENTER_SEAT event; leaving clears it.
- Power-on: sensors, weapons, life support, shields and engines come on over about 2 s; THR, SHLD and WPN flash MAJOR_ON and settle to NOMINAL.
- Gear moves DEPLOYED → RETRACTING → RETRACTED (about 4 s) and back the other way.
- `is_landed` follows lift-off and touchdown; PROX lights up on final approach.
- NAV mode turns the shields off and QDRV NOMINAL; SCM reverses it (4.10 has no master-mode field; 5.0 adds one).
- During a quantum jump ESP and G-safe go inactive and THR flashes MAJOR.
- Lights, coupled/decoupled and engines are each a clean flag.
- Not in 4.10's stream: ATC calls, shield level, beds, storing the ship. Force feedback and turret frames never appeared in that session.

## Decoding tips and quirks

- It is proto3: a field holding its default (false, 0, empty) is **left out** of the frame, so "missing" means false/0. Fields marked `optional` carry presence.
- `altitude` and `radar_altitude` read `3.4028235e38` (the largest float) when there is no reading.
- `external_temperature` reads −273.15 °C outside an atmosphere.
- `gravity` jitters in the seventh significant digit; use a small deadband before treating it as changed.
- The stream includes your aUEC balance and entity ids appended to ship and weapon names — keep that in mind before posting raw captures.
