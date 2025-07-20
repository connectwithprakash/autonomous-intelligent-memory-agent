"""Debug screen for detailed agent inspection."""

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Label, Static


class DebugScreen(Screen):
    """Debug screen for inspecting agent internals."""
    
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
        Binding("r", "refresh", "Refresh"),
        Binding("c", "clear", "Clear"),
    ]
    
    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header(show_clock=True)
        
        with Container(id="debug-container"):
            yield Label("Debug Console", classes="title")
            
            with Horizontal(id="debug-panels"):
                # Left panel - Message Details
                with Vertical(id="message-details", classes="panel"):
                    yield Label("Message Details", classes="panel-title")
                    yield DataTable(id="message-table")
                
                # Right panel - Block Details  
                with Vertical(id="block-details", classes="panel"):
                    yield Label("Block Details", classes="panel-title")
                    yield DataTable(id="block-table")
            
            # Bottom panel - Raw Event Log
            with Vertical(id="event-log-panel", classes="panel"):
                yield Label("Raw Event Log", classes="panel-title")
                with VerticalScroll():
                    yield Static(id="event-log", classes="log")
            
            # Control buttons
            with Horizontal(id="controls"):
                yield Button("Refresh", id="refresh-btn", variant="primary")
                yield Button("Clear Log", id="clear-btn", variant="warning")
                yield Button("Export", id="export-btn", variant="default")
                yield Button("Back", id="back-btn", variant="default")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the debug screen."""
        self.title = "Debug Console"
        self.sub_title = "Agent internals"
        
        # Initialize message table
        message_table = self.query_one("#message-table", DataTable)
        message_table.add_columns("Field", "Value")
        message_table.add_rows([
            ("ID", "msg_12345"),
            ("Role", "assistant"),
            ("Type", "text"),
            ("Content", "Sample message content..."),
            ("Timestamp", "2024-01-20 10:30:45"),
            ("Metadata", "{}"),
        ])
        
        # Initialize block table
        block_table = self.query_one("#block-table", DataTable)
        block_table.add_columns("Property", "Value")
        block_table.add_rows([
            ("Block ID", "blk_67890"),
            ("Sequence", "42"),
            ("Relevance", "0.87"),
            ("Tier", "HOT"),
            ("Access Count", "3"),
            ("Size", "1.2KB"),
        ])
        
        # Add some sample log entries
        self.add_log_entry("System initialized")
        self.add_log_entry("WebSocket connection established")
        self.add_log_entry("Evaluation started for block_12345")
    
    def add_log_entry(self, message: str) -> None:
        """Add an entry to the event log."""
        from datetime import datetime
        
        log = self.query_one("#event-log", Static)
        timestamp = datetime.utcnow().strftime("%H:%M:%S.%f")[:-3]
        
        current_text = log.renderable
        if isinstance(current_text, str):
            lines = current_text.split("\n") if current_text else []
        else:
            lines = []
        
        # Add new entry with timestamp
        lines.append(f"[dim]{timestamp}[/dim] {message}")
        
        # Keep only last 100 lines
        if len(lines) > 100:
            lines = lines[-100:]
        
        log.update("\n".join(lines))
    
    @on(Button.Pressed, "#refresh-btn")
    def action_refresh(self) -> None:
        """Refresh debug data."""
        self.add_log_entry("[cyan]Refreshing debug data...[/cyan]")
        # In real implementation, would fetch fresh data
    
    @on(Button.Pressed, "#clear-btn")
    def action_clear(self) -> None:
        """Clear the event log."""
        log = self.query_one("#event-log", Static)
        log.update("")
        self.add_log_entry("[yellow]Log cleared[/yellow]")
    
    @on(Button.Pressed, "#export-btn")
    def handle_export(self) -> None:
        """Export debug data."""
        self.add_log_entry("[green]Exporting debug data...[/green]")
        # In real implementation, would save to file
    
    @on(Button.Pressed, "#back-btn")
    def handle_back(self) -> None:
        """Go back to main screen."""
        self.app.pop_screen()