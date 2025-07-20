"""Demo script to show TUI screenshots and functionality."""

from memory_agent.infrastructure.cli.tui import MemoryAgentTUI

# Note: This is for demonstration purposes
# In real usage, run: memory-agent monitor

def capture_tui_info():
    """Capture TUI layout information."""
    
    print("Terminal UI Features:")
    print("=" * 50)
    print()
    print("1. MESSAGE CHAIN PANEL:")
    print("   - Shows conversation flow in real-time")
    print("   - Color-coded by role (User, Assistant, Tool)")
    print("   - Displays tool calls and results")
    print()
    print("2. MEMORY TIERS PANEL:")
    print("   - HOT: Active memory (Redis)")
    print("   - WARM: Compressed recent (PostgreSQL)")
    print("   - COLD: Archive (S3/MinIO)")
    print("   - Shows block counts, sizes, and access rates")
    print()
    print("3. RELEVANCE SCORES PANEL:")
    print("   - Real-time relevance score graph")
    print("   - Average, min/max statistics")
    print("   - Decision indicators (✓/✗)")
    print("   - Trend analysis")
    print()
    print("4. TOOL ACTIVITY PANEL:")
    print("   - Live tool execution monitoring")
    print("   - Call rates per minute")
    print("   - Success rates")
    print("   - Average execution times")
    print()
    print("5. CORRECTIONS LOG:")
    print("   - Recent self-corrections")
    print("   - Timestamps and reasons")
    print()
    print("KEYBOARD SHORTCUTS:")
    print("   D - Debug screen")
    print("   L - Logs screen")
    print("   R - Refresh")
    print("   Q - Quit")
    print()
    print("To run: memory-agent monitor")
    

if __name__ == "__main__":
    capture_tui_info()