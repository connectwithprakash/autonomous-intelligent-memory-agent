"""Memory monitor widget for displaying storage tier statistics."""

from typing import Dict

from rich.console import RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget

from memory_agent.core.interfaces import StorageTier


class MemoryMonitorWidget(Widget):
    """Widget for monitoring memory tier statistics."""
    
    stats: reactive[Dict[str, Dict]] = reactive({}, layout=True)
    
    def __init__(self, *args, **kwargs):
        """Initialize the widget."""
        super().__init__(*args, **kwargs)
        self._mock_stats = self._create_mock_stats()
    
    def _create_mock_stats(self) -> Dict[str, Dict]:
        """Create mock memory statistics."""
        return {
            StorageTier.HOT.value: {
                "blocks": 42,
                "size_mb": 2.1,
                "avg_age_mins": 15,
                "access_rate": 0.85,
            },
            StorageTier.WARM.value: {
                "blocks": 156,
                "size_mb": 8.4,
                "avg_age_mins": 120,
                "access_rate": 0.32,
            },
            StorageTier.COLD.value: {
                "blocks": 1024,
                "size_mb": 52.0,
                "avg_age_mins": 1440,
                "access_rate": 0.05,
            },
        }
    
    def render(self) -> RenderableType:
        """Render the memory statistics."""
        table = Table(
            title="Storage Tiers",
            show_header=True,
            header_style="bold cyan",
            expand=True,
        )
        
        # Add columns
        table.add_column("Tier", style="bold", width=8)
        table.add_column("Blocks", justify="right", width=8)
        table.add_column("Size", justify="right", width=10)
        table.add_column("Avg Age", justify="right", width=10)
        table.add_column("Access", justify="right", width=8)
        
        # Use mock stats for now
        stats = self._mock_stats if not self.stats else self.stats
        
        # Define tier colors
        tier_colors = {
            StorageTier.HOT.value: "red",
            StorageTier.WARM.value: "yellow",
            StorageTier.COLD.value: "blue",
        }
        
        # Add rows
        for tier_name, tier_stats in stats.items():
            color = tier_colors.get(tier_name, "white")
            
            # Format size
            size_mb = tier_stats.get("size_mb", 0)
            if size_mb >= 1024:
                size_str = f"{size_mb/1024:.1f}GB"
            else:
                size_str = f"{size_mb:.1f}MB"
            
            # Format age
            age_mins = tier_stats.get("avg_age_mins", 0)
            if age_mins >= 60:
                age_str = f"{age_mins//60}h {age_mins%60}m"
            else:
                age_str = f"{age_mins}m"
            
            # Format access rate
            access_rate = tier_stats.get("access_rate", 0)
            access_str = f"{access_rate:.0%}"
            
            table.add_row(
                Text(tier_name.upper(), style=f"bold {color}"),
                str(tier_stats.get("blocks", 0)),
                size_str,
                age_str,
                access_str,
            )
        
        # Add summary row
        table.add_section()
        total_blocks = sum(s.get("blocks", 0) for s in stats.values())
        total_size = sum(s.get("size_mb", 0) for s in stats.values())
        
        table.add_row(
            Text("TOTAL", style="bold green"),
            str(total_blocks),
            f"{total_size:.1f}MB",
            "",
            "",
        )
        
        # Create memory usage bar
        memory_bar = self._create_memory_bar(stats)
        
        return Panel(
            table,
            border_style="blue",
            title="Memory Statistics",
            title_align="left",
            subtitle=memory_bar,
            subtitle_align="center",
        )
    
    def _create_memory_bar(self, stats: Dict) -> str:
        """Create a visual memory usage bar."""
        total_blocks = sum(s.get("blocks", 0) for s in stats.values())
        if total_blocks == 0:
            return "No data"
        
        bar_width = 30
        bar_chars = []
        
        tier_chars = {
            StorageTier.HOT.value: "█",
            StorageTier.WARM.value: "▓",
            StorageTier.COLD.value: "░",
        }
        
        for tier_name, tier_stats in stats.items():
            blocks = tier_stats.get("blocks", 0)
            chars = int((blocks / total_blocks) * bar_width)
            char = tier_chars.get(tier_name, "·")
            bar_chars.extend([char] * chars)
        
        # Ensure we have exactly bar_width characters
        bar_chars = bar_chars[:bar_width]
        while len(bar_chars) < bar_width:
            bar_chars.append(" ")
        
        return f"[{''.join(bar_chars)}]"
    
    def refresh_data(self) -> None:
        """Refresh the memory statistics."""
        # In a real implementation, this would fetch from the agent
        # For now, we'll slightly modify mock stats
        import random
        
        for tier_stats in self._mock_stats.values():
            # Simulate some changes
            tier_stats["blocks"] += random.randint(-2, 3)
            tier_stats["blocks"] = max(0, tier_stats["blocks"])
            tier_stats["size_mb"] = tier_stats["blocks"] * 0.05
            tier_stats["access_rate"] = min(1.0, max(0.0, 
                tier_stats["access_rate"] + random.uniform(-0.05, 0.05)))
        
        self.refresh()
    
    def update_stats(self, new_stats: Dict[str, Dict]) -> None:
        """Update the memory statistics."""
        self.stats = new_stats