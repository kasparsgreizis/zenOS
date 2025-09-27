#!/usr/bin/env python3
"""
zenOS CLI - The main command-line interface for zenOS.

Usage:
    zen <agent> "your prompt"
    zen --list
    zen --create <agent>
"""

import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.syntax import Syntax

from zen.core.launcher import Launcher
from zen.core.agent import AgentRegistry
from zen.utils.config import Config
from zen import __version__
from zen.cli_plugins import plugins
from zen.inbox import receive

console = Console()


@click.group()
@click.option("--version", is_flag=True, help="Show version")
def cli(version: bool):
    """🧘 zenOS - The Zen of AI Workflow Orchestration"""
    if version:
        console.print(f"zenOS v{__version__}")
        return

@cli.command()
@click.argument("agent", required=False)
@click.argument("prompt", required=False)
@click.option("--list", "list_agents", is_flag=True, help="List all available agents")
@click.option("--create", help="Create a new agent from template")
@click.option("--vars", help="Variables as JSON string or key=value pairs")
@click.option("--no-critique", is_flag=True, help="Disable auto-critique")
@click.option("--upgrade-only", is_flag=True, help="Only upgrade the prompt, don't execute")
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.option("--chat", is_flag=True, help="Start interactive chat mode")
@click.option("--offline", is_flag=True, help="Force offline mode with local models")
@click.option("--model", "-m", help="Specify model to use")
@click.option("--eco", is_flag=True, help="Battery-saving eco mode (mobile)")
def run(
    agent: Optional[str],
    prompt: Optional[str],
    list_agents: bool,
    create: Optional[str],
    vars: Optional[str],
    no_critique: bool,
    upgrade_only: bool,
    debug: bool,
    version: bool,
    chat: bool,
    offline: bool,
    model: Optional[str],
    eco: bool,
) -> None:
    """
    🧘 zenOS - The Zen of AI Workflow Orchestration
    
    Run AI agents with zen-like simplicity.
    
    Examples:
        zen chat                      # Start interactive chat mode
        zen troubleshoot "fix my git issue"
        zen critic "review this prompt"
        zen --list
        zen --create my-agent
    """
    
    if version:
        console.print(f"[cyan]zenOS version {__version__}[/cyan]")
        return
    
    if chat or (agent and agent == "chat"):
        # Start interactive chat mode
        import asyncio
        import os
        
        # Configure offline/eco modes
        if offline:
            os.environ['ZEN_PREFER_OFFLINE'] = 'true'
            console.print("[green]🔌 Offline mode enabled - using local models[/green]")
        
        if eco:
            os.environ['ZEN_ECO_MODE'] = 'true'
            console.print("[yellow]🔋 Eco mode enabled - optimizing for battery[/yellow]")
        
        if model:
            os.environ['ZEN_DEFAULT_MODEL'] = model
        
        # Auto-detect mobile/compact mode
        is_mobile = (
            os.environ.get("COMPACT_MODE") == "1" or
            os.environ.get("TERMUX_VERSION") or
            int(os.environ.get("COLUMNS", 80)) < 60
        )
        
        if is_mobile:
            from zen.ui.mobile import MobileChat
            console.print("[cyan]🧘 zenOS Mobile Mode[/cyan]")
            
            # Show offline status if available
            if offline:
                from zen.providers.offline import get_offline_manager
                mgr = get_offline_manager()
                status = mgr.get_status()
                if status['recommended_model']:
                    console.print(f"[green]📱 Using {status['recommended_model']} (optimized for your device)[/green]")
            
            chat_session = MobileChat()
        else:
            from zen.ui.interactive import InteractiveChat
            chat_session = InteractiveChat()
        
        asyncio.run(chat_session.start())
        return
    
    if list_agents:
        show_agents()
        return
    
    if create:
        create_agent(create)
        return
    
    if not agent:
        console.print("[red]Error:[/red] Please specify an agent or use --chat for interactive mode")
        console.print("\n[dim]Usage: zen chat  OR  zen <agent> \"your prompt\"[/dim]")
        sys.exit(1)
    
    if not prompt and not upgrade_only:
        console.print("[red]Error:[/red] Please provide a prompt")
        console.print("\n[dim]Usage: zen <agent> \"your prompt\"[/dim]")
        sys.exit(1)
    
    # Parse variables
    variables = parse_variables(vars) if vars else {}
    
    # Run the agent
    run_agent(
        agent=agent,
        prompt=prompt or "",
        variables=variables,
        no_critique=no_critique,
        upgrade_only=upgrade_only,
        debug=debug,
    )


def show_agents() -> None:
    """Display all available agents in a beautiful table."""
    registry = AgentRegistry()
    agents = registry.list_agents()
    
    if not agents:
        console.print("[yellow]No agents found.[/yellow]")
        console.print("\nCreate your first agent with: [cyan]zen --create my-agent[/cyan]")
        return
    
    table = Table(title="🤖 Available Agents", show_header=True, header_style="bold cyan")
    table.add_column("Agent", style="green", no_wrap=True)
    table.add_column("Description", style="white")
    table.add_column("Type", style="yellow")
    
    for agent_info in agents:
        table.add_row(
            agent_info["name"],
            agent_info.get("description", "No description"),
            agent_info.get("type", "custom"),
        )
    
    console.print(table)
    console.print("\n[dim]Run an agent: zen <agent> \"your prompt\"[/dim]")


def create_agent(name: str) -> None:
    """Create a new agent from template."""
    console.print(f"[cyan]Creating new agent: {name}[/cyan]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Setting up agent template...", total=None)
        
        registry = AgentRegistry()
        try:
            agent_path = registry.create_agent(name)
            progress.update(task, completed=True)
            
            console.print(f"[green]✓[/green] Agent created at: {agent_path}")
            console.print(f"\nEdit your agent configuration and run:")
            console.print(f"[cyan]zen {name} \"your prompt\"[/cyan]")
            
        except Exception as e:
            progress.update(task, completed=True)
            console.print(f"[red]✗[/red] Failed to create agent: {e}")
            sys.exit(1)


def parse_variables(vars_str: str) -> Dict[str, Any]:
    """Parse variables from string input."""
    # Try JSON first
    try:
        return json.loads(vars_str)
    except json.JSONDecodeError:
        pass
    
    # Try key=value pairs
    variables = {}
    for pair in vars_str.split(","):
        if "=" in pair:
            key, value = pair.split("=", 1)
            variables[key.strip()] = value.strip()
    
    return variables


def run_agent(
    agent: str,
    prompt: str,
    variables: Dict[str, Any],
    no_critique: bool,
    upgrade_only: bool,
    debug: bool,
) -> None:
    """Run an agent with the given prompt."""
    console.print(Panel.fit(
        f"[bold cyan]🧘 Running Agent:[/bold cyan] {agent}",
        border_style="cyan",
    ))
    
    launcher = Launcher(debug=debug)
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Load agent
            task = progress.add_task("Loading agent...", total=None)
            launcher.load_agent(agent)
            progress.update(task, completed=True)
            
            # Auto-critique unless disabled
            if not no_critique:
                task = progress.add_task("Enhancing prompt with auto-critique...", total=None)
                prompt = launcher.critique_prompt(prompt)
                progress.update(task, completed=True)
                
                if upgrade_only:
                    console.print("\n[green]✓[/green] Prompt upgraded successfully!")
                    console.print(Panel(prompt, title="Enhanced Prompt", border_style="green"))
                    return
            
            # Execute agent
            task = progress.add_task("Executing agent...", total=None)
            result = launcher.execute(prompt, variables)
            progress.update(task, completed=True)
        
        # Display result
        console.print("\n[green]✓[/green] Agent completed successfully!")
        
        if isinstance(result, str):
            console.print(Panel(result, title="Result", border_style="green"))
        else:
            # Pretty print JSON/dict results
            syntax = Syntax(
                json.dumps(result, indent=2),
                "json",
                theme="monokai",
                line_numbers=False,
            )
            console.print(Panel(syntax, title="Result", border_style="green"))
            
    except Exception as e:
        console.print(f"\n[red]✗[/red] Agent failed: {e}")
        if debug:
            import traceback
            console.print("[dim]" + traceback.format_exc() + "[/dim]")
        sys.exit(1)


@cli.command()
@click.option('--unattended', is_flag=True, help='Run in unattended mode')
@click.option('--validate-only', is_flag=True, help='Only validate environment')
@click.option('--phase', type=click.Choice(['detection', 'validation', 'git_setup', 'mcp_setup', 'zenos_setup', 'integration', 'verification']), help='Start from specific phase')
def setup(unattended, validate_only, phase):
    """Setup zenOS development environment"""
    from zen.setup.unified_setup import UnifiedSetupManager
    
    manager = UnifiedSetupManager(unattended=unattended)
    
    if validate_only:
        success = manager._run_validation_phase()
    elif phase:
        # Start from specific phase
        phase_map = {
            'detection': manager._run_detection_phase,
            'validation': manager._run_validation_phase,
            'git_setup': manager._run_git_setup_phase,
            'mcp_setup': manager._run_mcp_setup_phase,
            'zenos_setup': manager._run_zenos_setup_phase,
            'integration': manager._run_integration_phase,
            'verification': manager._run_verification_phase
        }
        success = phase_map[phase]()
    else:
        success = manager.run_setup()
    
    if not success:
        sys.exit(1)

# Add plugin commands to CLI
cli.add_command(plugins)
cli.add_command(receive)

# Add PKM commands
from zen.pkm.cli import pkm
cli.add_command(pkm)

if __name__ == "__main__":
    cli()
