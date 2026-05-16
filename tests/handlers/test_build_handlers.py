"""Tests for BuildHandlersMixin helpers."""

import subprocess
from unittest.mock import Mock, patch

from uv_forger.handlers.build_handlers import BuildHandlersMixin


class TestOpenInFileManager:
    """Tests for BuildHandlersMixin._open_in_file_manager."""

    def test_macos_uses_open(self, tmp_path):
        with patch("sys.platform", "darwin"), patch("subprocess.Popen") as mock_popen:
            BuildHandlersMixin._open_in_file_manager(tmp_path)
        mock_popen.assert_called_once_with(["open", str(tmp_path)])

    def test_windows_uses_explorer(self, tmp_path):
        with patch("sys.platform", "win32"), patch("subprocess.Popen") as mock_popen:
            BuildHandlersMixin._open_in_file_manager(tmp_path)
        mock_popen.assert_called_once_with(["explorer", str(tmp_path)])

    def test_linux_uses_xdg_open(self, tmp_path):
        with patch("sys.platform", "linux"), patch("subprocess.Popen") as mock_popen:
            BuildHandlersMixin._open_in_file_manager(tmp_path)
        mock_popen.assert_called_once_with(["xdg-open", str(tmp_path)])


class TestOpenInTerminal:
    """Tests for BuildHandlersMixin._open_in_terminal."""

    def test_macos_uses_open_terminal(self, tmp_path):
        with patch("sys.platform", "darwin"), patch("subprocess.Popen") as mock_popen:
            BuildHandlersMixin._open_in_terminal(tmp_path)
        mock_popen.assert_called_once_with(["open", "-a", "Terminal", str(tmp_path)])

    def test_windows_uses_cmd(self, tmp_path):
        with (
            patch("sys.platform", "win32"),
            patch("subprocess.Popen") as mock_popen,
            patch.object(subprocess, "CREATE_NEW_CONSOLE", 16, create=True),
        ):
            BuildHandlersMixin._open_in_terminal(tmp_path)
        call_kwargs = mock_popen.call_args
        assert call_kwargs[0][0] == ["cmd"]
        assert call_kwargs[1]["cwd"] == str(tmp_path)

    def test_linux_tries_gnome_terminal_first(self, tmp_path):
        with patch("sys.platform", "linux"), patch("subprocess.Popen") as mock_popen:
            BuildHandlersMixin._open_in_terminal(tmp_path)
        # First call should be gnome-terminal
        first_call_cmd = mock_popen.call_args_list[0][0][0]
        assert first_call_cmd[0] == "gnome-terminal"

    def test_linux_falls_through_to_next_terminal_on_not_found(self, tmp_path):
        call_count = [0]

        def popen_side_effect(cmd, **kwargs):
            call_count[0] += 1
            if cmd[0] == "gnome-terminal":
                raise FileNotFoundError
            return Mock()

        with (
            patch("sys.platform", "linux"),
            patch("subprocess.Popen", side_effect=popen_side_effect),
        ):
            BuildHandlersMixin._open_in_terminal(tmp_path)

        # gnome-terminal failed, konsole succeeded
        assert call_count[0] == 2

    def test_linux_tries_all_terminals_silently_if_none_found(self, tmp_path):
        """If all terminals raise FileNotFoundError, no exception is propagated."""
        with (
            patch("sys.platform", "linux"),
            patch("subprocess.Popen", side_effect=FileNotFoundError),
        ):
            BuildHandlersMixin._open_in_terminal(tmp_path)  # should not raise


class TestRunPostBuildCommand:
    """Tests for BuildHandlersMixin._run_post_build_command."""

    def _make_mixin(self):
        """Create a minimal BuildHandlersMixin with a mock _show_snackbar."""
        mixin = BuildHandlersMixin.__new__(BuildHandlersMixin)
        mixin._show_snackbar = Mock()
        return mixin

    def test_empty_command_is_noop(self, tmp_path):
        mixin = self._make_mixin()
        with patch("uv_forger.handlers.build_handlers.subprocess.run") as mock_run:
            mixin._run_post_build_command(tmp_path, "")
        mock_run.assert_not_called()
        mixin._show_snackbar.assert_not_called()

    def test_whitespace_only_command_is_noop(self, tmp_path):
        mixin = self._make_mixin()
        with patch("uv_forger.handlers.build_handlers.subprocess.run") as mock_run:
            mixin._run_post_build_command(tmp_path, "   ")
        mock_run.assert_not_called()

    def test_successful_command(self, tmp_path):
        mixin = self._make_mixin()
        mock_result = Mock(returncode=0, stdout="ok", stderr="")
        with patch(
            "uv_forger.handlers.build_handlers.subprocess.run", return_value=mock_result
        ) as mock_run:
            mixin._run_post_build_command(tmp_path, "echo hello")
        mock_run.assert_called_once_with(
            "echo hello",
            cwd=str(tmp_path),
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        mixin._show_snackbar.assert_called_once_with("Post-build command completed")

    def test_failed_command_shows_error(self, tmp_path):
        mixin = self._make_mixin()
        mock_result = Mock(returncode=1, stdout="", stderr="bad input")
        with patch(
            "uv_forger.handlers.build_handlers.subprocess.run", return_value=mock_result
        ):
            mixin._run_post_build_command(tmp_path, "false")
        mixin._show_snackbar.assert_called_once_with(
            "Post-build command failed (exit 1)", is_error=True
        )

    def test_timeout_shows_error(self, tmp_path):
        mixin = self._make_mixin()
        with patch(
            "uv_forger.handlers.build_handlers.subprocess.run",
            side_effect=subprocess.TimeoutExpired("cmd", 30),
        ):
            mixin._run_post_build_command(tmp_path, "sleep 60")
        mixin._show_snackbar.assert_called_once_with(
            "Post-build command timed out", is_error=True
        )

    def test_unexpected_exception_shows_error(self, tmp_path):
        mixin = self._make_mixin()
        with patch(
            "uv_forger.handlers.build_handlers.subprocess.run",
            side_effect=OSError("no such file"),
        ):
            mixin._run_post_build_command(tmp_path, "nonexistent")
        mixin._show_snackbar.assert_called_once()
        call_args = mixin._show_snackbar.call_args
        assert "error" in call_args[0][0].lower() or call_args[1].get("is_error")

    def test_uses_correct_cwd(self, tmp_path):
        mixin = self._make_mixin()
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        mock_result = Mock(returncode=0, stdout="", stderr="")
        with patch(
            "uv_forger.handlers.build_handlers.subprocess.run", return_value=mock_result
        ) as mock_run:
            mixin._run_post_build_command(project_dir, "ls")
        assert mock_run.call_args[1]["cwd"] == str(project_dir)
