"""Main Textual application for memory agent monitoring."""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Label,
    Sparkline,
    Static,
    TabbedContent,
    TabPane,
)

from memory_agent.core.entities import ConversationBlock, Message
from memory_agent.core.interfaces import MessageRole, StorageTier

from .widgets import (
    MessageChainWidget,
    MemoryMonitorWidget,
    RelevanceMeterWidget,
    ToolTrackerWidget,
)
from .screens import DebugScreen, LogScreen


class DashboardScreen(Screen):
    """Main dashboard screen."""
    
    BINDINGS = [
        Binding("d", "debug", "Debug"),
        Binding("l", "logs", "Logs"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]
    
    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header(show_clock=True)
        
        with Container(id="main-container"):
            with Horizontal(id="top-row"):
                # Left panel - Message Chain
                with Vertical(id="message-panel", classes="panel"):
                    yield Label("Message Chain", classes="panel-title")
                    yield MessageChainWidget(id="message-chain")
                
                # Right panel - Memory Tiers
                with Vertical(id="memory-panel", classes="panel"):
                    yield Label("Memory Tiers", classes="panel-title")
                    yield MemoryMonitorWidget(id="memory-monitor")
            
            with Horizontal(id="middle-row"):
                # Relevance Scores
                with Vertical(id="relevance-panel", classes="panel"):
                    yield Label("Relevance Scores", classes="panel-title")
                    yield RelevanceMeterWidget(id="relevance-meter")
                
                # Tool Activity
                with Vertical(id="tools-panel", classes="panel"):
                    yield Label("Tool Activity", classes="panel-title")
                    yield ToolTrackerWidget(id="tool-tracker")
            
            # Bottom - Corrections Log
            with Vertical(id="corrections-panel", classes="panel"):
                yield Label("Recent Corrections", classes="panel-title")
                with VerticalScroll(id="corrections-scroll"):
                    yield Static(id="corrections-log", classes="log")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the dashboard."""
        self.title = "Memory Agent Monitor"
        self.sub_title = "Real-time monitoring"
        
        # Start update workers
        self.update_stats()
        self.update_corrections()
    
    @work(exclusive=True, thread=True)
    def update_stats(self) -> None:
        """Worker to update statistics periodically."""
        while True:
            # This would connect to the actual agent
            # For now, we'll use mock data
            self.call_from_thread(self.refresh_widgets)
            asyncio.run(asyncio.sleep(1))
    
    @work(exclusive=True, thread=True)
    def update_corrections(self) -> None:
        """Worker to update corrections log."""
        while True:
            # Mock correction updates
            self.call_from_thread(self.add_correction_log, 
                                datetime.utcnow().strftime("%H:%M:%S"),
                                "Sample correction event")
            asyncio.run(asyncio.sleep(5))
    
    def refresh_widgets(self) -> None:
        """Refresh all widget data."""
        # Update each widget with new data
        message_chain = self.query_one("#message-chain", MessageChainWidget)
        message_chain.refresh_data()
        
        memory_monitor = self.query_one("#memory-monitor", MemoryMonitorWidget)
        memory_monitor.refresh_data()
        
        relevance_meter = self.query_one("#relevance-meter", RelevanceMeterWidget)
        relevance_meter.refresh_data()
        
        tool_tracker = self.query_one("#tool-tracker", ToolTrackerWidget)
        tool_tracker.refresh_data()
    
    def add_correction_log(self, timestamp: str, event: str) -> None:
        """Add an entry to the corrections log."""
        log = self.query_one("#corrections-log", Static)
        current_text = log.renderable
        if isinstance(current_text, str):
            lines = current_text.split("\n")
        else:
            lines = []
        
        # Add new entry
        lines.append(f"[cyan]{timestamp}[/cyan] {event}")
        
        # Keep only last 10 entries
        if len(lines) > 10:
            lines = lines[-10:]
        
        log.update("\n".join(lines))
    
    def action_debug(self) -> None:
        """Switch to debug screen."""
        self.app.push_screen(DebugScreen())
    
    def action_logs(self) -> None:
        """Switch to logs screen."""
        self.app.push_screen(LogScreen())
    
    def action_refresh(self) -> None:
        """Manual refresh."""
        self.refresh_widgets()


class MemoryAgentTUI(App):
    """Memory Agent Terminal UI Application."""
    
    CSS = """
    #main-container {
        layout: vertical;
        height: 100%;
    }
    
    #top-row, #middle-row {
        layout: horizontal;
        height: 40%;
    }
    
    #corrections-panel {
        height: 20%;
        border: solid green;
    }
    
    .panel {
        border: solid blue;
        margin: 1;
        padding: 1;
    }
    
    .panel-title {
        text-style: bold;
        color: cyan;
        margin-bottom: 1;
    }
    
    #message-panel, #memory-panel {
        width: 50%;
    }
    
    #relevance-panel, #tools-panel {
        width: 50%;
    }
    
    .log {
        scrollbar-gutter: stable;
    }
    
    MessageChainWidget {
        height: 100%;
    }
    
    MemoryMonitorWidget {
        height: 100%;
    }
    
    RelevanceMeterWidget {
        height: 100%;
    }
    
    ToolTrackerWidget {
        height: 100%;
    }
    """
    
    TITLE = "Memory Agent Monitor"
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
    ]
    
    def __init__(self, agent_url: Optional[str] = None):
        """Initialize the TUI app.
        
        Args:
            agent_url: URL to connect to the memory agent API
        """
        super().__init__()
        self.agent_url = agent_url or "http://localhost:8000"
        self.dark = True
    
    def on_mount(self) -> None:
        """Set up the application."""
        self.push_screen(DashboardScreen())


def run_tui(agent_url: Optional[str] = None):
    """Run the terminal UI application."""
    app = MemoryAgentTUI(agent_url)
    app.run()