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
3. ✅ **DONE** — Convert one leaf panel — packages display. `PackagesPanel` is now an
    `@ft.component`; `_update_package_display()` no longer builds controls. Landed with
    **no** components mode and no update scheduler — see "Step 3" below for how, and for
    the subscription rule that made it possible.
4. ✅ **DONE** — Folders display converted too, same pattern, no new machinery.
    See "Step 4" below. Stopping here: dialogs.py and custom_dropdown.py remain
    imperative and there is no reason to touch them.

## Current position (2026-08-28)

### Done

**Step 1 — Flet upgrade.** Merged to main as `3eca4c8` + `1d01b13`. Flet 0.82.2 → 0.86.5,
flet-code-editor → 0.86.5, fce-enhanced 0.1.5 → 0.1.6. Details in "Upgrade hazards" below.

**Step 2 — observable AppState.** Merged to main as `6c510ae` (the `feat/observable-appstate`
branch was fast-forwarded in and deleted). `@ft.observable` on AppState plus three consequences
that had to be handled:

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

### Was blocked — resolved 2026-08-28, merged to main as `e7025be`

**The file editor was broken.** Clicking Edit raised:

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

1. ✅ **DONE** — fce-enhanced: extend `EditorHandle` with the missing actions + `search_open`,
   add a way to set a save target without loading from disk, answer the syntax-highlight
   question. Released as 0.2.2, live on PyPI.
2. ✅ **DONE** — uv-forger migration. `fce-enhanced>=0.2.2`; `create_file_editor_view`
   and `_handle_editor_keyboard` rewritten against the handle; tests updated. 774 pass,
   ruff clean. Details below.
3. ✅ **DONE** — manually verified in the running app: toolbar buttons, keyboard shortcuts,
   typing, and Save round-tripping to disk (reopened the file and the edit was there). Took two
   rounds — see "Migration notes" below for the two silent failure modes that surfaced only
   under a real client. 774 tests pass.
4. Then resume step 3.

### Migration notes (2026-08-28)

The one thing the handoff spec did not cover: `EnhancedCodeEditor` is now an `@ft.component`,
so **calling it raises** `RuntimeError: No current renderer is set` outside a render pass. The
app is still imperative, so `create_file_editor_view` renders that one subtree on its own
`Renderer()`:

```python
handle = EditorHandle()
editor = Renderer().render(lambda: EnhancedCodeEditor(..., handle=handle))
```

`page.render()` was rejected — it replaces `views[0].controls` and flips the whole session into
components mode, which disables Flet's auto-update everywhere else.

Component state changes flush through the session's deferred-update scheduler, which an
imperative app never starts, so `_edit_file` calls `page.session.start_updates_scheduler()`
after pushing the view (idempotent). Components mode is deliberately *not* enabled — auto-update
stays on for the rest of the app.

**`ft.memo` is load-bearing.** First manual test: keyboard shortcuts worked, no toolbar button
did, and typing appeared to work but never reached the backend. Flet debug log:

```text
flet DEBUG Control with ID 2090 not found.
```

2090 was the `CodeEditor`; by the end of the session the live subtree was numbered 3268+. Every
imperative `page.update()` — including Flet's post-event auto-update, which fires after
*unrelated* events such as a snackbar dismissing — runs `Component.before_update()`, which
re-renders the body into brand-new controls with brand-new ids and never patches the client.
The client keeps sending the ids it was given, the backend can no longer resolve them, and
every event from inside the editor is dropped silently. Keyboard shortcuts were unaffected
because they arrive on `page.on_keyboard_event`, not on a control inside the component.

`ft.memo(EnhancedCodeEditor)(...)` makes an unchanged parent update reuse the previous render
(`_state.last_b`), so ids stay stable; state changes still re-render via `Component.update()`,
which does patch the client. This is the general rule for hosting any component inside an
imperative Flet app, not something specific to the editor. Pinned by
`test_editor_component_is_memoized`.

Note the same bug silently broke saving: with `on_change` dropped, the component's `r.text`
never advanced past the initial content, so `handle.value` would have written stale text.

**Components mode is also load-bearing** — memo alone was not enough. Second manual test: clicks
now dispatched, but a toolbar button raised

```text
CodeEditor(475) Control must be added to the page first
```

Mechanism, from `object_patch.py:605` and the reconciliation comment at 1160. When a parent
update (non-frozen) reaches a component whose `_b` was just swapped for a freshly rendered one,
`src is not dst` and there is no explicit key, so **the whole subtree diff is skipped** — the new
controls are never sent to the client and never get a `_parent`. `r.editor.current` then points
at an orphan, and the next `ctrl.focus()` dies on the `.page` property. The race is tight and
lands exactly on a click: the handler marks the component dirty and queues
`Component.update()`, then Flet's post-event auto-update fires a `page.update()` *first*, whose
`before_update()` misses the memo (dirty) and burns the render.

`ft.context.enable_components_mode()` while the editor view is open removes auto-update — its
only effect — so component state changes reach the client through `Component.update()` alone,
which patches with `frozen=True` and takes the reconciliation path that reindexes and reparents.
`close_editor()` disables it again so the imperative main window keeps auto-update.

The two fixes cover different paths and are both needed: memo keeps an *unrelated* explicit
`page.update()` from swapping a clean component's body; components mode keeps auto-update from
racing a *dirty* one.

Other changes: `save_path=user_template_path or filename` replaces the `_current_path` /
`_title_bar` pokes and the `did_mount` highlight hack; `view.editor` → `view.editor_handle`
(plus `view.editor_save_path` for tests); all 14 private calls in `_handle_editor_keyboard`
are now handle calls, all synchronous (the handle schedules coroutines via `page.run_task`).

Rejected alternative, still viable if the above stalls: patch the 0.1.x line — branch from the
`v0.1.6` tag, rename `self._dirty` → `self._is_dirty` (13 uses), release 0.1.7. Editor works
again with zero uv-forger changes, but keeps a superseded line alive.

### Step 3 — declarative packages panel (2026-08-28)

`uv_forger/ui/packages_panel.py`: `PackagesPanel` is an `@ft.component` returning the bordered
package list, rendered straight from state. `_create_package_item()` and the whole
`.controls = [...]` rebuild are gone; `_update_package_display()` is down to normalizing
always-dev packages, setting the count label, the preset button, and re-rendering the panel.
`_on_package_click(e)` became `_on_package_select(idx)`. 779 tests pass, ruff clean, and
manually verified in the running app on 2026-08-28: row select, Add Packages, Remove,
Toggle Dev, Clear All, and framework-change repopulation all functional. First try — unlike
the editor, which took two rounds.

#### The rule that makes it cheap: do not pass the observable

The migration note above said hosting a component needs `ft.memo` **and** components mode.
That is true for a component subscribed to observable state — and the reason is worth
spelling out, because it decides whether the incremental path is viable at all:

- `Component._subscribe_observable_args` subscribes to any argument that `isinstance(..., Observable)`,
  and the subscription is **whole-object** — no field-level filtering, no read tracking. Pass
  `AppState` and the panel goes dirty on every unrelated write: project name, a checkbox, a folder.
- A dirty component reached by an imperative `page.update()` goes through
  `before_update()`, which misses the memo, re-renders into fresh control ids, and **does not
  patch the client** (`component.py:170`). The client keeps sending ids the backend can no
  longer resolve. Silent.
- Components mode only removes Flet's *post-event auto-update*
  (`context.auto_update_enabled()` gates `session.after_event`). It does nothing about the
  ~30 explicit `self.page.update()` calls this app's handlers make. So for a panel that lives
  in the always-on main window, components mode is not a fix — and turning it on globally
  would mean auditing every handler for an explicit update.

So the panel takes a **getter**, `lambda: state`, not `state`. A plain callable is not
`Observable`, nothing subscribes, the component never goes dirty, and every `page.update()`
anywhere in the app takes the memo-skip path. Invalidation stays explicit:
`controls.packages_panel.update()` — the one path that re-renders *and* patches — called at the
end of `_update_package_display()`, after `page.update()`.

Net: `ft.memo` yes, components mode no, update scheduler no.

#### Other mechanics

- `render_packages_panel(state, controls)` in `components.py` does the `Renderer().render(...)`
  + `ft.memo` wrapping; extracted so the invariants are testable
  (`tests/ui/test_packages_panel.py`, 3 tests).
- The panel is built before handlers exist, so clicks dispatch through
  `controls.on_package_select`, a slot `attach_handlers()` fills in.
- `page.update()` **before** `packages_panel.update()`, not after: the memo-skip path leaves
  `_b is last_b`, so the later component patch is the only thing the client sees change.
- `controls.packages_container` is gone; six test mocks and three assertions were updated.

#### Verdict on step 4

Genuinely better, but not by much. ~55 lines of control-building replaced by ~50 lines of
component, so the win is in *where* the code is, not how much: rendering is one pure function
of state, and selection highlighting stopped being a manual per-item branch. Against that,
hosting cost is real and permanent — a getter instead of the observable, a memo wrapper, an
explicit `.update()`, and a comment block explaining why, none of which a fully declarative app
would need. The pattern is now proven and mechanical, so the folders display was worth doing
next; a full port still is not.

### Step 4 — declarative folders panel (2026-08-28)

`uv_forger/ui/folders_panel.py`: `FoldersPanel` renders the whole project-structure tree —
root files, folders, nested subfolders, selection highlight, override pencil, and both context
menus — as pure functions over state. `_create_item_container` (88 lines) and
`_process_folder_recursive` are gone from `folder_handlers.py`; `_update_folder_display()` is
down to the count label, the preset button, and a panel re-render. 781 tests pass, ruff clean,
app launches clean. **Interactive click-through unverified** — see "Left to verify".

Same hosting contract as the packages panel, no new machinery: own `Renderer`, `ft.memo`,
state as a getter, explicit `controls.folders_panel.update()` after `page.update()`. The
pattern transferred as predicted.

What was different from step 3:

- **Three callbacks, not one.** Row click, file context menu, folder context menu. Rather than
  three slots on `Controls`, the panel takes one `FolderPanelCallbacks` dataclass whose fields
  `attach_handlers` fills in. Its identity stays stable, which is what `ft.memo` compares.
- **The `data=` dicts are gone.** Rows used to carry `{"path", "type", "name"}` on the control
  so `_on_item_click(e)` could read `e.control.data`; menu items carried `{"action", ...}`.
  Closures capture those directly now, so `_on_item_click(e)` became
  `_on_item_select(path, type, name)` and the two context dispatchers take
  `(action, path, name)`. This is where most of the test churn came from — a lot of assertions
  poked at `.data`.
- **`get_canonical_file_path()` moved to `core/models.py`.** The panel needs it for the
  override pencil, and `ui/` importing from `handlers/` would have been backwards. It is a
  pure function over folder dicts, so `core` is where it belonged anyway; `folder_handlers`
  re-imports it, so the existing test imports still resolve.

Test churn: `_create_item_container` / `_process_folder_recursive` / `_on_item_click` tests
scattered across three handler test files were replaced by 19 tests in
`tests/ui/test_folders_panel.py` — flattening order, root-file placement, selection, pencil,
both menus, dispatch, unwired-callback safety, and the two hosting invariants. Net 781 tests.

### Left to verify

Interactive click-through of the folders panel: select a folder and a file (highlight + status
line + Edit File button enabling), right-click a file for all four actions, right-click a
folder for Import Folder from Disk, Add Folder/File, Remove, Import Tree (root files above
folders), Clear Folders, and a framework change that rebuilds the tree. Startup renders clean
and 781 tests pass, but this panel's failure modes are silent under test.


### Dependency state

`flet==0.86.5`, `flet-code-editor==0.86.5` (exact pins, must move together),
`fce-enhanced>=0.2.2` (moved 2026-08-28 — also drops the 0.1.6 `_dirty` collision).

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
