"""
Unit tests for the TTS Queue System
"""

import asyncio
import pytest
import time
import threading
from unittest.mock import Mock, patch, AsyncMock
from tts_queue_system import (
    TTSQueueManager, TTSWorker, AudioManager, RateLimiter,
    TTSMessage, MessagePriority, TTSStatus, TTSConfig
)


class TestTTSMessage:
    """Test TTSMessage functionality"""
    
    def test_message_creation(self):
        """Test basic message creation"""
        message = TTSMessage(
            text="Hello world",
            priority=MessagePriority.HIGH,
            created_by="test"
        )
        
        assert message.text == "Hello world"
        assert message.priority == MessagePriority.HIGH
        assert message.created_by == "test"
        assert message.status == TTSStatus.PENDING
        assert message.retry_count == 0
    
    def test_message_priority_ordering(self):
        """Test priority queue ordering"""
        high_priority = TTSMessage(text="urgent", priority=MessagePriority.HIGH)
        low_priority = TTSMessage(text="normal", priority=MessagePriority.LOW)
        
        # Higher priority should come first
        assert high_priority < low_priority
        assert not (low_priority < high_priority)
    
    def test_message_timestamp_ordering(self):
        """Test timestamp-based ordering for same priority"""
        message1 = TTSMessage(text="first", priority=MessagePriority.NORMAL)
        time.sleep(0.01)  # Small delay
        message2 = TTSMessage(text="second", priority=MessagePriority.NORMAL)
        
        # Earlier timestamp should come first
        assert message1 < message2


class TestAudioManager:
    """Test AudioManager functionality"""
    
    def test_audio_manager_creation(self):
        """Test AudioManager initialization"""
        config = TTSConfig()
        audio_manager = AudioManager(config)
        
        assert audio_manager.config == config
        assert audio_manager.current_audio_end_time == 0
    
    def test_can_play_audio(self):
        """Test audio overlap detection"""
        config = TTSConfig()
        audio_manager = AudioManager(config)
        
        # Should be able to play when no audio is playing
        assert audio_manager.can_play_audio(1.0) is True
        
        # Schedule some audio
        audio_manager.schedule_audio(2.0)
        
        # Should not be able to play immediately after
        assert audio_manager.can_play_audio(1.0) is False
    
    def test_schedule_audio(self):
        """Test audio scheduling"""
        config = TTSConfig()
        audio_manager = AudioManager(config)
        
        start_time = audio_manager.schedule_audio(1.5)
        current_time = time.time()
        
        # Start time should be close to current time
        assert abs(start_time - current_time) < 0.1
        
        # End time should be set correctly
        assert audio_manager.current_audio_end_time == start_time + 1.5
    
    def test_estimate_duration(self):
        """Test duration estimation"""
        config = TTSConfig()
        audio_manager = AudioManager(config)
        
        # Test with different text lengths
        short_text = "Hello"
        long_text = "This is a much longer text that should take more time to speak"
        
        short_duration = audio_manager.estimate_duration(short_text)
        long_duration = audio_manager.estimate_duration(long_text)
        
        assert short_duration > 0
        assert long_duration > short_duration
        assert long_duration >= 0.5  # Minimum duration


class TestRateLimiter:
    """Test RateLimiter functionality"""
    
    def test_rate_limiter_creation(self):
        """Test RateLimiter initialization"""
        config = TTSConfig(rate_limit_per_minute=10)
        rate_limiter = RateLimiter(config)
        
        assert rate_limiter.config == config
        assert len(rate_limiter.requests) == 0
    
    def test_rate_limiting_disabled(self):
        """Test rate limiting when disabled"""
        config = TTSConfig(enable_rate_limiting=False)
        rate_limiter = RateLimiter(config)
        
        # Should always allow when disabled
        for _ in range(100):
            assert rate_limiter.can_process() is True
    
    def test_rate_limiting_enabled(self):
        """Test rate limiting when enabled"""
        config = TTSConfig(rate_limit_per_minute=2)
        rate_limiter = RateLimiter(config)
        
        # First two requests should be allowed
        assert rate_limiter.can_process() is True
        assert rate_limiter.can_process() is True
        
        # Third request should be blocked
        assert rate_limiter.can_process() is False
    
    def test_rate_limiting_reset(self):
        """Test rate limiting reset over time"""
        config = TTSConfig(rate_limit_per_minute=1)
        rate_limiter = RateLimiter(config)
        
        # Use up the limit
        assert rate_limiter.can_process() is True
        assert rate_limiter.can_process() is False
        
        # Manually reset by modifying the requests list
        rate_limiter.requests = []
        
        # Should be able to process again
        assert rate_limiter.can_process() is True


class TestTTSWorker:
    """Test TTSWorker functionality"""
    
    @pytest.fixture
    def worker(self):
        """Create a test worker"""
        config = TTSConfig()
        audio_manager = AudioManager(config)
        return TTSWorker(0, config, audio_manager)
    
    def test_worker_creation(self, worker):
        """Test worker initialization"""
        assert worker.worker_id == 0
        assert worker.is_running is False
        assert worker.current_message is None
    
    @pytest.mark.asyncio
    async def test_process_message_success(self, worker):
        """Test successful message processing"""
        message = TTSMessage(text="Hello world", priority=MessagePriority.NORMAL)
        mock_tts_engine = AsyncMock(return_value=b"audio_data")
        
        # Mock the audio generation and playback
        with patch.object(worker, '_generate_audio', new_callable=AsyncMock) as mock_generate, \
             patch.object(worker, '_play_audio', new_callable=AsyncMock) as mock_play:
            
            mock_generate.return_value = b"audio_data"
            
            result = await worker.process_message(message, mock_tts_engine)
            
            assert result is True
            assert message.status == TTSStatus.COMPLETED
            mock_generate.assert_called_once()
            mock_play.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_message_failure(self, worker):
        """Test message processing failure"""
        message = TTSMessage(text="Hello world", priority=MessagePriority.NORMAL)
        mock_tts_engine = AsyncMock(side_effect=Exception("TTS Error"))
        
        result = await worker.process_message(message, mock_tts_engine)
        
        assert result is False
        assert message.status == TTSStatus.FAILED


class TestTTSQueueManager:
    """Test TTSQueueManager functionality"""
    
    @pytest.fixture
    def tts_manager(self):
        """Create a test TTS manager"""
        config = TTSConfig(max_concurrent_workers=1, max_queue_size=10)
        return TTSQueueManager(config)
    
    def test_manager_creation(self, tts_manager):
        """Test manager initialization"""
        assert tts_manager.is_running is False
        assert len(tts_manager.workers) == 0
        assert tts_manager.tts_engine is None
    
    def test_set_tts_engine(self, tts_manager):
        """Test setting TTS engine"""
        mock_engine = Mock()
        tts_manager.set_tts_engine(mock_engine)
        assert tts_manager.tts_engine == mock_engine
    
    def test_add_message(self, tts_manager):
        """Test adding messages to queue"""
        # Should fail when not running
        with pytest.raises(RuntimeError, match="TTS queue system is not running"):
            tts_manager.add_message("Hello world")
        
        # Start the manager
        asyncio.run(tts_manager.start())
        
        try:
            # Should succeed when running
            message_id = tts_manager.add_message(
                text="Hello world",
                priority=MessagePriority.NORMAL,
                created_by="test"
            )
            assert message_id is not None
            assert len(message_id) > 0
        finally:
            asyncio.run(tts_manager.stop())
    
    def test_add_message_queue_full(self, tts_manager):
        """Test adding message when queue is full"""
        # Create manager with very small queue
        config = TTSConfig(max_queue_size=1)
        small_manager = TTSQueueManager(config)
        asyncio.run(small_manager.start())
        
        try:
            # Fill the queue
            small_manager.add_message("First message")
            
            # This should fail
            with pytest.raises(RuntimeError, match="TTS queue is full"):
                small_manager.add_message("Second message")
        finally:
            asyncio.run(small_manager.stop())
    
    def test_get_stats(self, tts_manager):
        """Test getting statistics"""
        stats = tts_manager.get_stats()
        
        assert "total_processed" in stats
        assert "total_failed" in stats
        assert "queue_size" in stats
        assert "is_running" in stats
        assert "active_workers" in stats
        
        assert stats["total_processed"] == 0
        assert stats["total_failed"] == 0
        assert stats["queue_size"] == 0
        assert stats["is_running"] is False
    
    def test_clear_queue(self, tts_manager):
        """Test clearing the queue"""
        # Add some messages
        tts_manager.message_queue.put(TTSMessage(text="Message 1"))
        tts_manager.message_queue.put(TTSMessage(text="Message 2"))
        
        assert tts_manager.message_queue.qsize() == 2
        
        # Clear the queue
        tts_manager.clear_queue()
        
        assert tts_manager.message_queue.qsize() == 0


class TestIntegration:
    """Integration tests for the complete system"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete workflow from message addition to processing"""
        config = TTSConfig(
            max_concurrent_workers=1,
            max_queue_size=5,
            rate_limit_per_minute=10
        )
        
        manager = TTSQueueManager(config)
        
        # Mock TTS engine
        async def mock_tts_engine(text: str, **kwargs) -> bytes:
            await asyncio.sleep(0.1)  # Simulate processing time
            return b"mock_audio"
        
        manager.set_tts_engine(mock_tts_engine)
        
        # Start the manager
        await manager.start()
        
        try:
            # Add multiple messages with different priorities
            message_ids = []
            message_ids.append(manager.add_message("High priority", MessagePriority.HIGH))
            message_ids.append(manager.add_message("Normal priority", MessagePriority.NORMAL))
            message_ids.append(manager.add_message("Low priority", MessagePriority.LOW))
            
            # Wait for processing
            await asyncio.sleep(2)
            
            # Check stats
            stats = manager.get_stats()
            assert stats["total_processed"] > 0
            assert stats["is_running"] is True
            
        finally:
            await manager.stop()
    
    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        """Test that messages are processed in priority order"""
        config = TTSConfig(max_concurrent_workers=1, max_queue_size=10)
        manager = TTSQueueManager(config)
        
        # Track processing order
        processing_order = []
        
        async def mock_tts_engine(text: str, **kwargs) -> bytes:
            processing_order.append(text)
            await asyncio.sleep(0.1)
            return b"mock_audio"
        
        manager.set_tts_engine(mock_tts_engine)
        await manager.start()
        
        try:
            # Add messages in reverse priority order
            manager.add_message("Low priority", MessagePriority.LOW)
            manager.add_message("High priority", MessagePriority.HIGH)
            manager.add_message("Normal priority", MessagePriority.NORMAL)
            
            # Wait for processing
            await asyncio.sleep(1)
            
            # High priority should be processed first
            assert len(processing_order) >= 1
            assert processing_order[0] == "High priority"
            
        finally:
            await manager.stop()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])