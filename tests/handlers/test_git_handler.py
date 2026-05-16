"""Test suite for git_handler.py"""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from uv_forger.handlers.git_handler import (
    check_gh_authenticated,
    check_gh_available,
    finalize_git_setup,
    handle_git_init,
)


@pytest.fixture
def check_git_available():
    """Check if git is available for testing"""
    try:
        subprocess.run(["git", "--version"], capture_output=True, text=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("Git is not available - tests require git to be installed")


@pytest.fixture(autouse=True)
def _isolate_hub(tmp_path):
    """Redirect bare hub repos to a temp directory so tests don't pollute
    ~/Projects/git-repos/ with leftover tmp*.git directories."""
    hub_dir = tmp_path / "git-repos"
    hub_dir.mkdir()
    with patch("uv_forger.handlers.git_handler.DEFAULT_GIT_HUB_ROOT", hub_dir):
        yield


class TestHandleGitInit:
    """Tests for handle_git_init function"""

    def test_initialize_git_repository(self, check_git_available):
        """Test initialize git repository when use_git=True"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            handle_git_init(project_path, use_git=True)

            git_dir = project_path / ".git"
            assert git_dir.exists()
            assert git_dir.is_dir()

    def test_dont_reinitialize_existing_repo(self, check_git_available):
        """Test don't reinitialize if .git already exists"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Initialize git first
            subprocess.run(
                ["git", "init"], cwd=project_path, capture_output=True, check=True
            )

            # Create a test file in .git to verify it's not overwritten
            test_file = project_path / ".git" / "test_marker.txt"
            test_file.write_text("existing")

            # Call handle_git_init
            handle_git_init(project_path, use_git=True)

            # Check that our marker file still exists
            assert test_file.exists()
            assert test_file.read_text() == "existing"

    def test_remove_git_repository(self, check_git_available):
        """Test remove .git directory when use_git=False"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Initialize git first
            subprocess.run(
                ["git", "init"], cwd=project_path, capture_output=True, check=True
            )

            # Verify .git exists
            git_dir = project_path / ".git"
            assert git_dir.exists()

            # Remove git
            handle_git_init(project_path, use_git=False)

            # Check that .git was removed
            assert not git_dir.exists()

    def test_handle_removing_nonexistent_git(self, check_git_available):
        """Test handle removing non-existent .git"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            # Call with use_git=False when no .git exists
            # Should complete without error
            handle_git_init(project_path, use_git=False)

    def test_git_commands_work_correctly(self, check_git_available):
        """Test verify git commands work correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            handle_git_init(project_path, use_git=True)

            # Check for typical git files/dirs
            git_dir = project_path / ".git"
            config_file = git_dir / "config"
            head_file = git_dir / "HEAD"

            assert git_dir.exists()
            assert config_file.exists()
            assert head_file.exists()

    def test_function_signature(self, check_git_available):
        """Test function signature and error handling"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            # This should work normally - verifies signature is correct
            handle_git_init(project_path, use_git=True)

    def test_initial_branch_is_main(self, check_git_available):
        """Test that git init sets the initial branch to main, not master"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "testproject"
            project_path.mkdir()
            handle_git_init(project_path, use_git=True)

            head_content = (project_path / ".git" / "HEAD").read_text()
            assert "refs/heads/main" in head_content


class TestFinalizeGitSetup:
    """Tests for finalize_git_setup function"""

    def _setup_repo(self, project_path: Path, bare_path: Path) -> None:
        """Create a project repo with a bare remote and local identity configured."""
        bare_path.mkdir(parents=True)
        subprocess.run(
            ["git", "init", "--bare"], cwd=bare_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "init", "--initial-branch=main"],
            cwd=project_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "remote", "add", "origin", str(bare_path)],
            cwd=project_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "--local", "user.email", "test@test.com"],
            cwd=project_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "--local", "user.name", "Test User"],
            cwd=project_path,
            check=True,
            capture_output=True,
        )

    def test_noop_when_git_disabled(self):
        """finalize_git_setup returns immediately when use_git is False"""
        finalize_git_setup(Path("/nonexistent"), use_git=False)

    def test_creates_initial_commit_and_pushes(self, check_git_available):
        """Test that an initial commit is created and pushed to origin"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "myproject"
            project_path.mkdir()
            bare_path = Path(tmpdir) / "myproject.git"
            self._setup_repo(project_path, bare_path)
            (project_path / "README.md").write_text("# Hello")

            finalize_git_setup(project_path, use_git=True)

            log = subprocess.run(
                ["git", "log", "--oneline"],
                cwd=project_path,
                capture_output=True,
                text=True,
            )
            assert "Initial commit" in log.stdout

    def test_skips_commit_when_nothing_to_stage(self, check_git_available):
        """Test that no commit is made when the project directory is empty"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "myproject"
            project_path.mkdir()
            bare_path = Path(tmpdir) / "myproject.git"
            self._setup_repo(project_path, bare_path)
            # No files added — nothing to commit

            finalize_git_setup(project_path, use_git=True)

            log = subprocess.run(
                ["git", "log", "--oneline"],
                cwd=project_path,
                capture_output=True,
                text=True,
            )
            assert log.stdout.strip() == ""

    def test_raises_clear_error_when_identity_not_configured(self, check_git_available):
        """Test that a RuntimeError with helpful message is raised when git
        user.email is not set, instead of an opaque CalledProcessError"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "myproject"
            project_path.mkdir()
            bare_path = Path(tmpdir) / "myproject.git"
            self._setup_repo(project_path, bare_path)
            # Override email to empty string to simulate unconfigured identity
            subprocess.run(
                ["git", "config", "--local", "user.email", ""],
                cwd=project_path,
                check=True,
                capture_output=True,
            )
            (project_path / "README.md").write_text("# Hello")

            with pytest.raises(RuntimeError, match="Git identity not configured"):
                finalize_git_setup(project_path, use_git=True)


class TestCheckGhAvailable:
    """Tests for check_gh_available function."""

    def test_returns_true_when_gh_installed(self):
        """Returns True when gh --version succeeds."""
        with patch("uv_forger.handlers.git_handler.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["gh", "--version"], returncode=0, stdout="gh version 2.0"
            )
            assert check_gh_available() is True

    def test_returns_false_when_gh_not_installed(self):
        """Returns False when gh is not found."""
        with patch(
            "uv_forger.handlers.git_handler.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            assert check_gh_available() is False

    def test_returns_false_on_non_zero_exit(self):
        """Returns False when gh --version fails."""
        with patch(
            "uv_forger.handlers.git_handler.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "gh"),
        ):
            assert check_gh_available() is False


class TestCheckGhAuthenticated:
    """Tests for check_gh_authenticated function."""

    def test_returns_true_when_authenticated(self):
        with patch("uv_forger.handlers.git_handler.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["gh", "auth", "status"], returncode=0
            )
            assert check_gh_authenticated() is True

    def test_returns_false_when_not_authenticated(self):
        with patch(
            "uv_forger.handlers.git_handler.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "gh"),
        ):
            assert check_gh_authenticated() is False

    def test_returns_false_when_gh_not_installed(self):
        with patch(
            "uv_forger.handlers.git_handler.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            assert check_gh_authenticated() is False


class TestHandleGitInitRemoteModes:
    """Tests for handle_git_init with different git_remote_mode values."""

    def test_github_mode_no_bare_repo(self, check_git_available):
        """GitHub mode should init local repo but NOT create bare repo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "myproject"
            project_path.mkdir()
            handle_git_init(project_path, use_git=True, git_remote_mode="github")

            assert (project_path / ".git").exists()
            # No remote should be configured
            result = subprocess.run(
                ["git", "remote", "-v"],
                cwd=project_path,
                capture_output=True,
                text=True,
            )
            assert result.stdout.strip() == ""

    def test_none_mode_no_bare_repo(self, check_git_available):
        """None mode should init local repo but NOT create bare repo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "myproject"
            project_path.mkdir()
            handle_git_init(project_path, use_git=True, git_remote_mode="none")

            assert (project_path / ".git").exists()
            result = subprocess.run(
                ["git", "remote", "-v"],
                cwd=project_path,
                capture_output=True,
                text=True,
            )
            assert result.stdout.strip() == ""

    def test_local_mode_creates_bare_repo(self, check_git_available):
        """Local mode should create bare repo and set remote (default behavior)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "myproject"
            project_path.mkdir()
            hub_dir = Path(tmpdir) / "hub"
            hub_dir.mkdir()
            handle_git_init(
                project_path,
                use_git=True,
                github_root=hub_dir,
                git_remote_mode="local",
            )

            assert (project_path / ".git").exists()
            bare_path = hub_dir / "myproject.git"
            assert bare_path.exists()
            assert (bare_path / "HEAD").exists()


class TestFinalizeGitSetupRemoteModes:
    """Tests for finalize_git_setup with different git_remote_mode values."""

    def _setup_local_repo(self, project_path: Path) -> None:
        """Create a local git repo with identity configured (no remote)."""
        subprocess.run(
            ["git", "init", "--initial-branch=main"],
            cwd=project_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "--local", "user.email", "test@test.com"],
            cwd=project_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "--local", "user.name", "Test User"],
            cwd=project_path,
            check=True,
            capture_output=True,
        )

    def test_none_mode_commits_no_push(self, check_git_available):
        """None mode should commit but not push."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "myproject"
            project_path.mkdir()
            self._setup_local_repo(project_path)
            (project_path / "README.md").write_text("# Hello")

            finalize_git_setup(project_path, use_git=True, git_remote_mode="none")

            log = subprocess.run(
                ["git", "log", "--oneline"],
                cwd=project_path,
                capture_output=True,
                text=True,
            )
            assert "Initial commit" in log.stdout

    def test_github_mode_calls_gh_repo_create(self, check_git_available):
        """GitHub mode should call gh repo create after committing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "myproject"
            project_path.mkdir()
            self._setup_local_repo(project_path)
            (project_path / "README.md").write_text("# Hello")

            with patch("uv_forger.handlers.git_handler._run_git") as mock_run:
                # Let real git commands through for add/status/config/commit
                original_run = subprocess.run

                def side_effect(cmd, cwd, **kwargs):
                    if cmd[0] == "gh":
                        return subprocess.CompletedProcess(
                            args=cmd, returncode=0, stdout="repo created"
                        )
                    return original_run(
                        cmd,
                        cwd=cwd,
                        capture_output=True,
                        text=True,
                        check=kwargs.get("check", True),
                    )

                mock_run.side_effect = side_effect

                finalize_git_setup(
                    project_path,
                    use_git=True,
                    git_remote_mode="github",
                    github_username="testuser",
                    github_repo_private=True,
                )

                # Verify gh repo create was called
                gh_calls = [
                    call for call in mock_run.call_args_list if call[0][0][0] == "gh"
                ]
                assert len(gh_calls) == 1
                cmd = gh_calls[0][0][0]
                assert "gh" in cmd
                assert "repo" in cmd
                assert "create" in cmd
                assert "testuser/myproject" in cmd
                assert "--private" in cmd

    def test_github_mode_public_repo(self, check_git_available):
        """GitHub mode with private=False should pass --public."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "myproject"
            project_path.mkdir()
            self._setup_local_repo(project_path)
            (project_path / "README.md").write_text("# Hello")

            with patch("uv_forger.handlers.git_handler._run_git") as mock_run:
                original_run = subprocess.run

                def side_effect(cmd, cwd, **kwargs):
                    if cmd[0] == "gh":
                        return subprocess.CompletedProcess(
                            args=cmd, returncode=0, stdout="repo created"
                        )
                    return original_run(
                        cmd,
                        cwd=cwd,
                        capture_output=True,
                        text=True,
                        check=kwargs.get("check", True),
                    )

                mock_run.side_effect = side_effect

                finalize_git_setup(
                    project_path,
                    use_git=True,
                    git_remote_mode="github",
                    github_repo_private=False,
                )

                gh_calls = [
                    call for call in mock_run.call_args_list if call[0][0][0] == "gh"
                ]
                assert len(gh_calls) == 1
                cmd = gh_calls[0][0][0]
                assert "--public" in cmd

    def test_github_mode_empty_username(self, check_git_available):
        """GitHub mode with empty username should use just the project name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "myproject"
            project_path.mkdir()
            self._setup_local_repo(project_path)
            (project_path / "README.md").write_text("# Hello")

            with patch("uv_forger.handlers.git_handler._run_git") as mock_run:
                original_run = subprocess.run

                def side_effect(cmd, cwd, **kwargs):
                    if cmd[0] == "gh":
                        return subprocess.CompletedProcess(
                            args=cmd, returncode=0, stdout="repo created"
                        )
                    return original_run(
                        cmd,
                        cwd=cwd,
                        capture_output=True,
                        text=True,
                        check=kwargs.get("check", True),
                    )

                mock_run.side_effect = side_effect

                finalize_git_setup(
                    project_path,
                    use_git=True,
                    git_remote_mode="github",
                    github_username="",
                    github_repo_private=True,
                )

                gh_calls = [
                    call for call in mock_run.call_args_list if call[0][0][0] == "gh"
                ]
                assert len(gh_calls) == 1
                cmd = gh_calls[0][0][0]
                assert "myproject" in cmd
                # No slash means no username prefix
                assert "testuser/myproject" not in " ".join(cmd)
