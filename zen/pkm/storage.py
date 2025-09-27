"""
Storage and retrieval system for PKM module.
"""

import json
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any, Iterator
from dataclasses import asyncio

from .config import PKMConfig
from .models import Conversation, KnowledgeEntry, Message, MessageRole


class PKMStorage:
    """Storage system for PKM data."""
    
    def __init__(self, config: PKMConfig):
        self.config = config
        self.conversations_dir = config.conversations_dir
        self.knowledge_base_dir = config.knowledge_base_dir
        self.exports_dir = config.exports_dir
        
        # Ensure directories exist
        for directory in [self.conversations_dir, self.knowledge_base_dir, self.exports_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def save_conversation(self, conversation: Conversation) -> bool:
        """Save a conversation to storage."""
        try:
            # Save as JSON
            if self.config.storage_format in ["json", "both"]:
                json_path = self.conversations_dir / f"{conversation.id}.json"
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(conversation.to_dict(), f, indent=2, ensure_ascii=False)
                conversation.file_path = str(json_path)
                conversation.file_size = json_path.stat().st_size
            
            # Save as Markdown
            if self.config.storage_format in ["markdown", "both"]:
                md_path = self.conversations_dir / f"{conversation.id}.md"
                markdown_content = self._conversation_to_markdown(conversation)
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
            
            return True
            
        except Exception as e:
            print(f"Error saving conversation {conversation.id}: {e}")
            return False
    
    def load_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Load a conversation by ID."""
        json_path = self.conversations_dir / f"{conversation_id}.json"
        
        if not json_path.exists():
            return None
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return Conversation.from_dict(data)
        except Exception as e:
            print(f"Error loading conversation {conversation_id}: {e}")
            return None
    
    def list_conversations(self, limit: Optional[int] = None) -> List[Conversation]:
        """List all conversations."""
        conversations = []
        
        for json_file in self.conversations_dir.glob("*.json"):
            conversation = self.load_conversation(json_file.stem)
            if conversation:
                conversations.append(conversation)
        
        # Sort by updated_at descending
        conversations.sort(key=lambda x: x.updated_at, reverse=True)
        
        if limit:
            conversations = conversations[:limit]
        
        return conversations
    
    def search_conversations(self, query: str, limit: Optional[int] = None) -> List[Conversation]:
        """Search conversations by content."""
        results = []
        query_lower = query.lower()
        
        for conversation in self.list_conversations():
            # Search in title
            if query_lower in conversation.title.lower():
                results.append(conversation)
                continue
            
            # Search in messages
            for message in conversation.messages:
                if query_lower in message.content.lower():
                    results.append(conversation)
                    break
            
            # Search in summary
            if conversation.summary and query_lower in conversation.summary.lower():
                results.append(conversation)
                continue
        
        if limit:
            results = results[:limit]
        
        return results
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        try:
            # Delete JSON file
            json_path = self.conversations_dir / f"{conversation_id}.json"
            if json_path.exists():
                json_path.unlink()
            
            # Delete Markdown file
            md_path = self.conversations_dir / f"{conversation_id}.md"
            if md_path.exists():
                md_path.unlink()
            
            return True
            
        except Exception as e:
            print(f"Error deleting conversation {conversation_id}: {e}")
            return False
    
    def save_knowledge_entry(self, entry: KnowledgeEntry) -> bool:
        """Save a knowledge entry."""
        try:
            json_path = self.knowledge_base_dir / f"{entry.id}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(entry.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving knowledge entry {entry.id}: {e}")
            return False
    
    def load_knowledge_entry(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """Load a knowledge entry by ID."""
        json_path = self.knowledge_base_dir / f"{entry_id}.json"
        
        if not json_path.exists():
            return None
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return KnowledgeEntry(**data)
        except Exception as e:
            print(f"Error loading knowledge entry {entry_id}: {e}")
            return None
    
    def list_knowledge_entries(self, limit: Optional[int] = None) -> List[KnowledgeEntry]:
        """List all knowledge entries."""
        entries = []
        
        for json_file in self.knowledge_base_dir.glob("*.json"):
            entry = self.load_knowledge_entry(json_file.stem)
            if entry:
                entries.append(entry)
        
        # Sort by updated_at descending
        entries.sort(key=lambda x: x.updated_at, reverse=True)
        
        if limit:
            entries = entries[:limit]
        
        return entries
    
    def search_knowledge_entries(self, query: str, limit: Optional[int] = None) -> List[KnowledgeEntry]:
        """Search knowledge entries by content."""
        results = []
        query_lower = query.lower()
        
        for entry in self.list_knowledge_entries():
            # Search in title
            if query_lower in entry.title.lower():
                results.append(entry)
                continue
            
            # Search in content
            if query_lower in entry.content.lower():
                results.append(entry)
                continue
            
            # Search in tags
            for tag in entry.tags:
                if query_lower in tag.lower():
                    results.append(entry)
                    break
        
        if limit:
            results = results[:limit]
        
        return results
    
    def export_conversations(self, format: str = "json", limit: Optional[int] = None) -> Path:
        """Export conversations to a file."""
        conversations = self.list_conversations(limit)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "json":
            export_path = self.exports_dir / f"conversations_{timestamp}.json"
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump([conv.to_dict() for conv in conversations], f, indent=2, ensure_ascii=False)
        
        elif format == "markdown":
            export_path = self.exports_dir / f"conversations_{timestamp}.md"
            with open(export_path, 'w', encoding='utf-8') as f:
                for conversation in conversations:
                    f.write(self._conversation_to_markdown(conversation))
                    f.write("\n\n---\n\n")
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        return export_path
    
    def export_knowledge_base(self, format: str = "json", limit: Optional[int] = None) -> Path:
        """Export knowledge base to a file."""
        entries = self.list_knowledge_entries(limit)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "json":
            export_path = self.exports_dir / f"knowledge_base_{timestamp}.json"
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump([entry.to_dict() for entry in entries], f, indent=2, ensure_ascii=False)
        
        elif format == "markdown":
            export_path = self.exports_dir / f"knowledge_base_{timestamp}.md"
            with open(export_path, 'w', encoding='utf-8') as f:
                for entry in entries:
                    f.write(f"# {entry.title}\n\n")
                    f.write(f"**Type:** {entry.entry_type}\n")
                    f.write(f"**Confidence:** {entry.confidence}\n")
                    f.write(f"**Tags:** {', '.join(entry.tags)}\n\n")
                    f.write(entry.content)
                    f.write("\n\n---\n\n")
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        return export_path
    
    def cleanup_old_data(self, days: int = 30) -> int:
        """Clean up old data files."""
        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned_count = 0
        
        # Clean up old conversations
        for json_file in self.conversations_dir.glob("*.json"):
            if json_file.stat().st_mtime < cutoff_date.timestamp():
                # Compress if enabled
                if self.config.compress_old_conversations:
                    compressed_path = json_file.with_suffix('.json.gz')
                    with open(json_file, 'rb') as f_in:
                        with gzip.open(compressed_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    json_file.unlink()
                else:
                    json_file.unlink()
                cleaned_count += 1
        
        return cleaned_count
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        conversations = self.list_conversations()
        knowledge_entries = self.list_knowledge_entries()
        
        total_size = 0
        for file_path in self.conversations_dir.glob("*.json"):
            total_size += file_path.stat().st_size
        
        for file_path in self.knowledge_base_dir.glob("*.json"):
            total_size += file_path.stat().st_size
        
        return {
            "conversations_count": len(conversations),
            "knowledge_entries_count": len(knowledge_entries),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "conversations_dir": str(self.conversations_dir),
            "knowledge_base_dir": str(self.knowledge_base_dir),
            "exports_dir": str(self.exports_dir),
        }
    
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