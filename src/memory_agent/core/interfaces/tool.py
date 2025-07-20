"""Tool interface definitions for external integrations."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class ToolType(str, Enum):
    """Types of tools available."""

    NATIVE = "native"  # Built-in tools
    MCP = "mcp"  # MCP server tools
    CUSTOM = "custom"  # User-defined tools


class ToolParameter(BaseModel):
    """Definition of a tool parameter."""

    name: str
    type: str  # "string", "number", "boolean", etc.
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None


class ToolSpec(BaseModel):
    """Specification of a tool."""

    name: str
    description: str
    type: ToolType
    parameters: List[ToolParameter] = []
    returns: str = "string"
    examples: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}


class ToolResult(BaseModel):
    """Result from tool execution."""

    success: bool
    output: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}
    execution_time_ms: float


@runtime_checkable
class ITool(Protocol):
    """Protocol for individual tools."""

    @property
    def spec(self) -> ToolSpec:
        """Tool specification."""
        ...

    async def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate tool parameters.
        
        Args:
            params: Parameters to validate
            
        Returns:
            True if valid
        """
        ...

    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Execute the tool with parameters.
        
        Args:
            params: Tool parameters
            
        Returns:
            Tool execution result
        """
        ...


@runtime_checkable
class IToolRegistry(Protocol):
    """Protocol for tool registry management."""

    async def register_tool(self, tool: ITool) -> bool:
        """Register a new tool.
        
        Args:
            tool: Tool to register
            
        Returns:
            True if successful
        """
        ...

    async def unregister_tool(self, name: str) -> bool:
        """Unregister a tool.
        
        Args:
            name: Tool name
            
        Returns:
            True if successful
        """
        ...

    async def get_tool(self, name: str) -> Optional[ITool]:
        """Get a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool if found
        """
        ...

    async def list_tools(self) -> List[ToolSpec]:
        """List all available tools.
        
        Returns:
            List of tool specifications
        """
        ...

    async def discover_tools(self) -> List[ToolSpec]:
        """Discover new tools (e.g., from MCP servers).
        
        Returns:
            List of discovered tools
        """
        ...


@runtime_checkable
class IMCPClient(Protocol):
    """Protocol for MCP server client."""

    async def connect(self, server_url: str) -> bool:
        """Connect to an MCP server.
        
        Args:
            server_url: MCP server URL
            
        Returns:
            True if connected
        """
        ...

    async def disconnect(self) -> bool:
        """Disconnect from the MCP server.
        
        Returns:
            True if disconnected
        """
        ...

    async def list_tools(self) -> List[ToolSpec]:
        """List tools available on the MCP server.
        
        Returns:
            List of tool specifications
        """
        ...

    async def execute_tool(
        self, tool_name: str, params: Dict[str, Any]
    ) -> ToolResult:
        """Execute a tool on the MCP server.
        
        Args:
            tool_name: Name of the tool
            params: Tool parameters
            
        Returns:
            Tool execution result
        """
        ...