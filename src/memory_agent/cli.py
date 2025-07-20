"""Command-line interface for the memory agent."""

import click


@click.group()
def main():
    """Memory Agent CLI - Autonomous AI with self-correction."""
    pass


@main.command()
@click.option(
    "--url",
    "-u",
    default="http://localhost:8000",
    help="URL of the memory agent API",
)
def monitor(url: str):
    """Launch the terminal UI monitor."""
    from memory_agent.infrastructure.cli.tui import run_tui
    
    click.echo(f"Connecting to Memory Agent at {url}...")
    run_tui(agent_url=url)


@main.command()
@click.option(
    "--host",
    "-h",
    default="0.0.0.0",
    help="Host to bind the API server",
)
@click.option(
    "--port",
    "-p",
    default=8000,
    type=int,
    help="Port to bind the API server",
)
@click.option(
    "--reload",
    is_flag=True,
    help="Enable auto-reload for development",
)
def start(host: str, port: int, reload: bool):
    """Start the memory agent API server."""
    import uvicorn
    
    click.echo(f"Starting Memory Agent API on {host}:{port}")
    
    uvicorn.run(
        "memory_agent.infrastructure.api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


@main.command()
@click.option(
    "--port",
    "-p", 
    default=5173,
    type=int,
    help="Port for the web dashboard",
)
def dashboard(port: int):
    """Launch the web dashboard."""
    import subprocess
    import os
    
    dashboard_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "dashboard",
        "dashboard"
    )
    
    if not os.path.exists(dashboard_dir):
        click.echo("Dashboard not found. Please ensure the dashboard is built.")
        return
    
    click.echo(f"Starting web dashboard on port {port}")
    click.echo("Navigate to http://localhost:5173 to view the dashboard")
    
    try:
        subprocess.run(
            ["npm", "run", "dev"],
            cwd=dashboard_dir,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        click.echo(f"Failed to start dashboard: {e}")
    except KeyboardInterrupt:
        click.echo("\nDashboard stopped.")


if __name__ == "__main__":
    main()