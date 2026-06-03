# ai_dc2 Python Web Bridge

This Django service runs inside the ai_dc2 repository and connects to the BWAPI DLL bridge.

## Ports
- Event input from DLL: `127.0.0.1:37000` (UDP)
- Action output to DLL: `127.0.0.1:37001` (UDP)

## Setup
1. Create and activate a Python virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Run server:
   - `python manage.py runserver 127.0.0.1:8000`

## API
- `GET /api/health`
- `GET /api/state`
- `POST /api/actions/send`
- `POST /api/runtime/start` with body `{ "strategy_unit": "auto|ProtossStrategy|TerranStrategy|ZergStrategy" }`
- `POST /api/runtime/stop`
- `GET /api/runtime/status`

## Strategy Structure
- `strategy/selector.py`: selects strategy unit by name (auto or forced)
- `strategy/banana_brain_strategy_units.py`: all strategy units in one file (`ProtossStrategy`, `TerranStrategy`, `ZergStrategy`)
- `strategy/base.py`: shared context, decision model, helper functions

## Notes
- The runtime receives DLL events and can automatically publish actions back.
- Manual action POST supports both a single object and array payload.
- The policy runtime now mirrors BananaBrain style: race-specific strategy files plus selector-based execution.

## Execution Split
- Python owns decisions: strategy selection, opening selection, mode selection, worker cap, worker gather/return, and worker training requests.
- DLL owns execution: it reads game state, forwards events to Python, and executes the commands Python sends back.
- The DLL should not decide economy or strategy on its own; if new behavior is added, it should enter through Python first.
- If a command can be expressed as a Python decision, prefer adding it to `strategy_runtime.py` instead of hardcoding it in C++.

## Progress Notes (2026-05-28)
- Added `strategy/` folder strategy architecture similar to BananaBrain split:
   - `protoss_strategy.py`, `terran_strategy.py`, `zerg_strategy.py`, `selector.py`, `base.py`.
- Runtime now supports strategy selection at start:
   - `POST /api/runtime/start/` body `{ "strategy_unit": "auto|ProtossStrategy|TerranStrategy|ZergStrategy" }`.
- Added runtime endpoint aliases without trailing slash:
   - `/api/runtime/start`, `/api/runtime/stop`, `/api/runtime/status`.

## Verification Notes (2026-05-28)
- `python manage.py check` passed with no issues.
- Confirmed root cause of prior `500` was POST to no-slash URL while APPEND_SLASH was active.
- Dashboard updated to choose race strategy before starting policy.

## Progress Notes (2026-05-28, placement policy)
- Building placement decision policy moved to Python strategy layer:
   - `strategy/base.py`: placement decision field on strategy result.
   - `strategy/protoss_strategy.py`, `strategy/terran_strategy.py`, `strategy/zerg_strategy.py`: race-specific placement policy logic.
- Runtime now publishes `placement_policy` action messages derived from Python decisions.
- DLL bridge extended to consume:
   - `placement_policy` (execution-side policy intake)
   - `worker_build` (execute build command from Python-decided request).

## Progress Notes (2026-05-28, single strategy unit file)
- Consolidated strategy units from split files into one Python file:
   - `strategy/banana_brain_strategy_units.py`
- Strategy units are distinguished by BananaBrain-style names:
   - `ProtossStrategy`, `TerranStrategy`, `ZergStrategy`.
- Runtime and API accept and expose `strategy_unit` for end-to-end selection and delivery.

## Progress Notes (2026-05-28, BananaBrain parity expansion)
- Pulled additional opening/mode conditions from BananaBrain C++ source (`ProtossStrategy.cpp`, `TerranStrategy.cpp`, `ZergStrategy.cpp`) into the single Python strategy-unit file.
- Added opening-specific, supply-threshold-driven `build_requests` sequences for representative openings:
  - Protoss: `PvZ_sairdt`, `PvZ_1basespeedzeal`, `PvT_12nexus`
  - Terran: `TvZ_1raxfe`, `TvZ_fantasy`
  - Zerg: `ZvZ_9poolspire`, `ZvZ_9gas9pool`, `ZvT_3hatchmuta`
- Added additional fallback state logic for rush/gas-stolen/lost-worker branches to better align with original strategy transitions.

## Progress Notes (2026-05-28, split editable strategy files)
- Strategy logic is now split into per-strategy Python files for direct editing in Django project:
   - `strategy/protoss_strategy.py`
   - `strategy/terran_strategy.py`
   - `strategy/zerg_strategy.py`
- Shared opening/profile helpers moved to:
   - `strategy/opening_profile.py`
- Runtime selector and package exports now load split files (no combined strategy file import).

## Progress Notes (2026-05-28, opening-level file split)
- Added dynamic opening profile loader:
   - `strategy/opening_loader.py`
- Added opening package directories:
   - `strategy/openings/protoss/`
   - `strategy/openings/terran/`
   - `strategy/openings/zerg/`
- Generated one Python file per opening name so each opening can be edited individually.
- Strategy classes now merge built-in profile data with opening-file profile overrides at runtime.

## Progress Notes (2026-05-28, opening edit workflow)
- Added concrete opening profile logic examples:
   - `strategy/openings/protoss/pvz_bisu.py`
   - `strategy/openings/terran/tvz_1raxfe.py`
   - `strategy/openings/zerg/zvz_9poolspire.py`
- Added opening-module reload API for live editing:
   - `POST /api/runtime/reload-openings/`
- Dashboard now includes `Reload Openings` button to apply opening-file edits without full process restart.

## Progress Notes (2026-06-02, web selection control)
- Added runtime selection APIs for web-driven overrides:
   - `GET /api/runtime/catalog`
   - `POST /api/runtime/select`
   - `POST /api/runtime/clear`
- Added generic raw action endpoint:
   - `POST /api/actions/send`
- `GET /api/state` now includes `runtime` status payload with:
   - selected overrides, effective strategy/opening/mode, last applied frame.
- Dashboard now supports selecting and applying:
   - strategy unit override
   - opening override (race-aware)
   - mode override
   - per-kind clear and clear-all actions
- Opening catalog now reports implementation status (implemented vs template) for UI display.

## Progress Notes (2026-06-02, tab UI + strategy file apply)
- Dashboard now uses tabs:
   - `Control`
   - `Message Flow`
   - `Recent Events`
- `Message Flow` and `Recent Events` panels were moved into dedicated tabs.
- Added strategy-file selector in `Control` tab:
   - supports unit files under `strategy/` (protoss/terran/zerg strategy files)
   - supports opening files under `strategy/openings/**`
- `POST /api/runtime/select` now accepts `strategy_file` and applies matching runtime strategy/opening overrides.

## Progress Notes (2026-06-02, Python economy control)
- Worker economy control is moving out of the DLL and into Python policy runtime.
- `strategy_runtime.py` now parses `own_units` and `mineral_fields`, sends `worker_production`, and emits `worker_gather` / `worker_return` commands.
- `strategy/base.py` now tolerates the DLL's semicolon-delimited `own_units` payload.
- The DLL bridge now executes Python-issued worker commands instead of deciding worker mining locally.

## Verification Notes (2026-06-02, Python economy control)
- `python -m py_compile AI\python\web_bridge\strategy_runtime.py AI\python\web_bridge\strategy\base.py` passed.
- `msbuild ai_dc2.vcxproj /p:Configuration=Release /p:Platform=Win32 /t:Build /m` passed.
