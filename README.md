# TTS Queue System for Voice Models/Agents

A robust, thread-safe Text-to-Speech queue system designed to handle high-frequency TTS requests from sources like streamer donation messages, preventing race conditions and ensuring proper audio playback ordering.

## Features

- **Thread-Safe Operations**: Uses asyncio and threading for concurrent processing
- **Priority-Based Queue**: Different priority levels for different message types
- **Audio Overlap Prevention**: Prevents multiple audio streams from playing simultaneously
- **Rate Limiting**: Configurable rate limiting to prevent system overload
- **Multiple TTS Engine Support**: Works with pyttsx3, Google TTS, Azure Speech Services
- **Streamer Bot Integration**: Built-in support for donation, subscription, and chat messages
- **WebSocket API**: Real-time message handling via WebSocket
- **Comprehensive Testing**: Full test suite with unit and integration tests

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Basic Usage

```python
import asyncio
from tts_queue_system import TTSQueueManager, TTSConfig, MessagePriority

async def main():
    # Create configuration
    config = TTSConfig(
        max_queue_size=1000,
        max_concurrent_workers=3,
        rate_limit_per_minute=60
    )
    
    # Create TTS manager
    tts_manager = TTSQueueManager(config)
    
    # Set up TTS engine (example with pyttsx3)
    import pyttsx3
    engine = pyttsx3.init()
    
    async def tts_engine(text: str, **kwargs) -> bytes:
        # Your TTS implementation here
        return b"audio_data"
    
    tts_manager.set_tts_engine(tts_engine)
    
    # Start the system
    await tts_manager.start()
    
    # Add messages
    tts_manager.add_message("Hello world!", MessagePriority.NORMAL)
    tts_manager.add_message("Urgent message!", MessagePriority.URGENT)
    
    # Wait for processing
    await asyncio.sleep(5)
    
    # Stop the system
    await tts_manager.stop()

asyncio.run(main())
```

## Architecture

### Core Components

1. **TTSQueueManager**: Main orchestrator that manages the queue and workers
2. **TTSWorker**: Individual worker threads that process TTS requests
3. **AudioManager**: Handles audio playback scheduling and overlap prevention
4. **RateLimiter**: Implements rate limiting to prevent system overload
5. **TTSMessage**: Data structure representing a TTS request

### Priority System

Messages are processed based on priority levels:

- **URGENT**: High-value donations ($100+), critical alerts
- **HIGH**: Regular donations, subscriptions, follows, raids
- **NORMAL**: Commands, general alerts
- **LOW**: Regular chat messages (if enabled)

### Race Condition Prevention

The system prevents race conditions through:

1. **Thread-Safe Queues**: Using Python's `queue.PriorityQueue`
2. **Audio Overlap Detection**: Prevents multiple audio streams
3. **Atomic Operations**: All queue operations are atomic
4. **Worker Synchronization**: Coordinated worker management

## Streamer Bot Integration

The system includes built-in support for common streamer bot scenarios:

```python
from tts_integration_example import StreamerBotIntegration

# Create streamer bot
streamer_bot = StreamerBotIntegration(tts_manager)

# Process different types of events
streamer_bot.process_donation("VIP_User", 150.0, "Keep up the great work!")
streamer_bot.process_subscription("NewSub", 1, "First time subscribing!")
streamer_bot.process_follow("NewFollower")
streamer_bot.process_chat_message("Moderator", "!tts Welcome everyone!", is_mod=True)
```

## TTS Engine Integration

### pyttsx3 (Offline, Fast)

```python
from tts_integration_example import Pyttsx3TTSEngine

engine = Pyttsx3TTSEngine(voice_id="english", rate=200)
tts_manager.set_tts_engine(engine.generate_audio)
```

### Google Text-to-Speech (Online, High Quality)

```python
from tts_integration_example import GTTS_Engine

engine = GTTS_Engine(language='en', tld='com')
tts_manager.set_tts_engine(engine.generate_audio)
```

### Azure Speech Services (Enterprise)

```python
from tts_integration_example import AzureTTS_Engine

engine = AzureTTS_Engine(
    subscription_key="your_key",
    region="your_region",
    voice_name="en-US-AriaNeural"
)
tts_manager.set_tts_engine(engine.generate_audio)
```

## WebSocket API

Start a WebSocket server for real-time message handling:

```python
from tts_integration_example import WebSocketServer

# Create WebSocket server
server = WebSocketServer(streamer_bot, host="localhost", port=8765)

# Start server
await server.start_server()
```

### WebSocket Message Format

```json
{
  "type": "donation",
  "donor_name": "JohnDoe",
  "amount": 25.0,
  "message": "Great stream!"
}
```

## Configuration

The system can be configured via JSON:

```json
{
  "tts_queue": {
    "max_queue_size": 1000,
    "max_concurrent_workers": 3,
    "rate_limit_per_minute": 60,
    "enable_priority_queue": true
  },
  "streamer_bot": {
    "priorities": {
      "donation": "URGENT",
      "subscription": "HIGH",
      "chat": "LOW"
    }
  }
}
```

## Testing

Run the test suite:

```bash
pytest test_tts_queue_system.py -v
```

## Performance Considerations

### Queue Size
- Set `max_queue_size` based on expected peak load
- Monitor queue size via `get_stats()`

### Worker Count
- More workers = higher throughput but more resource usage
- Recommended: 2-4 workers for most use cases

### Rate Limiting
- Prevents overwhelming TTS engines
- Adjust `rate_limit_per_minute` based on TTS engine capabilities

### Memory Usage
- Each queued message consumes memory
- Consider implementing message persistence for very high loads

## Error Handling

The system includes comprehensive error handling:

- **Queue Full**: Raises `RuntimeError` when queue is full
- **TTS Engine Errors**: Retries failed messages up to `max_retries`
- **Audio Playback Errors**: Graceful fallback and logging
- **Worker Errors**: Automatic worker recovery

## Monitoring

Get real-time statistics:

```python
stats = tts_manager.get_stats()
print(f"Queue size: {stats['queue_size']}")
print(f"Processed: {stats['total_processed']}")
print(f"Failed: {stats['total_failed']}")
print(f"Active workers: {stats['active_workers']}")
```

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## Support

For issues and questions:
- Create an issue on GitHub
- Check the documentation
- Review the test cases for usage examples