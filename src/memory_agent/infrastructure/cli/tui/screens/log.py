"""Log viewer screen for system logs."""

from datetime import datetime
from typing import List, Tuple

from rich.syntax import Syntax
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, RadioButton, RadioSet, Static


class LogScreen(Screen):
    """Screen for viewing and filtering system logs."""
    
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
        Binding("r", "refresh", "Refresh"),
        Binding("f", "focus_filter", "Filter"),
        Binding("/", "focus_search", "Search"),
    ]
    
    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header(show_clock=True)
        
        with Container(id="log-container"):
            yield Label("System Logs", classes="title")
            
            # Filter controls
            with Horizontal(id="filter-controls"):
                # Log level filter
                with Vertical(classes="filter-group"):
                    yield Label("Log Level:")
                    with RadioSet(id="level-filter"):
                        yield RadioButton("All", value=True)
                        yield RadioButton("Debug")
                        yield RadioButton("Info")
                        yield RadioButton("Warning")
                        yield RadioButton("Error")
                
                # Component filter
                with Vertical(classes="filter-group"):
                    yield Label("Component:")
                    with RadioSet(id="component-filter"):
                        yield RadioButton("All", value=True)
                        yield RadioButton("Agent")
                        yield RadioButton("Memory")
                        yield RadioButton("Evaluator")
                        yield RadioButton("Tools")
                
                # Search
                with Vertical(classes="filter-group"):
                    yield Label("Search:")
                    yield Input(
                        placeholder="Search logs...",
                        id="search-input"
                    )
            
            # Log viewer
            with Vertical(id="log-viewer-panel", classes="panel"):
                with VerticalScroll():
                    yield Static(id="log-content", classes="log")
            
            # Status bar
            yield Label(
                "0 logs loaded | Press / to search | ESC to go back",
                id="status-bar"
            )
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the log screen."""
        self.title = "Log Viewer"
        self.sub_title = "System logs"
        
        # Load initial logs
        self.logs: List[Tuple[str, str, str, str]] = []
        self.filtered_logs: List[Tuple[str, str, str, str]] = []
        self.load_sample_logs()
        self.update_log_display()
    
    def load_sample_logs(self) -> None:
        """Load sample log entries."""
        # Format: (timestamp, level, component, message)
        self.logs = [
            (
                "2024-01-20 10:30:00.123",
                "INFO",
                "Agent",
                "Agent initialized successfully"
            ),
            (
                "2024-01-20 10:30:00.456",
                "DEBUG",
                "Memory",
                "Loading conversation blocks from storage"
            ),
            (
                "2024-01-20 10:30:01.789",
                "INFO",
                "Tools",
                "Registered tool: web_search"
            ),
            (
                "2024-01-20 10:30:02.012",
                "WARNING",
                "Evaluator",
                "Low relevance score detected: 0.45"
            ),
            (
                "2024-01-20 10:30:02.345",
                "ERROR",
                "Tools",
                "Failed to connect to MCP server: Connection refused"
            ),
            (
                "2024-01-20 10:30:02.678",
                "INFO",
                "Agent",
                "Processing user message: 'What is the weather?'"
            ),
            (
                "2024-01-20 10:30:03.901",
                "DEBUG",
                "Evaluator",
                "Semantic alignment score: 0.87"
            ),
            (
                "2024-01-20 10:30:04.234",
                "INFO",
                "Memory",
                "Block compressed and moved to warm storage"
            ),
        ]
        
        self.filtered_logs = self.logs.copy()
    
    def update_log_display(self) -> None:
        """Update the log display with filtered entries."""
        log_content = self.query_one("#log-content", Static)
        
        if not self.filtered_logs:
            log_content.update("[dim]No logs match the current filters[/dim]")
            self.update_status_bar(0)
            return
        
        # Format logs with color coding
        formatted_lines = []
        for timestamp, level, component, message in self.filtered_logs:
            # Color code by level
            level_colors = {
                "DEBUG": "dim cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
            }
            color = level_colors.get(level, "white")
            
            # Format the line
            line = (
                f"[dim]{timestamp}[/dim] "
                f"[{color}]{level:>7}[/{color}] "
                f"[bold blue]{component:>10}[/bold blue] "
                f"{message}"
            )
            formatted_lines.append(line)
        
        log_content.update("\n".join(formatted_lines))
        self.update_status_bar(len(self.filtered_logs))
    
    def update_status_bar(self, count: int) -> None:
        """Update the status bar."""
        status = self.query_one("#status-bar", Label)
        status.update(
            f"{count} logs loaded | Press / to search | ESC to go back"
        )
    
    def apply_filters(self) -> None:
        """Apply current filters to logs."""
        # Get filter values
        level_filter = self.get_selected_radio_value("#level-filter")
        component_filter = self.get_selected_radio_value("#component-filter")
        search_term = self.query_one("#search-input", Input).value.lower()
        
        # Filter logs
        self.filtered_logs = []
        for log_entry in self.logs:
            timestamp, level, component, message = log_entry
            
            # Apply level filter
            if level_filter != "All" and level != level_filter.upper():
                continue
            
            # Apply component filter
            if component_filter != "All" and component != component_filter:
                continue
            
            # Apply search filter
            if search_term and search_term not in message.lower():
                continue
            
            self.filtered_logs.append(log_entry)
        
        self.update_log_display()
    
    def get_selected_radio_value(self, radio_set_id: str) -> str:
        """Get the selected value from a RadioSet."""
        radio_set = self.query_one(radio_set_id, RadioSet)
        for button in radio_set.query(RadioButton):
            if button.value:
                return button.label.plain
        return "All"
    
    @on(RadioButton.Changed)
    def on_radio_changed(self, event: RadioButton.Changed) -> None:
        """Handle radio button changes."""
        if event.value:  # Only process when a button is selected
            self.apply_filters()
    
    @on(Input.Changed, "#search-input")
    def on_search_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        self.apply_filters()
    
    def action_refresh(self) -> None:
        """Refresh logs."""
        # In real implementation, would reload logs from source
        self.load_sample_logs()
        self.apply_filters()
    
    def action_focus_filter(self) -> None:
        """Focus on filter controls."""
        self.query_one("#level-filter").focus()
    
    def action_focus_search(self) -> None:
        """Focus on search input."""
        self.query_one("#search-input").focus()