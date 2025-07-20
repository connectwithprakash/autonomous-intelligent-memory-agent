"""Generate a preview of what the TUI looks like."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.text import Text
from rich.align import Align


def create_tui_preview():
    """Create a static preview of the TUI layout."""
    console = Console()
    
    # Create the main layout
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3)
    )
    
    # Header
    header = Panel(
        Align.center("Memory Agent Monitor - Real-time monitoring", vertical="middle"),
        style="bold white on blue",
    )
    layout["header"].update(header)
    
    # Body layout
    layout["body"].split_row(
        Layout(name="left"),
        Layout(name="right")
    )
    
    # Left side - Message Chain
    message_table = Table(show_header=False, show_edge=False, padding=(0, 1))
    message_table.add_row(Text("[USER]", style="bold green"), "What's the weather like?")
    message_table.add_row(Text("[ASSISTANT]", style="bold blue"), "I'll check the weather for you.")
    message_table.add_row(Text("[ASSISTANT]", style="bold blue"), Text("→ Calling weather_api...", style="italic cyan"))
    message_table.add_row(Text("[TOOL]", style="bold magenta"), Text("← Temperature: 22°C, Sunny", style="italic magenta"))
    message_table.add_row(Text("[ASSISTANT]", style="bold blue"), "It's 22°C and sunny.")
    
    layout["left"].split_column(
        Layout(Panel(message_table, title="Message Chain", border_style="blue"), name="messages"),
        Layout(name="corrections", size=8)
    )
    
    # Right side
    layout["right"].split_column(
        Layout(name="memory", size=12),
        Layout(name="relevance", size=10),
        Layout(name="tools", size=12)
    )
    
    # Memory Tiers
    memory_table = Table(title="Storage Tiers", show_header=True, header_style="bold cyan")
    memory_table.add_column("Tier", style="bold", width=8)
    memory_table.add_column("Blocks", justify="right", width=8)
    memory_table.add_column("Size", justify="right", width=10)
    memory_table.add_column("Access", justify="right", width=8)
    
    memory_table.add_row(Text("HOT", style="bold red"), "42", "2.1MB", "85%")
    memory_table.add_row(Text("WARM", style="bold yellow"), "156", "8.4MB", "32%")
    memory_table.add_row(Text("COLD", style="bold blue"), "1024", "52MB", "5%")
    memory_table.add_section()
    memory_table.add_row(Text("TOTAL", style="bold green"), "1222", "62.5MB", "")
    
    layout["memory"].update(Panel(memory_table, border_style="blue"))
    
    # Relevance Scores
    relevance_content = Text()
    relevance_content.append("Average: ", style="bold")
    relevance_content.append("0.87\n", style="green")
    relevance_content.append("Range: ", style="bold")
    relevance_content.append("0.45 - 0.98\n\n")
    relevance_content.append("Last 10: ", style="bold")
    relevance_content.append("✓", style="green")
    relevance_content.append("✓", style="green")
    relevance_content.append("✓", style="green")
    relevance_content.append("✗", style="red")
    relevance_content.append("✓", style="green")
    relevance_content.append("✓", style="green")
    relevance_content.append("◐", style="yellow")
    relevance_content.append("✓", style="green")
    relevance_content.append("✗", style="red")
    relevance_content.append("✓", style="green")
    relevance_content.append("\n\nTrend: ", style="bold")
    relevance_content.append("↑ Improving", style="green")
    
    layout["relevance"].update(Panel(relevance_content, title="Relevance Analysis", border_style="blue"))
    
    # Tool Activity
    tools_table = Table(show_header=True, header_style="bold cyan")
    tools_table.add_column("Tool", style="bold", width=15)
    tools_table.add_column("Activity", width=15)
    tools_table.add_column("Rate", justify="right", width=10)
    tools_table.add_column("Success", justify="right", width=8)
    
    tools_table.add_row(
        Text("● web_search", style="green"),
        "[yellow]███████████░░░░[/yellow]",
        "45/min",
        Text("96%", style="green")
    )
    tools_table.add_row(
        Text("○ calculator", style="dim"),
        "[cyan]██░░░░░░░░░░░░░[/cyan]",
        "12/min",
        Text("100%", style="green")
    )
    tools_table.add_row(
        Text("● mcp_server_1", style="green"),
        "[yellow]██████░░░░░░░░░[/yellow]",
        "23/min",
        Text("89%", style="yellow")
    )
    
    layout["tools"].update(Panel(tools_table, title="Tool Execution Monitor", border_style="blue"))
    
    # Corrections Log
    corrections_text = Text()
    corrections_text.append("[cyan]14:23:15[/cyan] Removed outdated weather data\n")
    corrections_text.append("[cyan]14:19:42[/cyan] Discarded irrelevant tool result\n")
    corrections_text.append("[cyan]14:15:08[/cyan] Corrected message sequence\n")
    
    layout["corrections"].update(Panel(corrections_text, title="Recent Corrections", border_style="green"))
    
    # Footer
    footer = Panel(
        "[bold]Keyboard:[/bold] [D]ebug | [L]ogs | [R]efresh | [Q]uit | Connected to agent | CPU: 23% | Mem: 487MB",
        style="white on grey23"
    )
    layout["footer"].update(footer)
    
    # Print the layout
    console.print("\n[bold cyan]Terminal UI Preview:[/bold cyan]\n")
    console.print(layout)
    console.print("\n[dim]This is a static preview. Run 'memory-agent monitor' for the interactive version.[/dim]")


if __name__ == "__main__":
    create_tui_preview()