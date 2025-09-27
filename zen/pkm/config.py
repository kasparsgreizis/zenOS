"""
Configuration for PKM module.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv


@dataclass
class PKMConfig:
    """PKM module configuration."""
    
    # Storage paths
    pkm_dir: Path = Path.home() / ".zenOS" / "pkm"
    conversations_dir: Path = pkm_dir / "conversations"
    knowledge_base_dir: Path = pkm_dir / "knowledge_base"
    exports_dir: Path = pkm_dir / "exports"
    
    # Google Gemini settings
    gemini_session_cookie: Optional[str] = None
    gemini_csrf_token: Optional[str] = None
    gemini_user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    # Extraction settings
    max_conversations_per_run: int = 50
    extraction_interval_hours: int = 6
    conversation_timeout: int = 30
    retry_attempts: int = 3
    
    # Processing settings
    auto_summarize: bool = True
    extract_keywords: bool = True
    generate_tags: bool = True
    save_raw_html: bool = False
    
    # Storage settings
    storage_format: str = "json"  # json, markdown, both
    compress_old_conversations: bool = True
    max_storage_size_mb: int = 1000
    
    # Cron settings
    cron_enabled: bool = True
    cron_schedule: str = "0 */6 * * *"  # Every 6 hours
    
    def __post_init__(self):
        """Initialize paths and load environment variables."""
        load_dotenv()
        
        # Load from environment
        self.gemini_session_cookie = os.getenv("GEMINI_SESSION_COOKIE")
        self.gemini_csrf_token = os.getenv("GEMINI_CSRF_TOKEN")
        
        # Ensure directories exist
        for path in [self.pkm_dir, self.conversations_dir, 
                    self.knowledge_base_dir, self.exports_dir]:
            path.mkdir(parents=True, exist_ok=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "pkm_dir": str(self.pkm_dir),
            "conversations_dir": str(self.conversations_dir),
            "knowledge_base_dir": str(self.knowledge_base_dir),
            "exports_dir": str(self.exports_dir),
            "max_conversations_per_run": self.max_conversations_per_run,
            "extraction_interval_hours": self.extraction_interval_hours,
            "conversation_timeout": self.conversation_timeout,
            "retry_attempts": self.retry_attempts,
            "auto_summarize": self.auto_summarize,
            "extract_keywords": self.extract_keywords,
            "generate_tags": self.generate_tags,
            "save_raw_html": self.save_raw_html,
            "storage_format": self.storage_format,
            "compress_old_conversations": self.compress_old_conversations,
            "max_storage_size_mb": self.max_storage_size_mb,
            "cron_enabled": self.cron_enabled,
            "cron_schedule": self.cron_schedule,
        }
    
    def save(self, path: Optional[Path] = None):
        """Save configuration to file."""
        import yaml
        
        if path is None:
            path = self.pkm_dir / "config.yaml"
        
        with open(path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)
    
    @classmethod
    def load(cls, path: Optional[Path] = None) -> "PKMConfig":
        """Load configuration from file."""
        import yaml
        
        if path is None:
            path = Path.home() / ".zenOS" / "pkm" / "config.yaml"
        
        config = cls()
        
        if path.exists():
            with open(path, 'r') as f:
                data = yaml.safe_load(f)
                if data:
                    for key, value in data.items():
                        if hasattr(config, key):
                            if key.endswith('_dir'):
                                setattr(config, key, Path(value))
                            else:
                                setattr(config, key, value)
        
        return config