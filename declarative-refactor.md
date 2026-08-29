# Flet declarative refactor

**Question:** how hard would it be to convert the UI from imperative Flet to the
declarative (`@ft.component` / `ft.use_state`) style introduced in 0.80?

## Verdict

Not worth a full rewrite. Big job, low payoff for an app that already works.

## Numbers

~10k LOC in uv_forger/. Split:

- Untouched by conversion (~2.5k): core/*, uv_handler, git_handler, filesystem_handler,
project_builder. Pure logic, no Flet.
- Full rewrite (~5k): ui/components.py 874, ui/dialogs.py 3228, content_dialogs 262,
tree_builder 283, custom_dropdown 341.
- Heavy rework (~1.5–2k of 3.8k handler lines): every self.controls.X.value = ... +
page.update() becomes state write. build_handlers.py (64 controls refs),
input_handlers, option_handlers worst.
- Test blast radius: Controls class, page.controls_ref, attach_handlers() all vanish.
tests/handlers/* + tests/ui/test_dialogs.py mostly rewritten — ~150 of 776 tests.

## Blockers

1. ~~On flet 0.82.2. ft.use_dialog() and ft.Router land in 0.85. Without use_dialog,
    converting dialogs.py (the largest file) has no good declarative story. Upgrade
    first, non-negotiable.~~ **RESOLVED** — on 0.86.5 as of 2026-08-28, see below.
2. Nested-observable gotcha. AppState is flat dataclass — good, @ft.observable on it
    works. But state.settings is nested AppSettings; components reading state.settings.x
    won't re-render. Also reset() uses setattr loop — fires N notifies, and set/list/dict
    fields (dev_packages, folders, file_overrides) need reassignment not in-place mutation
    to notify.
3. custom_dropdown.py (341 lines, hand-rolled overlay) — declarative rewrite of
    imperative overlay control is its own project.

## What I'd do instead

### Incremental, stop anytime:

1. ✅ **DONE** — Upgrade flet — see Upgrade hazards below. Verify app still runs. Value even
    standalone (6.7× diffing, smarter .update()).
2. ✅ **DONE** — @ft.observable on AppState. Imperative code keeps working.
3. ⏸ **PAUSED** — Convert one leaf panel — packages display. _update_package_display() is
    textbook: rebuild whole .controls list from state.packages every time. That's already
    declarative thinking with manual plumbing. ~50 lines out, component in.
    Paused on 2026-08-28 to fix the file editor first — see "Current position" below.
4. Judge from there. If step 3 doesn't clearly beat the current code, stop — the
    lesson was cheap.

## Current position (2026-08-28)

### Done

**Step 1 — Flet upgrade.** Merged to main as `3eca4c8` + `1d01b13`. Flet 0.82.2 → 0.86.5,
flet-code-editor → 0.86.5, fce-enhanced 0.1.5 → 0.1.6. Details in "Upgrade hazards" below.

**Step 2 — observable AppState.** Branch `feat/observable-appstate` @ `6c510ae`, pushed, **not
yet merged**. `@ft.observable` on AppState plus three consequences that had to be handled:

- Flet wraps `list`/`dict` fields, so in-place mutation notifies. **Sets are not wrapped** —
  `|=`, `.add()`, `.discard()` are silent. The `dev_packages` handlers now rebind instead.
- `dataclasses.asdict()` raises `TypeError` on the wrappers (their constructors need
  `(owner, field)`), which broke saving presets and history built from live state. Added
  `models.to_plain()` at that boundary. `json.dumps` was never affected.
- `reset()` assigned a throwaway instance's collections, which stay owned by *that* instance —
  post-reset mutations notified a discarded object. Would have silently frozen the UI after
  every Reset. `reset()` now copies through `to_plain()`.

12 tests in `tests/core/test_state_observable.py` pin this contract. 774 tests pass, ruff
clean, manually verified by creating and saving a project.

### Blocked

**The file editor is broken.** Clicking Edit raises:

```text
AttributeError: 'bool' object has no attribute 'clear'
  flet/controls/object_patch.py:1641  dst_dirty.clear()
```

fce-enhanced 0.1.6's `EnhancedCodeEditor(ft.Column)` sets `self._dirty: bool = False`, which
overwrites Flet's reserved `BaseControl._dirty: dict` (a field since the 0.83 Prop work). The
next `page.update()` on the mounted tree explodes. Reproduces in 12 lines: any `ft.Column`
subclass that assigns `self._dirty = False`.

This was introduced by the step 1 upgrade — the editor worked on 0.82.2, which had no `_dirty`.
It survived upgrade verification because constructing the view headlessly never triggers a
`page.update()` on a mounted tree.

### Chosen fix: extend EditorHandle upstream

fce-enhanced 0.2.1 (the declarative rewrite) has no such collision and **is now published to
PyPI**. But uv-forger cannot simply upgrade: 0.2.x makes `EnhancedCodeEditor` an
`@ft.component` function, and uv-forger drives it through **15 private members** that no longer
exist — 10 of them from `_handle_editor_keyboard` in `build_handlers.py:655`.

Decision (2026-08-28): fix the layering in fce-enhanced rather than hunt for new privates.
Full spec: `HANDOFF-editor-handle.md` in `~/Projects/flet-fce-enhanced`.

Order of work:

1. fce-enhanced: extend `EditorHandle` with the missing actions + `search_open`, add a way to
   set a save target without loading from disk, answer the syntax-highlight question. Release
   0.2.2.
2. uv-forger: bump to `fce-enhanced>=0.2.2`; rewrite `create_file_editor_view`
   (`ui/dialogs.py:2843`, ~70 lines) and `_handle_editor_keyboard`
   (`handlers/build_handlers.py:655`, ~50 lines) against the handle; fix 8 assertions across 4
   tests in `tests/handlers/test_file_editor.py` that poke `_current_path` / `_title_bar`.
3. Manually verify initial syntax highlighting — the current workaround (poking
   `editor._code_editor.language`) cannot come along.
4. Then resume step 3.

Rejected alternative, still viable if the above stalls: patch the 0.1.x line — branch from the
`v0.1.6` tag, rename `self._dirty` → `self._is_dirty` (13 uses), release 0.1.7. Editor works
again with zero uv-forger changes, but keeps a superseded line alive.

### Dependency state

`flet==0.86.5`, `flet-code-editor==0.86.5` (exact pins, must move together),
`fce-enhanced>=0.1.6` (**not** yet moved to 0.2.x).

Folders display (folder_handlers.py, 1112 lines, 18 .update() calls) is the real prize
but also the hairiest — recursive tree + selection paths. Do it third, not first.

skipped: full port, dialog conversion, router. add when the step-3 panel feels better
than what it replaced (the upgrade half of this is now done — see below).

## Upgrade hazards (0.82.2 → 0.86.5) — DONE 2026-08-28

Step 1 is complete. Flet 0.82.2 → 0.86.5, flet-code-editor 0.82.2 → 0.86.5, fce-enhanced
0.1.5 → 0.1.6. 762 tests pass, ruff clean, app launches on flet-desktop-full-0.86.5, all 17
dialog factories construct. Both hazards below hit exactly as predicted and are fixed.
Kept for the record.

### 1. flet-code-editor pins flet exactly — this is what kept the app on 0.82

`flet-code-editor==0.82.2` declares `flet==0.82.2`. Not `>=`. An exact pin, so
`uv add 'flet>=0.85'` fails to resolve. Upgrade lockstep:

```bash
uv add 'flet==0.86.5' 'flet-code-editor==0.86.5' 'fce-enhanced>=0.1.6'
```

`fce-enhanced` 0.1.6 is loose (`flet>=0.81.0`) so it follows along; it also dropped the
`ruff` dependency 0.1.5 carried. Every future flet bump needs the code-editor bumped in
the same command — this is recorded in the CLAUDE.md dependency notes.

### 2. Removed module-level padding/margin/border helpers (0.85.0 breaking)

`ft.padding.*`, `ft.margin.*`, `ft.border.*`, `ft.border_radius.*` were deprecated through
0.84 and deleted in 0.85.0. Three sites, all in `ui/dialogs.py`:

- `1483: content_padding=ft.padding.symmetric(...)` → `ft.Padding.symmetric(...)`
- `2979: border=ft.border.all(1, ...)` → `ft.Border.all(1, ...)`
- `2980: margin=ft.margin.only(bottom=12)` → `ft.Margin.only(bottom=12)`

Only the lowercase module-level helpers died; the capitalised class methods
(`Padding.symmetric`, `Border.all`, `Margin.only`, …) all survive and take keyword-only
args. 30-second fix — but it's an AttributeError at dialog-open time, not import time, so tests
that don't build those dialogs won't catch it.

### Non-hazards (checked, clear)

- `auto_scroll` (dialogs.py:1699, log viewer) already sets `scroll=ft.ScrollMode.AUTO`
  alongside it. 0.85 turned the missing-`scroll` case into a visible error; no change needed.
- No `DragTarget`, no `Video` — the 0.88 deprecations don't touch this app.
- Packaging changes (CPython 3.14 default, `.pyc` compile, read-only bundle + working dir
  moved) only apply to `flet build`/`flet pack`. The app ships via `uv run uv-forger`, so no
  impact — but note it before ever packaging: `boilerplate_resolver` and
  `template_loader` read files relative to `__file__`, which is read-only-bundle-safe for
  reads, and settings already go through platformdirs. Writes would be the problem, and
  there are none.
