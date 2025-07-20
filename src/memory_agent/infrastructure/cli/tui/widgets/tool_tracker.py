"""Tool tracker widget for monitoring tool execution."""

import random
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

from rich.console import RenderableType
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget


class ToolTrackerWidget(Widget):
    """Widget for tracking tool execution statistics."""
    
    tool_stats: reactive[Dict[str, Dict]] = reactive({}, layout=True)
    
    def __init__(self, *args, **kwargs):
        """Initialize the widget."""
        super().__init__(*args, **kwargs)
        self._mock_stats = self._create_mock_stats()
        self._activity_history = defaultdict(list)
    
    def _create_mock_stats(self) -> Dict[str, Dict]:
        """Create mock tool statistics."""
        return {
            "web_search": {
                "calls_per_min": 45,
                "success_rate": 0.96,
                "avg_time_ms": 234,
                "total_calls": 1523,
                "status": "active",
            },
            "calculator": {
                "calls_per_min": 12,
                "success_rate": 1.0,
                "avg_time_ms": 15,
                "total_calls": 456,
                "status": "idle",
            },
            "mcp_server_1": {
                "calls_per_min": 23,
                "success_rate": 0.89,
                "avg_time_ms": 567,
                "total_calls": 892,
                "status": "active",
            },
            "weather_api": {
                "calls_per_min": 8,
                "success_rate": 0.94,
                "avg_time_ms": 432,
                "total_calls": 234,
                "status": "idle",
            },
        }
    
    def render(self) -> RenderableType:
        """Render the tool tracker."""
        # Use mock stats for now
        stats = self._mock_stats if not self.tool_stats else self.tool_stats
        
        if not stats:
            return Panel(
                "No tool activity yet",
                border_style="blue",
                title="Tool Activity",
            )
        
        # Create main table
        table = Table(
            show_header=True,
            header_style="bold cyan",
            expand=True,
        )
        
        table.add_column("Tool", style="bold", width=15)
        table.add_column("Activity", width=15)
        table.add_column("Rate", justify="right", width=10)
        table.add_column("Success", justify="right", width=8)
        table.add_column("Avg Time", justify="right", width=10)
        
        # Sort tools by activity
        sorted_tools = sorted(
            stats.items(),
            key=lambda x: x[1].get("calls_per_min", 0),
            reverse=True
        )
        
        for tool_name, tool_stat in sorted_tools:
            # Create activity bar
            activity_bar = self._create_activity_bar(
                tool_stat.get("calls_per_min", 0),
                max_rate=50
            )
            
            # Format rate
            rate = tool_stat.get("calls_per_min", 0)
            rate_text = f"{rate}/min"
            
            # Format success rate
            success = tool_stat.get("success_rate", 0)
            success_text = Text(f"{success:.0%}")
            if success >= 0.95:
                success_text.stylize("green")
            elif success >= 0.8:
                success_text.stylize("yellow")
            else:
                success_text.stylize("red")
            
            # Format avg time
            avg_time = tool_stat.get("avg_time_ms", 0)
            if avg_time >= 1000:
                time_text = f"{avg_time/1000:.1f}s"
            else:
                time_text = f"{avg_time}ms"
            
            # Status indicator
            status = tool_stat.get("status", "idle")
            if status == "active":
                tool_display = Text(f"● {tool_name}", style="green")
            else:
                tool_display = Text(f"○ {tool_name}", style="dim")
            
            table.add_row(
                tool_display,
                activity_bar,
                rate_text,
                success_text,
                time_text,
            )
        
        # Add summary section
        table.add_section()
        total_rate = sum(s.get("calls_per_min", 0) for s in stats.values())
        avg_success = sum(s.get("success_rate", 0) for s in stats.values()) / len(stats)
        
        table.add_row(
            Text("TOTAL", style="bold green"),
            "",
            f"{total_rate}/min",
            f"{avg_success:.0%}",
            "",
        )
        
        return Panel(
            table,
            border_style="blue",
            title="Tool Execution Monitor",
            title_align="left",
            subtitle=self._create_status_line(stats),
            subtitle_align="center",
        )
    
    def _create_activity_bar(self, rate: int, max_rate: int = 50) -> str:
        """Create a visual activity bar."""
        bar_width = 15
        filled = int((rate / max_rate) * bar_width)
        filled = min(filled, bar_width)
        
        # Choose color based on rate
        if rate >= 40:
            char = "█"
            color = "red"
        elif rate >= 20:
            char = "█"
            color = "yellow"
        elif rate >= 10:
            char = "▓"
            color = "green"
        elif rate > 0:
            char = "▒"
            color = "cyan"
        else:
            char = "░"
            color = "dim"
        
        bar = char * filled + "░" * (bar_width - filled)
        
        # Apply color styling inline
        if rate > 0:
            return f"[{color}]{bar}[/{color}]"
        else:
            return f"[dim]{bar}[/dim]"
    
    def _create_status_line(self, stats: Dict) -> str:
        """Create a status line summary."""
        active_tools = sum(1 for s in stats.values() if s.get("status") == "active")
        total_tools = len(stats)
        
        total_calls = sum(s.get("total_calls", 0) for s in stats.values())
        
        return f"Active: {active_tools}/{total_tools} | Total Calls: {total_calls:,}"
    
    def refresh_data(self) -> None:
        """Refresh the tool statistics."""
        # Simulate activity changes
        for tool_name, tool_stat in self._mock_stats.items():
            # Random activity changes
            if random.random() < 0.3:  # 30% chance of change
                old_rate = tool_stat["calls_per_min"]
                change = random.randint(-5, 8)
                new_rate = max(0, old_rate + change)
                tool_stat["calls_per_min"] = new_rate
                
                # Update status based on rate
                tool_stat["status"] = "active" if new_rate > 5 else "idle"
                
                # Slight variations in other stats
                tool_stat["success_rate"] = min(1.0, max(0.5,
                    tool_stat["success_rate"] + random.uniform(-0.02, 0.01)))
                
                # Update total calls
                if new_rate > 0:
                    tool_stat["total_calls"] += random.randint(0, 3)
        
        self.refresh()
    
    def update_tool_stats(self, tool_name: str, stats: Dict) -> None:
        """Update statistics for a specific tool."""
        new_stats = dict(self.tool_stats)
        new_stats[tool_name] = stats
        self.tool_stats = new_stats
    
    def record_tool_call(
        self,
        tool_name: str,
        success: bool,
        execution_time_ms: float
    ) -> None:
        """Record a tool call for statistics."""
        # Update activity history
        now = datetime.utcnow()
        self._activity_history[tool_name].append({
            "timestamp": now,
            "success": success,
            "time_ms": execution_time_ms,
        })
        
        # Clean old history (keep last hour)
        cutoff = now - timedelta(hours=1)
        self._activity_history[tool_name] = [
            e for e in self._activity_history[tool_name]
            if e["timestamp"] > cutoff
        ]
        
        # Calculate new statistics
        history = self._activity_history[tool_name]
        if history:
            # Calls per minute (last 5 minutes)
            recent_cutoff = now - timedelta(minutes=5)
            recent_calls = [e for e in history if e["timestamp"] > recent_cutoff]
            calls_per_min = len(recent_calls) / 5
            
            # Success rate
            success_rate = sum(1 for e in history if e["success"]) / len(history)
            
            # Average time
            avg_time_ms = sum(e["time_ms"] for e in history) / len(history)
            
            # Update stats
            self.update_tool_stats(tool_name, {
                "calls_per_min": int(calls_per_min),
                "success_rate": success_rate,
                "avg_time_ms": int(avg_time_ms),
                "total_calls": len(history),
                "status": "active" if calls_per_min > 5 else "idle",
            })