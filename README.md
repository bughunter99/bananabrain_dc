# Progress Notes

## 2026-05-27 - Strategy parity hook rollout (final Zerg set)

Updated scripts:
- AI/python/web_bridge/bridgeui/scripts/TvU_natural_expand.py
- AI/python/web_bridge/bridgeui/scripts/ZvP_9734.py
- AI/python/web_bridge/bridgeui/scripts/ZvU_3hatch.py
- AI/python/web_bridge/bridgeui/scripts/ZvU_9poolspeed.py
- AI/python/web_bridge/bridgeui/scripts/ZvU_ling_lurker.py
- AI/python/web_bridge/bridgeui/scripts/ZvU_muta_micro.py
- AI/python/web_bridge/bridgeui/scripts/ZvU_natural_expand.py
- AI/python/web_bridge/bridgeui/scripts/ZvU_queen_lurker.py

Pattern applied to each strategy script:
- Added CPP_OPENING constant
- Added opening trace startup via h.start_trace(...)
- Added periodic h.trace(...) opening state logging
- Added fallback condition:
  - h.enemy_offense_larger_than_defense(...)
  - h.opening_lost_too_many_workers(...)
  - mark_once("fallback_main", ...)
  - delegate_to_cpp(CPP_OPENING)
- Added opening-complete handoff to C++ main logic via delegate_to_cpp(CPP_OPENING)

Verification:
- Hook coverage scan (strategy scripts only): MISSING_STRATEGIES: 0
- Error check for all touched files: No errors found

## 2026-05-28 - Strategy selection uses opening + auto-play

Changed behavior:
- Dashboard strategy buttons no longer start the selected Python script in exclusive control mode.
- Selecting a strategy now applies the chosen C++ opening and immediately enables auto-play.
- Selecting "auto_play" only enables auto-play.

Reason:
- Exclusive script execution switched the bot into Python/manual control, which stopped the normal C++ strategy loop.
- The new path keeps the main autonomous loop active while the selected build order is executed by the bot.

Verification:
- Dashboard template diagnostics: No errors found
- Strategy button handler now calls strategy action + set_auto_play instead of script run

## 2026-05-28 - run_web_bridge.bat startup error fix

Issue:
- Web bridge server failed at startup with a SyntaxError in bridge status event emission.

Root cause:
- In AI/python/web_bridge/bridgeui/bridge.py, the payload dict in self.emit_local_event("bridge_status", ...) was missing an opening brace.

Fix:
- Restored the missing "{" in the bridge_status payload argument.

Verification:
- python manage.py runserver 127.0.0.1:8013 --noreload starts successfully.
- Django system checks report no issues.

## 2026-05-28 - PvU Forge Double Nexus build-order update

Changed behavior:
- Build order updated to: Natural Pylon -> Forge -> Nexus -> Cannon.
- The first Pylon is now placed near natural expansion tiles instead of default main-base placement logic.

Implementation:
- Added optional near-tile arguments to build-location lookup in script runner.
- Added `try_build_near(...)` helper for strategy scripts.
- Updated `PvU_forge_double_nexus.py` flow to gate Cannon after second Nexus starts.

Verification:
- Updated files compile cleanly via `python -m py_compile`.
- Diagnostics for modified files report no errors.

## 2026-05-28 - Strategy button execution path fix

Issue:
- Dashboard strategy buttons were applying C++ opening + auto-play only, so Python script build-order edits did not take effect.

Fix:
- In dashboard strategy click handler, non-`auto_play` selections now call `/api/scripts/<script_id>/run/`.
- `auto_play` keeps using `set_auto_play` control action.

Result:
- Selecting `PvU_forge_double_nexus` now executes the edited Python strategy script directly.

## 2026-05-28 - Current running strategy indicator

Added:
- Dashboard now shows `현재 실행 전략` under the strategy panel.
- Display updates in real time from backend `script_status` events (`started`/`stopped`).

Implementation:
- bridge state now includes `current_script_id`.
- script runner emits local `script_status` events when a script starts/stops.
- dashboard maps `script_id` to race strategy label and displays both label and id.

Verification:
- Modified backend files compile cleanly.
- Diagnostics report no errors for dashboard, bridge, and script runner.

## 2026-05-28 - PvU Forge Double Nexus idle loop fix

Issue:
- Script repeatedly attempted `Protoss Forge` placement with `build_location_result ok:false` and looked idle while training probes.

Fix:
- Forge build is now gated until at least one completed Pylon exists.
- Natural Pylon lookup now retries with interval and emits debug logs.
- If natural expansion tile lookup fails repeatedly, script falls back to main-base first Pylon to keep progression alive.

Verification:
- `PvU_forge_double_nexus.py` compiles cleanly.
- Diagnostics report no errors.

## 2026-05-28 - User unit command priority lock

Issue:
- User-issued unit move/attack/build commands were getting overridden quickly by script automation.

Fix:
- Added per-unit user override lock in bridge state (`user_unit_overrides`, default 10s).
- UI unit commands (`unit_move`, `unit_stop`, `unit_attack_move`, `unit_attack_unit`, `gather_unit`, `build`) now create/refresh lock for the unit.
- Strategy helper avoids selecting locked workers and skips attack orders for locked units.
- Script actions are now tagged as `origin="script"` to prevent self-locking.

Verification:
- Modified files compile cleanly.
- Diagnostics report no errors for bridge, script runner, helpers, and dashboard.
