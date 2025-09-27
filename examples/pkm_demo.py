#!/usr/bin/env python3
"""
PKM Module Demo Script

This script demonstrates the PKM module capabilities for extracting
and managing Google Gemini conversations.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the zenOS package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from zen.pkm.config import PKMConfig
from zen.pkm.extractor import GeminiExtractor
from zen.pkm.processor import ConversationProcessor
from zen.pkm.storage import PKMStorage
from zen.pkm.scheduler import PKMScheduler
from rich.console import Console
from rich.panel import Panel

console = Console()


async def demo_pkm_module():
    """Demonstrate PKM module functionality."""
    
    console.print(Panel.fit(
        "[bold cyan]🧘 PKM Module Demo[/bold cyan]\n"
        "Personal Knowledge Management for Google Gemini Conversations",
        border_style="cyan"
    ))
    
    # 1. Setup Configuration
    console.print("\n[cyan]1. Setting up PKM configuration...[/cyan]")
    config = PKMConfig.load()
    console.print(f"✅ Configuration loaded from: {config.pkm_dir}")
    
    # 2. Initialize Storage
    console.print("\n[cyan]2. Initializing storage system...[/cyan]")
    storage = PKMStorage(config)
    console.print(f"✅ Storage initialized")
    console.print(f"   • Conversations: {storage.conversations_dir}")
    console.print(f"   • Knowledge Base: {storage.knowledge_base_dir}")
    console.print(f"   • Exports: {storage.exports_dir}")
    
    # 3. Show Current Statistics
    console.print("\n[cyan]3. Current PKM statistics...[/cyan]")
    stats = storage.get_storage_stats()
    console.print(f"📊 Conversations: {stats['conversations_count']}")
    console.print(f"📊 Knowledge entries: {stats['knowledge_entries_count']}")
    console.print(f"📊 Storage size: {stats['total_size_mb']} MB")
    
    # 4. Demo Conversation Extraction (Simulated)
    console.print("\n[cyan]4. Demo conversation extraction...[/cyan]")
    console.print("⚠️  Note: This is a demo. Real extraction requires valid Google Gemini session cookies.")
    
    if not config.gemini_session_cookie:
        console.print("🔧 To enable real extraction, set environment variables:")
        console.print("   export GEMINI_SESSION_COOKIE='your_session_cookie'")
        console.print("   export GEMINI_CSRF_TOKEN='your_csrf_token'")
        console.print("   Then run: zen pkm extract")
    else:
        console.print("✅ Session cookie found. You can run: zen pkm extract")
    
    # 5. Demo Knowledge Processing
    console.print("\n[cyan]5. Demo knowledge processing...[/cyan]")
    processor = ConversationProcessor(config, storage)
    
    # Check if we have any conversations to process
    conversations = storage.list_conversations(limit=1)
    if conversations:
        console.print(f"📚 Found {len(conversations)} conversation(s) to process")
        console.print("   Run: zen pkm process")
    else:
        console.print("📭 No conversations found. Extract some first with: zen pkm extract")
    
    # 6. Demo Search Capabilities
    console.print("\n[cyan]6. Demo search capabilities...[/cyan]")
    if conversations:
        # Search through existing conversations
        search_results = storage.search_conversations("demo", limit=3)
        console.print(f"🔍 Search results for 'demo': {len(search_results)} conversations")
    else:
        console.print("🔍 No conversations to search. Extract some first.")
    
    # 7. Demo Scheduling
    console.print("\n[cyan]7. Demo scheduling system...[/cyan]")
    scheduler = PKMScheduler(config)
    console.print("📅 Available scheduled jobs:")
    scheduler.list_jobs()
    
    # 8. Demo Export
    console.print("\n[cyan]8. Demo export capabilities...[/cyan]")
    if conversations:
        console.print("📤 Export options available:")
        console.print("   • zen pkm export --format json")
        console.print("   • zen pkm export --format markdown")
    else:
        console.print("📤 No data to export. Extract conversations first.")
    
    # 9. Show CLI Commands
    console.print("\n[cyan]9. Available CLI commands...[/cyan]")
    console.print("""
🧘 PKM Commands:
  zen pkm setup                    # Setup PKM module
  zen pkm extract [--limit N]      # Extract conversations
  zen pkm list [--limit N]         # List conversations
  zen pkm search <query>           # Search conversations
  zen pkm process                  # Process conversations
  zen pkm export [--format FMT]    # Export data
  zen pkm stats                    # Show statistics
  zen pkm schedule list            # List scheduled jobs
  zen pkm schedule run <job>       # Run specific job
  zen pkm config-show              # Show configuration
""")
    
    # 10. Next Steps
    console.print("\n[cyan]10. Next steps...[/cyan]")
    console.print("""
🚀 To get started with PKM:

1. Setup authentication:
   export GEMINI_SESSION_COOKIE='your_session_cookie'
   export GEMINI_CSRF_TOKEN='your_csrf_token'

2. Extract conversations:
   zen pkm extract

3. Process knowledge:
   zen pkm process

4. Search and explore:
   zen pkm search "your query"
   zen pkm list
   zen pkm stats

5. Set up automation:
   zen pkm schedule start
""")
    
    console.print("\n[green]✅ PKM Module Demo completed![/green]")
    console.print("For more information, see: zen/pkm/README.md")


def main():
    """Main function."""
    try:
        asyncio.run(demo_pkm_module())
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Demo failed: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()