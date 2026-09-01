# Contributing

Thanks for your interest in contributing! There are plenty of ways to help out — from reporting bugs to adding new project templates.

## Ways to contribute

- **Bug reports** — Open an issue with steps to reproduce, your OS, and Python version
- **Feature requests** — Open an issue describing the use case
- **New templates** — Add a UI framework or project type (mostly declarative — see [Adding a new template](guide/templates.md#adding-a-new-template))
- **New boilerplate** — Drop starter files into the boilerplate directory; no code changes needed
- **Bug fixes and features** — Fork, branch, fix, test, PR
- **Documentation** — Improvements to these docs, in-app help, or code comments

## Development setup

You'll need Python 3.12+, `uv`, and Git.

```bash
git clone https://github.com/oktl/uv-forger.git
cd uv-forger
uv run uv-forger            # Run the app
uv run pytest               # Run 781+ tests (coverage automatic)
uv run ruff check uv_forger  # Lint
uv run ruff format uv_forger # Format
```

A pre-commit hook runs Ruff automatically on commit, so you'll catch lint issues before pushing.

## Code style

- **Linter/formatter:** Ruff — rules `E`, `F`, `I`, `W`, `UP`, `B`, `SIM`
- **Imports:** Absolute `uv_forger.*` paths only (e.g., `from uv_forger.core.state import AppState`)
- **Type hints:** Use `str | None` not `Optional[str]`; `collections.abc.Callable` not `typing.Callable`
- **Models:** Dataclasses for new data structures
- **Async:** Wrap coroutines with `wrap_async()` for Flet callbacks; use `AsyncExecutor.run()` for subprocess calls

## Testing

Run the full suite before opening a PR:

```bash
uv run pytest
```

Tests live in `tests/`, mirroring the `uv_forger/` structure. `pytest-asyncio` is configured in auto mode — async test functions just work.

Add tests for any new functionality in `tests/core/`, `tests/handlers/`, or `tests/ui/`. Handler tests use `Handlers(MockPage(), MockControls(), AppState())` — no real Flet runtime needed.

## Submitting a pull request

1. Fork the repo and create a branch from `main`
2. Make your changes
3. Run `uv run pytest` — all tests must pass
4. Run `uv run ruff check uv_forger` — no lint errors
5. Open a PR with a clear description of what changed and why

Small, focused PRs are easier to review. If you're planning something significant, open an issue first so we can discuss the approach.

## Releasing

Two GitHub Actions workflows, run in order. **Never create the tag by hand** — the version bump
has to land before the tag, or `publish.yml` builds the old version and PyPI rejects it with
`400 File already exists`.

1. **Update the changelog** — add a `## [x.y.z]` section to `CHANGELOG.md` and `docs/changelog.md`, commit, push to `main`.
2. **Run the *Release* workflow** — Actions → Release, or `gh workflow run release.yml -f bump=patch` (`patch` | `minor` | `major`). It runs `uv version --bump`, commits `chore: bump version to x.y.z`, and tags `vx.y.z` **on that commit**.
3. **Cut the release** — `gh release create vx.y.z --generate-notes`. The `release: published` event triggers `publish.yml`, which builds from the tag and uploads to PyPI via trusted publishing. This step is manual because releases created by `GITHUB_TOKEN` don't trigger other workflows.
4. **Pull locally** — `git pull` to get the bump commit.

`publish.yml` guards against a mismatched tag: it fails the run if the tag doesn't equal
`uv version --short`.

## Questions?

Open a [GitHub issue](https://github.com/oktl/uv-forger/issues) — happy to help.
