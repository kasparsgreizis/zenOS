"""
Conversation processing and knowledge extraction for PKM module.
"""

import asyncio
import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

from .config import PKMConfig
from .models import Conversation, KnowledgeEntry, Message, MessageRole
from .storage import PKMStorage


class ConversationProcessor:
    """Process conversations to extract knowledge and insights."""
    
    def __init__(self, config: PKMConfig, storage: PKMStorage):
        self.config = config
        self.storage = storage
    
    async def process_conversation(self, conversation: Conversation) -> Conversation:
        """Process a conversation to extract insights and knowledge."""
        # Generate summary if enabled
        if self.config.auto_summarize:
            conversation.summary = await self._generate_summary(conversation)
        
        # Extract keywords if enabled
        if self.config.extract_keywords:
            conversation.keywords = await self._extract_keywords(conversation)
        
        # Generate tags if enabled
        if self.config.generate_tags:
            conversation.tags = await self._generate_tags(conversation)
        
        # Extract knowledge entries
        knowledge_entries = await self._extract_knowledge_entries(conversation)
        
        # Save knowledge entries
        for entry in knowledge_entries:
            self.storage.save_knowledge_entry(entry)
        
        # Update conversation metadata
        conversation.metadata.update({
            "processed_at": datetime.now().isoformat(),
            "knowledge_entries_count": len(knowledge_entries),
            "processing_version": "1.0.0"
        })
        
        return conversation
    
    async def _generate_summary(self, conversation: Conversation) -> str:
        """Generate a summary of the conversation."""
        # Simple extractive summarization
        # In a real implementation, you'd use an AI model for this
        
        user_messages = [msg.content for msg in conversation.messages if msg.role == MessageRole.USER]
        assistant_messages = [msg.content for msg in conversation.messages if msg.role == MessageRole.ASSISTANT]
        
        if not user_messages and not assistant_messages:
            return "Empty conversation"
        
        # Extract key topics from user messages
        user_topics = []
        for msg in user_messages:
            # Simple keyword extraction
            words = re.findall(r'\b\w+\b', msg.lower())
            # Filter out common words
            common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'this', 'that', 'these', 'those'}
            key_words = [word for word in words if len(word) > 3 and word not in common_words]
            user_topics.extend(key_words[:3])  # Take first 3 key words
        
        # Create summary
        summary_parts = []
        
        if user_topics:
            summary_parts.append(f"Topics discussed: {', '.join(set(user_topics)[:5])}")
        
        if len(conversation.messages) > 0:
            summary_parts.append(f"Conversation with {len(conversation.messages)} messages")
        
        if assistant_messages:
            # Extract key insights from assistant responses
            insights = []
            for msg in assistant_messages:
                # Look for sentences that might contain insights
                sentences = msg.split('.')
                for sentence in sentences:
                    if any(word in sentence.lower() for word in ['important', 'key', 'note', 'remember', 'consider', 'suggest', 'recommend']):
                        insights.append(sentence.strip())
                        if len(insights) >= 2:
                            break
            
            if insights:
                summary_parts.append(f"Key insights: {'; '.join(insights[:2])}")
        
        return '. '.join(summary_parts) if summary_parts else "No summary available"
    
    async def _extract_keywords(self, conversation: Conversation) -> List[str]:
        """Extract keywords from the conversation."""
        all_text = []
        
        for message in conversation.messages:
            all_text.append(message.content)
        
        combined_text = ' '.join(all_text).lower()
        
        # Simple keyword extraction
        words = re.findall(r'\b\w+\b', combined_text)
        
        # Filter out common words
        common_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
            'this', 'that', 'these', 'those', 'what', 'when', 'where', 'why', 'how', 'who',
            'yes', 'no', 'not', 'here', 'there', 'now', 'then', 'so', 'if', 'because'
        }
        
        # Count word frequencies
        word_counts = {}
        for word in words:
            if len(word) > 3 and word not in common_words:
                word_counts[word] = word_counts.get(word, 0) + 1
        
        # Sort by frequency and return top keywords
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:10]]
    
    async def _generate_tags(self, conversation: Conversation) -> List[str]:
        """Generate tags for the conversation."""
        tags = []
        
        # Extract tags from keywords
        keywords = await self._extract_keywords(conversation)
        tags.extend(keywords[:5])  # Use top 5 keywords as tags
        
        # Add topic-based tags
        all_text = ' '.join([msg.content for msg in conversation.messages]).lower()
        
        # Technical topics
        if any(word in all_text for word in ['code', 'programming', 'function', 'variable', 'algorithm']):
            tags.append('programming')
        
        if any(word in all_text for word in ['python', 'javascript', 'java', 'c++', 'html', 'css']):
            tags.append('coding')
        
        if any(word in all_text for word in ['ai', 'machine learning', 'neural', 'model', 'training']):
            tags.append('ai')
        
        if any(word in all_text for word in ['database', 'sql', 'query', 'table', 'index']):
            tags.append('database')
        
        # General topics
        if any(word in all_text for word in ['help', 'question', 'problem', 'issue', 'error']):
            tags.append('help')
        
        if any(word in all_text for word in ['explain', 'how', 'what', 'why', 'tutorial']):
            tags.append('explanation')
        
        if any(word in all_text for word in ['example', 'sample', 'demo', 'show']):
            tags.append('example')
        
        # Remove duplicates and limit
        return list(set(tags))[:10]
    
    async def _extract_knowledge_entries(self, conversation: Conversation) -> List[KnowledgeEntry]:
        """Extract knowledge entries from the conversation."""
        entries = []
        
        for i, message in enumerate(conversation.messages):
            if message.role == MessageRole.ASSISTANT:
                # Extract potential knowledge from assistant responses
                content = message.content
                
                # Look for code blocks
                code_blocks = re.findall(r'```[\s\S]*?```', content)
                for j, code_block in enumerate(code_blocks):
                    entry = KnowledgeEntry(
                        id=f"{conversation.id}_code_{i}_{j}",
                        title=f"Code from {conversation.title}",
                        content=code_block,
                        source_conversation_id=conversation.id,
                        source_message_index=i,
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        entry_type="code",
                        confidence=0.9,
                        tags=["code", "programming"],
                        keywords=await self._extract_keywords_from_text(code_block)
                    )
                    entries.append(entry)
                
                # Look for lists or structured information
                if re.search(r'^\d+\.|^[-*]', content, re.MULTILINE):
                    entry = KnowledgeEntry(
                        id=f"{conversation.id}_list_{i}",
                        title=f"List from {conversation.title}",
                        content=content,
                        source_conversation_id=conversation.id,
                        source_message_index=i,
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        entry_type="list",
                        confidence=0.8,
                        tags=["list", "structured"],
                        keywords=await self._extract_keywords_from_text(content)
                    )
                    entries.append(entry)
                
                # Look for definitions or explanations
                if any(word in content.lower() for word in ['definition', 'means', 'refers to', 'is a', 'are']):
                    entry = KnowledgeEntry(
                        id=f"{conversation.id}_definition_{i}",
                        title=f"Definition from {conversation.title}",
                        content=content,
                        source_conversation_id=conversation.id,
                        source_message_index=i,
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        entry_type="definition",
                        confidence=0.85,
                        tags=["definition", "explanation"],
                        keywords=await self._extract_keywords_from_text(content)
                    )
                    entries.append(entry)
        
        return entries
    
    async def _extract_keywords_from_text(self, text: str) -> List[str]:
        """Extract keywords from a text string."""
        words = re.findall(r'\b\w+\b', text.lower())
        common_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
            'this', 'that', 'these', 'those', 'what', 'when', 'where', 'why', 'how', 'who'
        }
        
        word_counts = {}
        for word in words:
            if len(word) > 3 and word not in common_words:
                word_counts[word] = word_counts.get(word, 0) + 1
        
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:5]]