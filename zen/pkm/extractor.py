"""
Google Gemini conversation extractor for PKM module.
"""

import asyncio
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import Progress, TaskID

from .config import PKMConfig
from .models import Conversation, Message, MessageRole, ConversationStatus, ExtractionResult

console = Console()


class GeminiExtractor:
    """Extractor for Google Gemini web conversations."""
    
    def __init__(self, config: PKMConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = "https://gemini.google.com"
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self._create_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def _create_session(self):
        """Create aiohttp session with proper headers."""
        headers = {
            "User-Agent": self.config.gemini_user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        # Add cookies if available
        cookies = {}
        if self.config.gemini_session_cookie:
            cookies["session"] = self.config.gemini_session_cookie
        
        self.session = aiohttp.ClientSession(
            headers=headers,
            cookies=cookies,
            timeout=aiohttp.ClientTimeout(total=self.config.conversation_timeout)
        )
    
    async def extract_conversations(self, max_conversations: Optional[int] = None) -> ExtractionResult:
        """
        Extract conversations from Google Gemini.
        
        Args:
            max_conversations: Maximum number of conversations to extract
            
        Returns:
            ExtractionResult with extraction statistics
        """
        start_time = datetime.now()
        result = ExtractionResult(
            success=False,
            conversations_extracted=0,
            conversations_processed=0,
            conversations_failed=0,
            total_messages=0,
            start_time=start_time,
            end_time=start_time
        )
        
        try:
            console.print("[cyan]🔍 Starting Google Gemini conversation extraction...[/cyan]")
            
            # Get conversation list
            conversation_urls = await self._get_conversation_list(max_conversations)
            if not conversation_urls:
                console.print("[yellow]No conversations found to extract[/yellow]")
                result.success = True
                return result
            
            console.print(f"[green]Found {len(conversation_urls)} conversations to extract[/green]")
            
            # Extract each conversation
            with Progress() as progress:
                task = progress.add_task(
                    "Extracting conversations...", 
                    total=len(conversation_urls)
                )
                
                for url in conversation_urls:
                    try:
                        conversation = await self._extract_single_conversation(url)
                        if conversation:
                            await self._save_conversation(conversation)
                            result.conversations_extracted += 1
                            result.conversations_processed += 1
                            result.total_messages += len(conversation.messages)
                        else:
                            result.conversations_failed += 1
                            result.warnings.append(f"Failed to extract conversation from {url}")
                        
                        progress.update(task, advance=1)
                        
                        # Rate limiting
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        result.conversations_failed += 1
                        result.errors.append(f"Error extracting {url}: {str(e)}")
                        progress.update(task, advance=1)
            
            result.success = True
            console.print(f"[green]✓ Extraction completed: {result.conversations_extracted} conversations, {result.total_messages} messages[/green]")
            
        except Exception as e:
            result.errors.append(f"Fatal error during extraction: {str(e)}")
            console.print(f"[red]✗ Extraction failed: {e}[/red]")
        
        finally:
            result.end_time = datetime.now()
        
        return result
    
    async def _get_conversation_list(self, max_conversations: Optional[int] = None) -> List[str]:
        """Get list of conversation URLs from Gemini."""
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        try:
            # Try to access the main Gemini page
            async with self.session.get(self.base_url) as response:
                if response.status != 200:
                    console.print(f"[red]Failed to access Gemini: HTTP {response.status}[/red]")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Look for conversation links
                conversation_urls = []
                
                # This is a simplified approach - in reality, you'd need to:
                # 1. Handle authentication properly
                # 2. Use the actual Gemini API or reverse-engineer the web interface
                # 3. Parse the conversation list from the page
                
                # For now, we'll simulate finding conversation URLs
                # In a real implementation, you'd parse the actual conversation list
                console.print("[yellow]Note: This is a demo implementation. Real extraction requires proper authentication and API access.[/yellow]")
                
                # Simulate some conversation URLs for demonstration
                demo_urls = [
                    f"{self.base_url}/app/chat/1",
                    f"{self.base_url}/app/chat/2",
                    f"{self.base_url}/app/chat/3",
                ]
                
                if max_conversations:
                    demo_urls = demo_urls[:max_conversations]
                
                return demo_urls
                
        except Exception as e:
            console.print(f"[red]Error getting conversation list: {e}[/red]")
            return []
    
    async def _extract_single_conversation(self, url: str) -> Optional[Conversation]:
        """Extract a single conversation from its URL."""
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    console.print(f"[red]Failed to access conversation {url}: HTTP {response.status}[/red]")
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract conversation data
                # This is a simplified implementation
                # Real implementation would parse the actual Gemini conversation structure
                
                conversation_id = self._extract_conversation_id(url)
                title = self._extract_title(soup)
                messages = self._extract_messages(soup)
                
                if not messages:
                    console.print(f"[yellow]No messages found in conversation {url}[/yellow]")
                    return None
                
                conversation = Conversation(
                    id=conversation_id,
                    title=title,
                    messages=messages,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    url=url,
                    status=ConversationStatus.COMPLETED
                )
                
                return conversation
                
        except Exception as e:
            console.print(f"[red]Error extracting conversation {url}: {e}[/red]")
            return None
    
    def _extract_conversation_id(self, url: str) -> str:
        """Extract conversation ID from URL."""
        # Extract ID from URL path
        path_parts = urlparse(url).path.split('/')
        if len(path_parts) > 1:
            return path_parts[-1]
        return f"conv_{int(time.time())}"
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract conversation title from HTML."""
        # Look for title in various places
        title_selectors = [
            'h1',
            'title',
            '[data-testid="conversation-title"]',
            '.conversation-title'
        ]
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element and element.get_text().strip():
                return element.get_text().strip()
        
        return "Untitled Conversation"
    
    def _extract_messages(self, soup: BeautifulSoup) -> List[Message]:
        """Extract messages from conversation HTML."""
        messages = []
        
        # This is a simplified implementation
        # Real implementation would parse the actual Gemini message structure
        
        # Look for message containers
        message_containers = soup.find_all(['div', 'article'], class_=re.compile(r'message|chat|conversation'))
        
        for container in message_containers:
            # Determine if it's user or assistant message
            role = MessageRole.USER
            if 'assistant' in container.get('class', []) or 'bot' in container.get('class', []):
                role = MessageRole.ASSISTANT
            
            # Extract message content
            content_element = container.find(['p', 'div', 'span'])
            if content_element:
                content = content_element.get_text().strip()
                if content:
                    message = Message(
                        role=role,
                        content=content,
                        timestamp=datetime.now()
                    )
                    messages.append(message)
        
        # If no structured messages found, try to extract from text content
        if not messages:
            text_content = soup.get_text()
            if text_content and len(text_content.strip()) > 10:
                # Split by common patterns and create messages
                lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                for line in lines[:10]:  # Limit to first 10 lines
                    if len(line) > 5:  # Skip very short lines
                        message = Message(
                            role=MessageRole.USER,  # Default to user
                            content=line,
                            timestamp=datetime.now()
                        )
                        messages.append(message)
        
        return messages
    
    async def _save_conversation(self, conversation: Conversation):
        """Save conversation to storage."""
        # Save as JSON
        if self.config.storage_format in ["json", "both"]:
            json_path = self.config.conversations_dir / f"{conversation.id}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(conversation.to_dict(), f, indent=2, ensure_ascii=False)
            conversation.file_path = str(json_path)
            conversation.file_size = json_path.stat().st_size
        
        # Save as Markdown
        if self.config.storage_format in ["markdown", "both"]:
            md_path = self.config.conversations_dir / f"{conversation.id}.md"
            markdown_content = self._conversation_to_markdown(conversation)
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
    
    def _conversation_to_markdown(self, conversation: Conversation) -> str:
        """Convert conversation to Markdown format."""
        lines = [
            f"# {conversation.title}",
            f"",
            f"**ID:** {conversation.id}",
            f"**Created:** {conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Updated:** {conversation.updated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**URL:** {conversation.url or 'N/A'}",
            f"**Status:** {conversation.status.value}",
            f"",
            "---",
            f"",
        ]
        
        for i, message in enumerate(conversation.messages, 1):
            role_emoji = "👤" if message.role == MessageRole.USER else "🤖"
            timestamp = message.timestamp.strftime('%H:%M:%S') if message.timestamp else "Unknown"
            
            lines.extend([
                f"## {role_emoji} {message.role.value.title()} ({timestamp})",
                f"",
                message.content,
                f"",
            ])
        
        if conversation.summary:
            lines.extend([
                "---",
                f"",
                "## Summary",
                f"",
                conversation.summary,
                f"",
            ])
        
        if conversation.keywords:
            lines.extend([
                "## Keywords",
                f"",
                ", ".join(conversation.keywords),
                f"",
            ])
        
        if conversation.tags:
            lines.extend([
                "## Tags",
                f"",
                ", ".join(conversation.tags),
                f"",
            ])
        
        return "\n".join(lines)