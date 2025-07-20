"""Message chain widget for displaying conversation flow."""

from datetime import datetime
from typing import List, Optional

from rich.console import RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget

from memory_agent.core.entities import Message
from memory_agent.core.interfaces import MessageRole, MessageType


class MessageChainWidget(Widget):
    """Widget for displaying the message chain."""
    
    messages: reactive[List[Message]] = reactive([], layout=True)
    
    def __init__(self, *args, **kwargs):
        """Initialize the widget."""
        super().__init__(*args, **kwargs)
        self._mock_messages = self._create_mock_messages()
    
    def _create_mock_messages(self) -> List[Message]:
        """Create mock messages for demonstration."""
        return [
            Message(
                role=MessageRole.USER,
                content="What's the weather like?",
                type=MessageType.TEXT,
            ),
            Message(
                role=MessageRole.ASSISTANT,
                content="I'll check the weather for you.",
                type=MessageType.TEXT,
            ),
            Message(
                role=MessageRole.ASSISTANT,
                content="",
                type=MessageType.TOOL_CALL,
                tool_name="weather_api",
            ),
            Message(
                role=MessageRole.TOOL,
                content="Temperature: 22°C, Sunny",
                type=MessageType.TOOL_RESULT,
                tool_name="weather_api",
            ),
            Message(
                role=MessageRole.ASSISTANT,
                content="The weather is currently 22°C and sunny.",
                type=MessageType.TEXT,
            ),
        ]
    
    def render(self) -> RenderableType:
        """Render the message chain."""
        table = Table(
            show_header=False,
            show_edge=False,
            padding=(0, 1),
            expand=True,
        )
        
        # Use mock messages for now
        messages = self._mock_messages if not self.messages else self.messages
        
        for msg in messages[-10:]:  # Show last 10 messages
            # Format role
            role_color = {
                MessageRole.USER: "green",
                MessageRole.ASSISTANT: "blue",
                MessageRole.SYSTEM: "yellow",
                MessageRole.TOOL: "magenta",
            }.get(msg.role, "white")
            
            role_text = Text(f"[{msg.role.value.upper()}]", style=f"bold {role_color}")
            
            # Format content
            if msg.type == MessageType.TOOL_CALL:
                content = Text(f"→ Calling {msg.tool_name}...", style="italic cyan")
            elif msg.type == MessageType.TOOL_RESULT:
                content = Text(f"← {msg.content}", style="italic magenta")
            elif msg.type == MessageType.CORRECTION:
                content = Text(f"✗ {msg.content}", style="red")
            else:
                # Truncate long content
                text = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
                content = Text(text)
            
            # Add row
            table.add_row(role_text, content)
        
        return Panel(
            table,
            border_style="blue",
            title="Messages",
            title_align="left",
        )
    
    def refresh_data(self) -> None:
        """Refresh the message data."""
        # In a real implementation, this would fetch from the agent
        # For now, we'll rotate through mock messages
        if self._mock_messages:
            # Simulate new message
            self._mock_messages.append(
                Message(
                    role=MessageRole.SYSTEM,
                    content=f"Update at {datetime.utcnow().strftime('%H:%M:%S')}",
                    type=MessageType.TEXT,
                )
            )
            if len(self._mock_messages) > 20:
                self._mock_messages = self._mock_messages[-20:]
        
        self.refresh()
    
    def add_message(self, message: Message) -> None:
        """Add a new message to the chain."""
        new_messages = list(self.messages)
        new_messages.append(message)
        self.messages = new_messages
    
    def clear_messages(self) -> None:
        """Clear all messages."""
        self.messages = []