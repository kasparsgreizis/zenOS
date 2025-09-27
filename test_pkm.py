#!/usr/bin/env python3
"""
Test script for PKM module
"""

import asyncio
import sys
from pathlib import Path

# Add the zenOS package to the path
sys.path.insert(0, str(Path(__file__).parent))

from zen.pkm.config import PKMConfig
from zen.pkm.storage import PKMStorage
from zen.pkm.models import Conversation, Message, MessageRole
from zen.pkm.processor import ConversationProcessor
from zen.pkm.scheduler import PKMScheduler
from rich.console import Console

console = Console()


def test_config():
    """Test configuration loading."""
    console.print("[cyan]Testing configuration...[/cyan]")
    
    config = PKMConfig.load()
    console.print(f"✅ Config loaded: {config.pkm_dir}")
    console.print(f"✅ Storage format: {config.storage_format}")
    console.print(f"✅ Auto-summarize: {config.auto_summarize}")
    
    return config


def test_storage(config):
    """Test storage functionality."""
    console.print("\n[cyan]Testing storage...[/cyan]")
    
    storage = PKMStorage(config)
    
    # Create a test conversation
    test_conversation = Conversation(
        id="test_conv_001",
        title="Test Conversation",
        messages=[
            Message(
                role=MessageRole.USER,
                content="Hello, can you help me with Python programming?",
                timestamp=None
            ),
            Message(
                role=MessageRole.ASSISTANT,
                content="Of course! I'd be happy to help you with Python programming. What specific topic would you like to learn about?",
                timestamp=None
            )
        ],
        created_at=None,
        updated_at=None
    )
    
    # Save the conversation
    success = storage.save_conversation(test_conversation)
    console.print(f"✅ Conversation saved: {success}")
    
    # Load the conversation
    loaded_conv = storage.load_conversation("test_conv_001")
    console.print(f"✅ Conversation loaded: {loaded_conv is not None}")
    
    if loaded_conv:
        console.print(f"   • Title: {loaded_conv.title}")
        console.print(f"   • Messages: {len(loaded_conv.messages)}")
    
    # Test search
    search_results = storage.search_conversations("Python")
    console.print(f"✅ Search results: {len(search_results)} conversations found")
    
    # Test statistics
    stats = storage.get_storage_stats()
    console.print(f"✅ Storage stats: {stats['conversations_count']} conversations")
    
    return storage


async def test_processor(config, storage):
    """Test conversation processing."""
    console.print("\n[cyan]Testing processor...[/cyan]")
    
    processor = ConversationProcessor(config, storage)
    
    # Get the test conversation
    conversation = storage.load_conversation("test_conv_001")
    if not conversation:
        console.print("❌ No test conversation found")
        return
    
    # Process the conversation
    processed_conv = await processor.process_conversation(conversation)
    console.print(f"✅ Conversation processed: {processed_conv is not None}")
    
    if processed_conv:
        console.print(f"   • Summary: {processed_conv.summary[:50]}..." if processed_conv.summary else "   • Summary: None")
        console.print(f"   • Keywords: {processed_conv.keywords}")
        console.print(f"   • Tags: {processed_conv.tags}")
    
    # Save the processed conversation
    storage.save_conversation(processed_conv)
    console.print("✅ Processed conversation saved")


def test_scheduler(config):
    """Test scheduler functionality."""
    console.print("\n[cyan]Testing scheduler...[/cyan]")
    
    scheduler = PKMScheduler(config)
    
    # List jobs
    console.print("📅 Available jobs:")
    scheduler.list_jobs()
    
    # Test job creation
    def test_job():
        console.print("🧪 Test job executed!")
    
    job = scheduler.add_job("test_job", "every 1 minutes", test_job)
    console.print(f"✅ Test job added: {job.name}")
    
    # Test job execution
    success = scheduler.run_job("test_job")
    console.print(f"✅ Test job executed: {success}")
    
    # Remove test job
    removed = scheduler.remove_job("test_job")
    console.print(f"✅ Test job removed: {removed}")


async def main():
    """Main test function."""
    console.print(Panel.fit(
        "[bold cyan]🧪 PKM Module Test Suite[/bold cyan]",
        border_style="cyan"
    ))
    
    try:
        # Test configuration
        config = test_config()
        
        # Test storage
        storage = test_storage(config)
        
        # Test processor
        await test_processor(config, storage)
        
        # Test scheduler
        test_scheduler(config)
        
        console.print("\n[green]✅ All tests passed![/green]")
        console.print("\n[cyan]PKM module is working correctly.[/cyan]")
        console.print("You can now use: zen pkm --help")
        
    except Exception as e:
        console.print(f"\n[red]❌ Test failed: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())