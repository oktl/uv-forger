"""Tests for PyPI name availability checker."""

import httpx
import pytest

from uv_forger.core.pypi_checker import (
    check_pypi_availability,
    extract_package_name,
    normalize_pypi_name,
    validate_package_format,
)


class TestNormalizePypiName:
    """Tests for PEP 503 name normalization."""

    def test_lowercase(self):
        assert normalize_pypi_name("MyApp") == "myapp"

    def test_underscores_to_hyphens(self):
        assert normalize_pypi_name("my_cool_app") == "my-cool-app"

    def test_dots_to_hyphens(self):
        assert normalize_pypi_name("my.app") == "my-app"

    def test_consecutive_separators_collapsed(self):
        assert normalize_pypi_name("my__app") == "my-app"

    def test_mixed_separators(self):
        assert normalize_pypi_name("My_Cool.App") == "my-cool-app"

    def test_already_normalized(self):
        assert normalize_pypi_name("simple") == "simple"

    def test_hyphens_preserved(self):
        assert normalize_pypi_name("my-app") == "my-app"


class TestCheckPypiAvailability:
    """Tests for the async PyPI availability checker."""

    @pytest.mark.asyncio
    async def test_available_returns_true(self, monkeypatch):
        """404 from PyPI means name is available."""
        mock_response = httpx.Response(
            404, request=httpx.Request("GET", "https://pypi.org")
        )

        async def mock_get(self, url, **kwargs):
            return mock_response

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
        result = await check_pypi_availability("nonexistent-package-xyz")
        assert result is True

    @pytest.mark.asyncio
    async def test_taken_returns_false(self, monkeypatch):
        """200 from PyPI means name is taken."""
        mock_response = httpx.Response(
            200, request=httpx.Request("GET", "https://pypi.org")
        )

        async def mock_get(self, url, **kwargs):
            return mock_response

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
        result = await check_pypi_availability("requests")
        assert result is False

    @pytest.mark.asyncio
    async def test_network_error_returns_none(self, monkeypatch):
        """Network errors return None."""

        async def mock_get(self, url, **kwargs):
            raise httpx.ConnectError("No internet")

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
        result = await check_pypi_availability("anything")
        assert result is None

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self, monkeypatch):
        """Timeouts return None."""

        async def mock_get(self, url, **kwargs):
            raise httpx.TimeoutException("Timed out")

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
        result = await check_pypi_availability("anything")
        assert result is None

    @pytest.mark.asyncio
    async def test_unexpected_status_returns_none(self, monkeypatch):
        """Non-200/404 status returns None."""
        mock_response = httpx.Response(
            500, request=httpx.Request("GET", "https://pypi.org")
        )

        async def mock_get(self, url, **kwargs):
            return mock_response

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
        result = await check_pypi_availability("anything")
        assert result is None

    @pytest.mark.asyncio
    async def test_normalizes_name_before_check(self, monkeypatch):
        """Should normalize the name (PEP 503) before querying."""
        captured_urls = []

        async def mock_get(self, url, **kwargs):
            captured_urls.append(str(url))
            return httpx.Response(404, request=httpx.Request("GET", str(url)))

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
        await check_pypi_availability("My_Cool_App")
        assert "my-cool-app" in captured_urls[0]


class TestExtractPackageName:
    """Tests for extracting bare package name from versioned specs."""

    def test_bare_name(self):
        assert extract_package_name("requests") == "requests"

    def test_with_version_gte(self):
        assert extract_package_name("httpx>=0.25") == "httpx"

    def test_with_extras(self):
        assert extract_package_name("django[postgres]") == "django"

    def test_with_version_ne(self):
        assert extract_package_name("my-package!=1.0") == "my-package"

    def test_with_version_eq(self):
        assert extract_package_name("pytest==8.0") == "pytest"

    def test_with_version_tilde(self):
        assert extract_package_name("flask~=2.0") == "flask"

    def test_single_char(self):
        assert extract_package_name("x") == "x"

    def test_dotted_name(self):
        assert extract_package_name("zope.interface>=5.0") == "zope.interface"


class TestValidatePackageFormat:
    """Tests for client-side package spec format validation."""

    def test_valid_simple(self):
        assert validate_package_format("valid-pkg") is None

    def test_valid_with_version(self):
        assert validate_package_format("httpx>=0.25") is None

    def test_valid_with_extras(self):
        assert validate_package_format("django[postgres]") is None

    def test_invalid_spaces(self):
        result = validate_package_format("has space")
        assert result is not None
        assert "spaces" in result

    def test_invalid_at_sign(self):
        result = validate_package_format("@invalid")
        assert result is not None
        assert "Invalid" in result

    def test_valid_single_char(self):
        assert validate_package_format("x") is None

    def test_valid_underscored(self):
        assert validate_package_format("my_package") is None
