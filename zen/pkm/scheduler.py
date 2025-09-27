"""
Cron job scheduler for PKM module.
"""

import asyncio
import json
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass

import schedule
from rich.console import Console
from rich.panel import Panel

from .config import PKMConfig
from .extractor import GeminiExtractor
from .processor import ConversationProcessor
from .storage import PKMStorage

console = Console()


@dataclass
class CronJob:
    """A scheduled cron job."""
    name: str
    schedule: str
    function: Callable
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    enabled: bool = True
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class PKMScheduler:
    """Scheduler for PKM cron jobs."""
    
    def __init__(self, config: PKMConfig):
        self.config = config
        self.storage = PKMStorage(config)
        self.processor = ConversationProcessor(config, self.storage)
        self.jobs: Dict[str, CronJob] = {}
        self.running = False
        self.state_file = config.pkm_dir / "scheduler_state.json"
        
        # Load existing state
        self._load_state()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def add_job(self, name: str, schedule_str: str, function: Callable, **kwargs) -> CronJob:
        """Add a new cron job."""
        job = CronJob(
            name=name,
            schedule=schedule_str,
            function=function,
            **kwargs
        )
        
        self.jobs[name] = job
        self._schedule_job(job)
        self._save_state()
        
        console.print(f"[green]✓[/green] Added job '{name}' with schedule '{schedule_str}'")
        return job
    
    def remove_job(self, name: str) -> bool:
        """Remove a cron job."""
        if name in self.jobs:
            # Clear the job from schedule
            schedule.clear(name)
            del self.jobs[name]
            self._save_state()
            console.print(f"[green]✓[/green] Removed job '{name}'")
            return True
        return False
    
    def enable_job(self, name: str) -> bool:
        """Enable a cron job."""
        if name in self.jobs:
            self.jobs[name].enabled = True
            self._schedule_job(self.jobs[name])
            self._save_state()
            console.print(f"[green]✓[/green] Enabled job '{name}'")
            return True
        return False
    
    def disable_job(self, name: str) -> bool:
        """Disable a cron job."""
        if name in self.jobs:
            self.jobs[name].enabled = False
            schedule.clear(name)
            self._save_state()
            console.print(f"[green]✓[/green] Disabled job '{name}'")
            return True
        return False
    
    def list_jobs(self) -> None:
        """List all cron jobs."""
        if not self.jobs:
            console.print("[yellow]No jobs configured[/yellow]")
            return
        
        table_data = []
        for name, job in self.jobs.items():
            status = "✅ Enabled" if job.enabled else "❌ Disabled"
            last_run = job.last_run.strftime("%Y-%m-%d %H:%M:%S") if job.last_run else "Never"
            next_run = job.next_run.strftime("%Y-%m-%d %H:%M:%S") if job.next_run else "Not scheduled"
            
            table_data.append([
                name,
                job.schedule,
                status,
                last_run,
                next_run
            ])
        
        from rich.table import Table
        table = Table(title="📅 PKM Cron Jobs", show_header=True, header_style="bold cyan")
        table.add_column("Name", style="green")
        table.add_column("Schedule", style="white")
        table.add_column("Status", style="yellow")
        table.add_column("Last Run", style="blue")
        table.add_column("Next Run", style="blue")
        
        for row in table_data:
            table.add_row(*row)
        
        console.print(table)
    
    def run_job(self, name: str) -> bool:
        """Run a specific job immediately."""
        if name not in self.jobs:
            console.print(f"[red]Job '{name}' not found[/red]")
            return False
        
        job = self.jobs[name]
        if not job.enabled:
            console.print(f"[yellow]Job '{name}' is disabled[/yellow]")
            return False
        
        console.print(f"[cyan]Running job '{name}'...[/cyan]")
        
        try:
            # Run the job
            if asyncio.iscoroutinefunction(job.function):
                asyncio.run(job.function())
            else:
                job.function()
            
            # Update job state
            job.last_run = datetime.now()
            self._calculate_next_run(job)
            self._save_state()
            
            console.print(f"[green]✓[/green] Job '{name}' completed successfully")
            return True
            
        except Exception as e:
            console.print(f"[red]✗[/red] Job '{name}' failed: {e}")
            return False
    
    def run_all_jobs(self) -> None:
        """Run all enabled jobs."""
        console.print("[cyan]Running all enabled jobs...[/cyan]")
        
        for name, job in self.jobs.items():
            if job.enabled:
                self.run_job(name)
    
    def start_scheduler(self) -> None:
        """Start the scheduler daemon."""
        if self.running:
            console.print("[yellow]Scheduler is already running[/yellow]")
            return
        
        self.running = True
        console.print("[green]🚀 Starting PKM scheduler...[/green]")
        
        # Setup default jobs if none exist
        if not self.jobs:
            self._setup_default_jobs()
        
        try:
            while self.running:
                schedule.run_pending()
                asyncio.sleep(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]Scheduler stopped by user[/yellow]")
        except Exception as e:
            console.print(f"[red]Scheduler error: {e}[/red]")
        finally:
            self.running = False
            self._save_state()
    
    def stop_scheduler(self) -> None:
        """Stop the scheduler daemon."""
        self.running = False
        console.print("[yellow]Stopping scheduler...[/yellow]")
    
    def _setup_default_jobs(self) -> None:
        """Setup default PKM jobs."""
        # Conversation extraction job
        self.add_job(
            name="extract_conversations",
            schedule=self.config.cron_schedule,
            function=self._extract_conversations_job,
            metadata={"description": "Extract conversations from Google Gemini"}
        )
        
        # Knowledge processing job
        self.add_job(
            name="process_knowledge",
            schedule="0 2 * * *",  # Daily at 2 AM
            function=self._process_knowledge_job,
            metadata={"description": "Process conversations and extract knowledge"}
        )
        
        # Cleanup job
        self.add_job(
            name="cleanup_old_data",
            schedule="0 3 * * 0",  # Weekly on Sunday at 3 AM
            function=self._cleanup_job,
            metadata={"description": "Clean up old data files"}
        )
    
    async def _extract_conversations_job(self) -> None:
        """Job to extract conversations from Google Gemini."""
        console.print("[cyan]🔄 Running conversation extraction job...[/cyan]")
        
        try:
            async with GeminiExtractor(self.config) as extractor:
                result = await extractor.extract_conversations(
                    max_conversations=self.config.max_conversations_per_run
                )
                
                if result.success:
                    console.print(f"[green]✓[/green] Extracted {result.conversations_extracted} conversations")
                else:
                    console.print(f"[red]✗[/red] Extraction failed: {', '.join(result.errors)}")
        
        except Exception as e:
            console.print(f"[red]✗[/red] Extraction job failed: {e}")
    
    async def _process_knowledge_job(self) -> None:
        """Job to process conversations and extract knowledge."""
        console.print("[cyan]🔄 Running knowledge processing job...[/cyan]")
        
        try:
            # Get unprocessed conversations
            conversations = self.storage.list_conversations()
            processed_count = 0
            
            for conversation in conversations:
                # Check if already processed
                if conversation.metadata.get("processed_at"):
                    continue
                
                # Process the conversation
                processed_conversation = await self.processor.process_conversation(conversation)
                self.storage.save_conversation(processed_conversation)
                processed_count += 1
            
            console.print(f"[green]✓[/green] Processed {processed_count} conversations")
        
        except Exception as e:
            console.print(f"[red]✗[/red] Processing job failed: {e}")
    
    async def _cleanup_job(self) -> None:
        """Job to clean up old data."""
        console.print("[cyan]🔄 Running cleanup job...[/cyan]")
        
        try:
            cleaned_count = self.storage.cleanup_old_data(days=30)
            console.print(f"[green]✓[/green] Cleaned up {cleaned_count} old files")
        
        except Exception as e:
            console.print(f"[red]✗[/red] Cleanup job failed: {e}")
    
    def _schedule_job(self, job: CronJob) -> None:
        """Schedule a job using the schedule library."""
        if not job.enabled:
            return
        
        # Clear existing schedule for this job
        schedule.clear(job.name)
        
        # Parse schedule string and add to schedule
        if job.schedule.startswith("every "):
            # Handle "every X minutes/hours/days" format
            parts = job.schedule.split()
            if len(parts) >= 3:
                interval = int(parts[1])
                unit = parts[2]
                
                if unit == "minutes":
                    schedule.every(interval).minutes.do(self._run_job_wrapper, job.name).tag(job.name)
                elif unit == "hours":
                    schedule.every(interval).hours.do(self._run_job_wrapper, job.name).tag(job.name)
                elif unit == "days":
                    schedule.every(interval).days.do(self._run_job_wrapper, job.name).tag(job.name)
        else:
            # Handle cron format (simplified)
            # This is a basic implementation - for production, use a proper cron parser
            if job.schedule == "0 */6 * * *":  # Every 6 hours
                schedule.every(6).hours.do(self._run_job_wrapper, job.name).tag(job.name)
            elif job.schedule == "0 2 * * *":  # Daily at 2 AM
                schedule.every().day.at("02:00").do(self._run_job_wrapper, job.name).tag(job.name)
            elif job.schedule == "0 3 * * 0":  # Weekly on Sunday at 3 AM
                schedule.every().sunday.at("03:00").do(self._run_job_wrapper, job.name).tag(job.name)
        
        # Calculate next run time
        self._calculate_next_run(job)
    
    def _run_job_wrapper(self, job_name: str) -> None:
        """Wrapper to run a job and update its state."""
        if job_name in self.jobs:
            job = self.jobs[job_name]
            job.last_run = datetime.now()
            self._calculate_next_run(job)
            self._save_state()
            
            # Run the job
            try:
                if asyncio.iscoroutinefunction(job.function):
                    asyncio.run(job.function())
                else:
                    job.function()
            except Exception as e:
                console.print(f"[red]Job '{job_name}' failed: {e}[/red]")
    
    def _calculate_next_run(self, job: CronJob) -> None:
        """Calculate the next run time for a job."""
        # This is a simplified implementation
        # In a real implementation, you'd parse the cron expression properly
        if job.schedule == "0 */6 * * *":
            job.next_run = datetime.now() + timedelta(hours=6)
        elif job.schedule == "0 2 * * *":
            tomorrow = datetime.now() + timedelta(days=1)
            job.next_run = tomorrow.replace(hour=2, minute=0, second=0, microsecond=0)
        elif job.schedule == "0 3 * * 0":
            # Next Sunday at 3 AM
            days_ahead = 6 - datetime.now().weekday()  # Sunday is 6
            if days_ahead <= 0:
                days_ahead += 7
            next_sunday = datetime.now() + timedelta(days=days_ahead)
            job.next_run = next_sunday.replace(hour=3, minute=0, second=0, microsecond=0)
    
    def _load_state(self) -> None:
        """Load scheduler state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                
                for job_data in data.get("jobs", []):
                    job = CronJob(**job_data)
                    self.jobs[job.name] = job
                    if job.enabled:
                        self._schedule_job(job)
            
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to load scheduler state: {e}[/yellow]")
    
    def _save_state(self) -> None:
        """Save scheduler state to file."""
        try:
            data = {
                "jobs": [
                    {
                        "name": job.name,
                        "schedule": job.schedule,
                        "last_run": job.last_run.isoformat() if job.last_run else None,
                        "next_run": job.next_run.isoformat() if job.next_run else None,
                        "enabled": job.enabled,
                        "metadata": job.metadata
                    }
                    for job in self.jobs.values()
                ]
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
        
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to save scheduler state: {e}[/yellow]")
    
    def _signal_handler(self, signum, frame) -> None:
        """Handle shutdown signals."""
        console.print(f"\n[yellow]Received signal {signum}, shutting down...[/yellow]")
        self.stop_scheduler()
        sys.exit(0)