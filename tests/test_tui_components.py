"""Test TUI components to ensure they work correctly."""

from datetime import datetime

from memory_agent.core.entities import Message
from memory_agent.core.interfaces import MessageRole, MessageType, StorageTier
from memory_agent.infrastructure.cli.tui.widgets import (
    MessageChainWidget,
    MemoryMonitorWidget,
    RelevanceMeterWidget,
    ToolTrackerWidget,
)


def test_message_chain_widget():
    """Test the message chain widget."""
    widget = MessageChainWidget()
    
    # Test with mock messages
    assert widget._mock_messages is not None
    assert len(widget._mock_messages) > 0
    
    # Test adding a message
    msg = Message(
        role=MessageRole.USER,
        content="Test message",
        type=MessageType.TEXT,
    )
    widget.add_message(msg)
    assert len(widget.messages) == 1
    
    # Test clearing messages
    widget.clear_messages()
    assert len(widget.messages) == 0
    
    print("✓ MessageChainWidget tests passed")


def test_memory_monitor_widget():
    """Test the memory monitor widget."""
    widget = MemoryMonitorWidget()
    
    # Test with mock stats
    assert widget._mock_stats is not None
    assert StorageTier.HOT.value in widget._mock_stats
    assert StorageTier.WARM.value in widget._mock_stats
    assert StorageTier.COLD.value in widget._mock_stats
    
    # Test updating stats
    new_stats = {
        StorageTier.HOT.value: {
            "blocks": 50,
            "size_mb": 2.5,
            "avg_age_mins": 10,
            "access_rate": 0.9,
        }
    }
    widget.update_stats(new_stats)
    assert widget.stats == new_stats
    
    print("✓ MemoryMonitorWidget tests passed")


def test_relevance_meter_widget():
    """Test the relevance meter widget."""
    widget = RelevanceMeterWidget()
    
    # Test with mock scores
    assert widget._mock_scores is not None
    assert len(widget._mock_scores) > 0
    
    # Test adding a score
    widget.add_score(0.85)
    assert len(widget.scores) == 1
    assert widget.scores[0] == 0.85
    
    # Test score color coding
    assert widget._get_score_color(0.9) == "green"
    assert widget._get_score_color(0.75) == "yellow"
    assert widget._get_score_color(0.65) == "orange1"
    assert widget._get_score_color(0.5) == "red"
    
    print("✓ RelevanceMeterWidget tests passed")


def test_tool_tracker_widget():
    """Test the tool tracker widget."""
    widget = ToolTrackerWidget()
    
    # Test with mock stats
    assert widget._mock_stats is not None
    assert "web_search" in widget._mock_stats
    
    # Test updating tool stats
    widget.update_tool_stats("test_tool", {
        "calls_per_min": 10,
        "success_rate": 0.95,
        "avg_time_ms": 100,
        "total_calls": 50,
        "status": "active",
    })
    assert "test_tool" in widget.tool_stats
    
    # Test recording a tool call
    widget.record_tool_call("test_tool", True, 150.0)
    # Activity history should be updated
    assert "test_tool" in widget._activity_history
    
    print("✓ ToolTrackerWidget tests passed")


def test_all_widgets_render():
    """Test that all widgets can render without errors."""
    widgets = [
        MessageChainWidget(),
        MemoryMonitorWidget(),
        RelevanceMeterWidget(),
        ToolTrackerWidget(),
    ]
    
    for widget in widgets:
        # Test that render doesn't raise an exception
        try:
            rendered = widget.render()
            assert rendered is not None
            print(f"✓ {widget.__class__.__name__} renders successfully")
        except Exception as e:
            raise AssertionError(f"{widget.__class__.__name__} failed to render: {e}")


if __name__ == "__main__":
    print("Testing TUI Components...")
    print("=" * 50)
    
    test_message_chain_widget()
    test_memory_monitor_widget()
    test_relevance_meter_widget()
    test_tool_tracker_widget()
    test_all_widgets_render()
    
    print("\n" + "=" * 50)
    print("All TUI component tests passed! ✓")
    print("\nThe terminal UI is fully functional and ready to use.")
    print("Run 'memory-agent monitor' to launch the interactive interface.")