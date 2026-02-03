"""Unit tests for human_behavior module"""

import pytest
from unittest.mock import Mock, AsyncMock
from human_behavior import HumanBehavior


class TestHumanBehavior:
    """Test cases for HumanBehavior class"""

    def test_get_viewport_size_with_size(self):
        """Test getting viewport size when it exists"""
        mock_page = Mock()
        mock_page.viewport_size = {"width": 1920, "height": 1080}

        size = HumanBehavior._get_viewport_size(mock_page)

        assert size == {"width": 1920, "height": 1080}

    def test_get_viewport_size_none(self):
        """Test getting viewport size when it's None"""
        mock_page = Mock()
        mock_page.viewport_size = None

        size = HumanBehavior._get_viewport_size(mock_page)

        assert size == {"width": 1920, "height": 1080}

    @pytest.mark.asyncio
    async def test_random_delay(self):
        """Test random delay execution"""
        import time

        start = time.time()
        await HumanBehavior.random_delay(0.1, 0.2)
        elapsed = time.time() - start

        # Should be between 0.1 and 0.2 seconds (with small margin)
        assert 0.09 <= elapsed <= 0.25

    @pytest.mark.asyncio
    async def test_typing_delay(self):
        """Test typing delay execution"""
        import time

        start = time.time()
        await HumanBehavior.typing_delay()
        elapsed = time.time() - start

        # Should be between 0.05 and 0.15 seconds (with small margin)
        assert 0.04 <= elapsed <= 0.20

    @pytest.mark.asyncio
    async def test_reading_delay_short_text(self):
        """Test reading delay for short text"""
        import time

        text_length = 50  # Short text

        start = time.time()
        await HumanBehavior.reading_delay(text_length)
        elapsed = time.time() - start

        # Should be at least 1 second (minimum)
        assert elapsed >= 0.9

    @pytest.mark.asyncio
    async def test_reading_delay_long_text(self):
        """Test reading delay for long text"""
        import time

        text_length = 10000  # Very long text

        start = time.time()
        await HumanBehavior.reading_delay(text_length)
        elapsed = time.time() - start

        # Should be capped at 10 seconds (maximum)
        assert elapsed <= 10.5

    def test_bezier_curve_start(self):
        """Test bezier curve at start (t=0)"""
        result = HumanBehavior.bezier_curve(0.0)
        assert result == 0.0

    def test_bezier_curve_end(self):
        """Test bezier curve at end (t=1)"""
        result = HumanBehavior.bezier_curve(1.0)
        assert result == 1.0

    def test_bezier_curve_middle(self):
        """Test bezier curve at middle (t=0.5)"""
        result = HumanBehavior.bezier_curve(0.5)
        # Should be between 0 and 1
        assert 0.0 < result < 1.0

    @pytest.mark.asyncio
    async def test_move_mouse_human_like(self):
        """Test mouse movement with human-like behavior"""
        mock_page = Mock()
        mock_page.viewport_size = {"width": 1920, "height": 1080}
        mock_page.mouse = AsyncMock()
        mock_page.mouse.move = AsyncMock()

        target_x = 500
        target_y = 400
        steps = 10

        await HumanBehavior.move_mouse_human_like(mock_page, target_x, target_y, steps)

        # Should call mouse.move multiple times (steps + 1 for final position)
        assert mock_page.mouse.move.call_count >= steps

    @pytest.mark.asyncio
    async def test_scroll_page_human_like(self):
        """Test page scrolling with human-like behavior"""
        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock()

        scroll_distance = 300

        await HumanBehavior.scroll_page_human_like(mock_page, scroll_distance, direction="down")

        # Should call evaluate multiple times
        assert mock_page.evaluate.call_count >= 3

    @pytest.mark.asyncio
    async def test_click_with_human_behavior(self):
        """Test clicking with human-like behavior"""
        mock_page = AsyncMock()
        mock_page.viewport_size = {"width": 1920, "height": 1080}
        mock_page.mouse = AsyncMock()
        mock_page.mouse.move = AsyncMock()

        mock_element = AsyncMock()
        mock_element.scroll_into_view_if_needed = AsyncMock()
        mock_element.bounding_box = AsyncMock(
            return_value={"x": 100, "y": 100, "width": 200, "height": 50}
        )
        mock_element.click = AsyncMock()

        mock_locator = Mock()
        mock_locator.first = mock_element

        mock_page.locator = Mock(return_value=mock_locator)

        selector = "button.submit"

        await HumanBehavior.click_with_human_behavior(mock_page, selector, scroll_into_view=True)

        # Should scroll, move mouse, and click
        mock_element.scroll_into_view_if_needed.assert_called_once()
        mock_element.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_type_like_human(self):
        """Test typing like a human"""
        mock_page = Mock()

        mock_element = AsyncMock()
        mock_element.click = AsyncMock()
        mock_element.type = AsyncMock()

        mock_locator = Mock()
        mock_locator.first = mock_element

        mock_page.locator = Mock(return_value=mock_locator)

        selector = "input.text"
        text = "Hello"

        await HumanBehavior.type_like_human(mock_page, selector, text)

        # Should click and type each character
        mock_element.click.assert_called_once()
        assert mock_element.type.call_count == len(text)

    @pytest.mark.asyncio
    async def test_random_mouse_movement(self):
        """Test random mouse movements"""
        mock_page = Mock()
        mock_page.viewport_size = {"width": 1920, "height": 1080}
        mock_page.mouse = AsyncMock()
        mock_page.mouse.move = AsyncMock()

        num_movements = 3

        await HumanBehavior.random_mouse_movement(mock_page, num_movements)

        # Should make multiple mouse movements
        assert mock_page.mouse.move.call_count >= num_movements
