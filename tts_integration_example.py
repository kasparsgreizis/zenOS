"""
TTS Queue System Integration Examples

This file demonstrates how to integrate the TTS queue system with:
- Real TTS engines (pyttsx3, gTTS, Azure Speech, etc.)
- Audio playback libraries (pygame, pydub, etc.)
- Streamer bot integration
- WebSocket/API endpoints for real-time message handling
"""

import asyncio
import json
import logging
import websockets
from typing import Dict, Any, Optional
from tts_queue_system import TTSQueueManager, TTSConfig, MessagePriority, TTSMessage

# Optional imports for different TTS engines
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

try:
    from gtts import gTTS
    import pygame
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False


class Pyttsx3TTSEngine:
    """TTS engine using pyttsx3 (offline, fast)"""
    
    def __init__(self, voice_id: str = None, rate: int = 200):
        if not PYTTSX3_AVAILABLE:
            raise ImportError("pyttsx3 not available. Install with: pip install pyttsx3")
        
        self.engine = pyttsx3.init()
        
        # Set voice
        voices = self.engine.getProperty('voices')
        if voice_id and voices:
            for voice in voices:
                if voice_id in voice.id:
                    self.engine.setProperty('voice', voice.id)
                    break
        
        # Set rate
        self.engine.setProperty('rate', rate)
        
        # Set volume
        self.engine.setProperty('volume', 0.9)
    
    async def generate_audio(self, text: str, **kwargs) -> bytes:
        """Generate audio using pyttsx3"""
        # pyttsx3 doesn't return audio data directly, so we'll use a workaround
        # In a real implementation, you might want to use a different approach
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            self.engine.save_to_file(text, tmp_file.name)
            self.engine.runAndWait()
            
            with open(tmp_file.name, 'rb') as f:
                audio_data = f.read()
            
            os.unlink(tmp_file.name)
            return audio_data


class GTTS_Engine:
    """TTS engine using Google Text-to-Speech (online, high quality)"""
    
    def __init__(self, language: str = 'en', tld: str = 'com'):
        if not GTTS_AVAILABLE:
            raise ImportError("gTTS not available. Install with: pip install gtts pygame")
        
        self.language = language
        self.tld = tld
        pygame.mixer.init()
    
    async def generate_audio(self, text: str, **kwargs) -> bytes:
        """Generate audio using gTTS"""
        tts = gTTS(text=text, lang=self.language, tld=self.tld)
        
        # Save to temporary file
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
            tts.save(tmp_file.name)
            
            with open(tmp_file.name, 'rb') as f:
                audio_data = f.read()
            
            os.unlink(tmp_file.name)
            return audio_data
    
    async def play_audio(self, audio_data: bytes) -> None:
        """Play audio using pygame"""
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
            tmp_file.write(audio_data)
            tmp_file.flush()
            
            pygame.mixer.music.load(tmp_file.name)
            pygame.mixer.music.play()
            
            # Wait for playback to complete
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
            
            os.unlink(tmp_file.name)


class AzureTTS_Engine:
    """TTS engine using Azure Cognitive Services Speech"""
    
    def __init__(self, subscription_key: str, region: str, voice_name: str = "en-US-AriaNeural"):
        if not AZURE_AVAILABLE:
            raise ImportError("Azure Speech SDK not available. Install with: pip install azure-cognitiveservices-speech")
        
        self.subscription_key = subscription_key
        self.region = region
        self.voice_name = voice_name
        
        # Configure speech synthesis
        self.speech_config = speechsdk.SpeechConfig(
            subscription=subscription_key,
            region=region
        )
        self.speech_config.speech_synthesis_voice_name = voice_name
        self.speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
        )
    
    async def generate_audio(self, text: str, **kwargs) -> bytes:
        """Generate audio using Azure Speech Services"""
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config)
        
        result = synthesizer.speak_text_async(text).get()
        
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return result.audio_data
        else:
            raise Exception(f"Speech synthesis failed: {result.reason}")


class StreamerBotIntegration:
    """Integration class for streamer bot scenarios"""
    
    def __init__(self, tts_manager: TTSQueueManager):
        self.tts_manager = tts_manager
        self.logger = logging.getLogger(__name__ + ".StreamerBot")
        
        # Message type priorities
        self.priority_map = {
            "donation": MessagePriority.URGENT,
            "subscription": MessagePriority.HIGH,
            "follow": MessagePriority.HIGH,
            "raid": MessagePriority.HIGH,
            "host": MessagePriority.HIGH,
            "alert": MessagePriority.NORMAL,
            "chat": MessagePriority.LOW,
            "command": MessagePriority.NORMAL
        }
    
    def process_donation(self, donor_name: str, amount: float, message: str = ""):
        """Process a donation message"""
        if amount >= 100:
            priority = MessagePriority.URGENT
            text = f"WOW! {donor_name} just donated ${amount}! {message}".strip()
        elif amount >= 50:
            priority = MessagePriority.HIGH
            text = f"Amazing! {donor_name} donated ${amount}! {message}".strip()
        else:
            priority = MessagePriority.HIGH
            text = f"Thank you {donor_name} for the ${amount} donation! {message}".strip()
        
        return self.tts_manager.add_message(
            text=text,
            priority=priority,
            metadata={
                "type": "donation",
                "donor": donor_name,
                "amount": amount,
                "message": message
            },
            created_by="donation_handler"
        )
    
    def process_subscription(self, subscriber_name: str, months: int = 1, message: str = ""):
        """Process a subscription message"""
        if months >= 12:
            text = f"VIP subscriber {subscriber_name} has been subscribed for {months} months! {message}".strip()
            priority = MessagePriority.URGENT
        else:
            text = f"New subscriber {subscriber_name}! Welcome! {message}".strip()
            priority = MessagePriority.HIGH
        
        return self.tts_manager.add_message(
            text=text,
            priority=priority,
            metadata={
                "type": "subscription",
                "subscriber": subscriber_name,
                "months": months,
                "message": message
            },
            created_by="subscription_handler"
        )
    
    def process_follow(self, follower_name: str):
        """Process a follow message"""
        return self.tts_manager.add_message(
            text=f"New follower {follower_name}! Thanks for following!",
            priority=MessagePriority.HIGH,
            metadata={
                "type": "follow",
                "follower": follower_name
            },
            created_by="follow_handler"
        )
    
    def process_chat_message(self, username: str, message: str, is_mod: bool = False):
        """Process a chat message (only if it's from a mod or contains keywords)"""
        # Only process mod messages or messages with specific keywords
        keywords = ["!tts", "!say", "!announce"]
        should_process = is_mod or any(keyword in message.lower() for keyword in keywords)
        
        if should_process:
            # Remove command prefix if present
            clean_message = message
            for keyword in keywords:
                if keyword in message.lower():
                    clean_message = message.lower().replace(keyword, "").strip()
                    break
            
            return self.tts_manager.add_message(
                text=clean_message,
                priority=MessagePriority.LOW if not is_mod else MessagePriority.NORMAL,
                metadata={
                    "type": "chat",
                    "username": username,
                    "is_mod": is_mod,
                    "original_message": message
                },
                created_by="chat_handler"
            )
        
        return None


class WebSocketServer:
    """WebSocket server for real-time message handling"""
    
    def __init__(self, streamer_bot: StreamerBotIntegration, host: str = "localhost", port: int = 8765):
        self.streamer_bot = streamer_bot
        self.host = host
        self.port = port
        self.logger = logging.getLogger(__name__ + ".WebSocketServer")
    
    async def handle_message(self, websocket, path):
        """Handle incoming WebSocket messages"""
        async for message in websocket:
            try:
                data = json.loads(message)
                message_type = data.get("type")
                
                if message_type == "donation":
                    message_id = self.streamer_bot.process_donation(
                        donor_name=data["donor_name"],
                        amount=data["amount"],
                        message=data.get("message", "")
                    )
                    await websocket.send(json.dumps({"status": "queued", "message_id": message_id}))
                
                elif message_type == "subscription":
                    message_id = self.streamer_bot.process_subscription(
                        subscriber_name=data["subscriber_name"],
                        months=data.get("months", 1),
                        message=data.get("message", "")
                    )
                    await websocket.send(json.dumps({"status": "queued", "message_id": message_id}))
                
                elif message_type == "follow":
                    message_id = self.streamer_bot.process_follow(
                        follower_name=data["follower_name"]
                    )
                    await websocket.send(json.dumps({"status": "queued", "message_id": message_id}))
                
                elif message_type == "chat":
                    message_id = self.streamer_bot.process_chat_message(
                        username=data["username"],
                        message=data["message"],
                        is_mod=data.get("is_mod", False)
                    )
                    if message_id:
                        await websocket.send(json.dumps({"status": "queued", "message_id": message_id}))
                    else:
                        await websocket.send(json.dumps({"status": "ignored"}))
                
                elif message_type == "stats":
                    stats = self.streamer_bot.tts_manager.get_stats()
                    await websocket.send(json.dumps({"type": "stats", "data": stats}))
                
                else:
                    await websocket.send(json.dumps({"status": "error", "message": "Unknown message type"}))
            
            except json.JSONDecodeError:
                await websocket.send(json.dumps({"status": "error", "message": "Invalid JSON"}))
            except Exception as e:
                self.logger.error(f"Error handling message: {e}")
                await websocket.send(json.dumps({"status": "error", "message": str(e)}))
    
    async def start_server(self):
        """Start the WebSocket server"""
        self.logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        async with websockets.serve(self.handle_message, self.host, self.port):
            await asyncio.Future()  # Run forever


async def main():
    """Main function demonstrating the complete system"""
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Create TTS configuration
    config = TTSConfig(
        max_queue_size=1000,
        max_concurrent_workers=3,
        rate_limit_per_minute=60,
        enable_priority_queue=True,
        enable_rate_limiting=True
    )
    
    # Create TTS manager
    tts_manager = TTSQueueManager(config)
    
    # Choose TTS engine based on availability
    if PYTTSX3_AVAILABLE:
        tts_engine = Pyttsx3TTSEngine()
        print("Using pyttsx3 TTS engine")
    elif GTTS_AVAILABLE:
        tts_engine = GTTS_Engine()
        print("Using Google TTS engine")
    else:
        print("No TTS engines available. Install pyttsx3 or gtts+pygame")
        return
    
    # Set up TTS engine
    tts_manager.set_tts_engine(tts_engine.generate_audio)
    
    # Create streamer bot integration
    streamer_bot = StreamerBotIntegration(tts_manager)
    
    # Start TTS manager
    await tts_manager.start()
    
    try:
        # Simulate some streamer events
        print("Simulating streamer events...")
        
        # High-value donation
        streamer_bot.process_donation("VIP_User", 150.0, "Keep up the great work!")
        
        # Regular donation
        streamer_bot.process_donation("JohnDoe", 25.0, "Love the stream!")
        
        # New subscriber
        streamer_bot.process_subscription("NewSub", 1, "First time subscribing!")
        
        # VIP subscriber
        streamer_bot.process_subscription("LoyalFan", 24, "Been here for 2 years!")
        
        # New follower
        streamer_bot.process_follow("NewFollower")
        
        # Mod command
        streamer_bot.process_chat_message("Moderator", "!tts Welcome everyone to the stream!", is_mod=True)
        
        # Regular chat (should be ignored)
        streamer_bot.process_chat_message("Viewer", "Great stream today!")
        
        # Wait for processing
        print("Processing messages...")
        await asyncio.sleep(10)
        
        # Print final stats
        stats = tts_manager.get_stats()
        print(f"Final stats: {json.dumps(stats, indent=2)}")
        
    finally:
        await tts_manager.stop()


if __name__ == "__main__":
    asyncio.run(main())