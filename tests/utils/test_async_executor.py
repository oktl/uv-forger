"""Test suite for async_executor.py"""

import asyncio
import time

import pytest

from uv_forger.core.async_executor import AsyncExecutor


class TestAsyncExecutorClass:
    """Tests for AsyncExecutor class methods"""

    @pytest.mark.asyncio
    async def test_run_function_no_arguments(self):
        """Test run function with no arguments"""

        def simple_func():
            return "result"

        result = await AsyncExecutor.run(simple_func)
        assert result == "result"

    @pytest.mark.asyncio
    async def test_run_function_with_positional_arguments(self):
        """Test run function with positional arguments"""

        def add_numbers(a, b, c):
            return a + b + c

        result = await AsyncExecutor.run(add_numbers, 1, 2, 3)
        assert result == 6

    @pytest.mark.asyncio
    async def test_run_function_with_keyword_arguments(self):
        """Test run function with keyword arguments"""

        def format_string(name, age, city):
            return f"{name} is {age} years old and lives in {city}"

        result = await AsyncExecutor.run(
            format_string, name="Alice", age=30, city="NYC"
        )
        expected = "Alice is 30 years old and lives in NYC"
        assert result == expected

    @pytest.mark.asyncio
    async def test_run_function_with_args_and_kwargs(self):
        """Test run function with both args and kwargs"""

        def mixed_args(a, b, multiply=1):
            return (a + b) * multiply

        result = await AsyncExecutor.run(mixed_args, 5, 3, multiply=2)
        assert result == 16

    @pytest.mark.asyncio
    async def test_blocking_function_doesnt_block_event_loop(self):
        """Test blocking function doesn't block event loop"""

        def blocking_func(duration):
            time.sleep(duration)
            return "done"

        # Start multiple blocking calls concurrently
        tasks = [
            AsyncExecutor.run(blocking_func, 0.1),
            AsyncExecutor.run(blocking_func, 0.1),
            AsyncExecutor.run(blocking_func, 0.1),
        ]
        start = time.time()
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start

        # If running concurrently in thread pool, should take ~0.1s, not 0.3s
        assert elapsed < 0.5
        assert all(r == "done" for r in results)

    @pytest.mark.asyncio
    async def test_exception_propagation(self):
        """Test exception propagation"""

        def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError) as exc_info:
            await AsyncExecutor.run(failing_func)
        assert str(exc_info.value) == "Test error"

    @pytest.mark.asyncio
    async def test_return_type_preservation(self):
        """Test return type preservation"""

        def return_dict():
            return {"key": "value", "number": 42}

        result = await AsyncExecutor.run(return_dict)
        assert isinstance(result, dict)
        assert result["key"] == "value"
        assert result["number"] == 42


class TestEdgeCases:
    """Tests for edge cases and special scenarios"""

    @pytest.mark.asyncio
    async def test_function_returning_none(self):
        """Test function returning None"""

        def return_none():
            return None

        result = await AsyncExecutor.run(return_none)
        assert result is None

    @pytest.mark.asyncio
    async def test_function_with_default_arguments(self):
        """Test function with default arguments"""

        def with_defaults(a, b=10, c=20):
            return a + b + c

        result1 = await AsyncExecutor.run(with_defaults, 5)
        result2 = await AsyncExecutor.run(with_defaults, 5, b=15)
        assert result1 == 35
        assert result2 == 40

    @pytest.mark.asyncio
    async def test_function_with_mutable_arguments(self):
        """Test function with mutable arguments"""

        def append_to_list(lst, value):
            lst.append(value)
            return lst

        test_list = [1, 2, 3]
        result = await AsyncExecutor.run(append_to_list, test_list, 4)
        assert result == [1, 2, 3, 4]

    @pytest.mark.asyncio
    async def test_explicit_empty_kwargs(self):
        """Test explicit empty kwargs"""

        def simple_add(a, b):
            return a + b

        result = await AsyncExecutor.run(simple_add, 10, 20, **{})
        assert result == 30
