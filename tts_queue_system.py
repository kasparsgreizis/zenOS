"""
TTS Queue System for Voice Models/Agents

A robust queue system designed to handle high-frequency text-to-speech requests
from sources like streamer donation messages, preventing race conditions and
ensuring proper audio playback ordering.

Key Features:
- Thread-safe queue operations
- Priority-based message handling
- Audio overlap prevention
- Configurable TTS settings
- Rate limiting and throttling
- Graceful error handling
"""

import asyncio
import threading
import time
import queue
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
import json
import uuid


class MessagePriority(Enum):
    """Priority levels for TTS messages"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class TTSStatus(Enum):
    """Status of TTS operations"""
    PENDING = "pending"
    PROCESSING = "processing"
    PLAYING = "playing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TTSMessage:
    """Represents a TTS message in the queue"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: TTSStatus = TTSStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    created_by: str = "unknown"
    
    def __lt__(self, other):
        """Priority queue ordering (higher priority first, then by timestamp)"""
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        return self.timestamp < other.timestamp


@dataclass
class TTSConfig:
    """Configuration for TTS system"""
    max_queue_size: int = 1000
    max_concurrent_workers: int = 3
    audio_overlap_threshold: float = 0.1  # seconds
    rate_limit_per_minute: int = 60
    default_voice: str = "default"
    audio_format: str = "wav"
    sample_rate: int = 22050
    enable_priority_queue: bool = True
    enable_rate_limiting: bool = True
    log_level: str = "INFO"


class AudioManager:
    """Manages audio playback and prevents overlaps"""
    
    def __init__(self, config: TTSConfig):
        self.config = config
        self.current_audio_end_time = 0
        self.audio_lock = threading.Lock()
        self.logger = logging.getLogger(__name__ + ".AudioManager")
    
    def can_play_audio(self, estimated_duration: float) -> bool:
        """Check if audio can be played without overlap"""
        with self.audio_lock:
            current_time = time.time()
            if current_time >= self.current_audio_end_time:
                return True
            
            # Check if there's enough gap for new audio
            time_until_available = self.current_audio_end_time - current_time
            return time_until_available <= self.config.audio_overlap_threshold
    
    def schedule_audio(self, estimated_duration: float) -> float:
        """Schedule audio playback and return start time"""
        with self.audio_lock:
            current_time = time.time()
            start_time = max(current_time, self.current_audio_end_time)
            self.current_audio_end_time = start_time + estimated_duration
            return start_time
    
    def estimate_duration(self, text: str) -> float:
        """Estimate audio duration based on text length"""
        # Rough estimation: ~150 words per minute, ~2.5 characters per word
        words = len(text.split())
        duration = (words / 150) * 60  # seconds
        return max(duration, 0.5)  # Minimum 0.5 seconds


class RateLimiter:
    """Rate limiter to prevent overwhelming the TTS system"""
    
    def __init__(self, config: TTSConfig):
        self.config = config
        self.requests = []
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__ + ".RateLimiter")
    
    def can_process(self) -> bool:
        """Check if a new request can be processed within rate limits"""
        if not self.config.enable_rate_limiting:
            return True
        
        with self.lock:
            current_time = time.time()
            # Remove requests older than 1 minute
            self.requests = [req_time for req_time in self.requests 
                           if current_time - req_time < 60]
            
            if len(self.requests) >= self.config.rate_limit_per_minute:
                self.logger.warning(f"Rate limit exceeded: {len(self.requests)} requests in last minute")
                return False
            
            self.requests.append(current_time)
            return True


class TTSWorker:
    """Worker thread for processing TTS requests"""
    
    def __init__(self, worker_id: int, config: TTSConfig, audio_manager: AudioManager):
        self.worker_id = worker_id
        self.config = config
        self.audio_manager = audio_manager
        self.logger = logging.getLogger(__name__ + f".Worker{worker_id}")
        self.is_running = False
        self.current_message: Optional[TTSMessage] = None
    
    async def process_message(self, message: TTSMessage, tts_engine: Callable) -> bool:
        """Process a single TTS message"""
        try:
            self.current_message = message
            message.status = TTSStatus.PROCESSING
            
            self.logger.info(f"Processing message {message.id}: '{message.text[:50]}...'")
            
            # Estimate duration and check if we can play
            estimated_duration = self.audio_manager.estimate_duration(message.text)
            
            if not self.audio_manager.can_play_audio(estimated_duration):
                self.logger.info(f"Audio overlap detected, waiting for slot for message {message.id}")
                # Wait for audio slot
                while not self.audio_manager.can_play_audio(estimated_duration):
                    await asyncio.sleep(0.1)
            
            # Schedule audio playback
            start_time = self.audio_manager.schedule_audio(estimated_duration)
            
            # Generate TTS audio
            audio_data = await self._generate_audio(message, tts_engine)
            
            # Wait until it's time to play
            current_time = time.time()
            if start_time > current_time:
                await asyncio.sleep(start_time - current_time)
            
            # Play audio
            message.status = TTSStatus.PLAYING
            await self._play_audio(audio_data, message)
            
            message.status = TTSStatus.COMPLETED
            self.logger.info(f"Completed message {message.id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing message {message.id}: {e}")
            message.status = TTSStatus.FAILED
            return False
        finally:
            self.current_message = None
    
    async def _generate_audio(self, message: TTSMessage, tts_engine: Callable) -> bytes:
        """Generate audio using the TTS engine"""
        # This is a placeholder - replace with actual TTS engine call
        # For example: return await tts_engine(message.text, voice=message.metadata.get('voice', self.config.default_voice))
        
        # Simulate TTS processing time
        await asyncio.sleep(0.1)
        
        # Return dummy audio data (in real implementation, this would be actual audio)
        return b"dummy_audio_data"
    
    async def _play_audio(self, audio_data: bytes, message: TTSMessage) -> None:
        """Play the generated audio"""
        # This is a placeholder - replace with actual audio playback
        # For example: pygame.mixer.music.load(io.BytesIO(audio_data))
        
        # Simulate audio playback time
        estimated_duration = self.audio_manager.estimate_duration(message.text)
        await asyncio.sleep(estimated_duration)


class TTSQueueManager:
    """Main TTS queue manager"""
    
    def __init__(self, config: TTSConfig = None):
        self.config = config or TTSConfig()
        self.logger = logging.getLogger(__name__ + ".QueueManager")
        
        # Initialize components
        self.audio_manager = AudioManager(self.config)
        self.rate_limiter = RateLimiter(self.config)
        
        # Queue setup
        if self.config.enable_priority_queue:
            self.message_queue = queue.PriorityQueue(maxsize=self.config.max_queue_size)
        else:
            self.message_queue = queue.Queue(maxsize=self.config.max_queue_size)
        
        # Worker management
        self.workers: List[TTSWorker] = []
        self.worker_pool = ThreadPoolExecutor(max_workers=self.config.max_concurrent_workers)
        self.is_running = False
        self.tts_engine: Optional[Callable] = None
        
        # Statistics
        self.stats = {
            "total_processed": 0,
            "total_failed": 0,
            "queue_size": 0,
            "active_workers": 0
        }
        
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def set_tts_engine(self, tts_engine: Callable):
        """Set the TTS engine function"""
        self.tts_engine = tts_engine
    
    async def start(self):
        """Start the TTS queue system"""
        if self.is_running:
            self.logger.warning("TTS queue system is already running")
            return
        
        self.is_running = True
        self.logger.info("Starting TTS queue system")
        
        # Start worker tasks
        for i in range(self.config.max_concurrent_workers):
            worker = TTSWorker(i, self.config, self.audio_manager)
            self.workers.append(worker)
            asyncio.create_task(self._worker_loop(worker))
        
        self.logger.info(f"Started {len(self.workers)} TTS workers")
    
    async def stop(self):
        """Stop the TTS queue system"""
        self.is_running = False
        self.logger.info("Stopping TTS queue system")
        
        # Wait for workers to finish
        await asyncio.sleep(1)
        self.worker_pool.shutdown(wait=True)
    
    async def _worker_loop(self, worker: TTSWorker):
        """Main worker loop"""
        while self.is_running:
            try:
                # Get message from queue
                if self.config.enable_priority_queue:
                    message = self.message_queue.get_nowait()
                else:
                    message = self.message_queue.get_nowait()
                
                # Check rate limiting
                if not self.rate_limiter.can_process():
                    # Re-queue message with lower priority
                    message.priority = MessagePriority.LOW
                    self.message_queue.put(message)
                    await asyncio.sleep(1)
                    continue
                
                # Process message
                success = await worker.process_message(message, self.tts_engine)
                
                if success:
                    self.stats["total_processed"] += 1
                else:
                    self.stats["total_failed"] += 1
                
                self.stats["queue_size"] = self.message_queue.qsize()
                
            except queue.Empty:
                await asyncio.sleep(0.1)
            except Exception as e:
                self.logger.error(f"Worker error: {e}")
                await asyncio.sleep(1)
    
    def add_message(self, text: str, priority: MessagePriority = MessagePriority.NORMAL, 
                   metadata: Dict[str, Any] = None, created_by: str = "unknown") -> str:
        """Add a message to the TTS queue"""
        if not self.is_running:
            raise RuntimeError("TTS queue system is not running")
        
        message = TTSMessage(
            text=text,
            priority=priority,
            metadata=metadata or {},
            created_by=created_by
        )
        
        try:
            self.message_queue.put_nowait(message)
            self.logger.info(f"Added message {message.id} to queue: '{text[:50]}...'")
            return message.id
        except queue.Full:
            self.logger.error("Queue is full, dropping message")
            raise RuntimeError("TTS queue is full")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        return {
            **self.stats,
            "queue_size": self.message_queue.qsize(),
            "is_running": self.is_running,
            "active_workers": len([w for w in self.workers if w.current_message is not None])
        }
    
    def clear_queue(self):
        """Clear all pending messages from the queue"""
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except queue.Empty:
                break
        self.logger.info("Queue cleared")


# Example usage and configuration
async def example_usage():
    """Example demonstrating the TTS queue system"""
    
    # Create configuration
    config = TTSConfig(
        max_queue_size=500,
        max_concurrent_workers=2,
        rate_limit_per_minute=30,
        enable_priority_queue=True
    )
    
    # Create TTS queue manager
    tts_manager = TTSQueueManager(config)
    
    # Set up a mock TTS engine (replace with actual TTS engine)
    async def mock_tts_engine(text: str, **kwargs) -> bytes:
        print(f"Generating TTS for: {text}")
        await asyncio.sleep(0.2)  # Simulate TTS processing
        return b"mock_audio_data"
    
    tts_manager.set_tts_engine(mock_tts_engine)
    
    # Start the system
    await tts_manager.start()
    
    try:
        # Simulate donation messages with different priorities
        donation_messages = [
            ("Thank you for the $5 donation, John!", MessagePriority.HIGH, "donation"),
            ("New subscriber: Sarah! Welcome to the community!", MessagePriority.NORMAL, "subscription"),
            ("$50 donation from Mike! That's amazing!", MessagePriority.URGENT, "donation"),
            ("Regular chat message", MessagePriority.LOW, "chat"),
            ("$100 donation from VIP user! Incredible!", MessagePriority.URGENT, "donation"),
        ]
        
        # Add messages to queue
        for text, priority, msg_type in donation_messages:
            message_id = tts_manager.add_message(
                text=text,
                priority=priority,
                metadata={"type": msg_type, "amount": "$5" if "donation" in text else None},
                created_by="streamer_bot"
            )
            print(f"Added message {message_id}")
        
        # Let the system process messages
        await asyncio.sleep(10)
        
        # Print statistics
        stats = tts_manager.get_stats()
        print(f"Final stats: {json.dumps(stats, indent=2)}")
        
    finally:
        await tts_manager.stop()


if __name__ == "__main__":
    # Run the example
    asyncio.run(example_usage())