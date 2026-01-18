#!/usr/bin/env python3
"""
TurboPi Wake Word Service

Standalone always-on wake word detection service.
This service continuously monitors for the wake word and arms voice capture.

Note: For the current implementation, wake word detection is integrated
into the API service. This standalone service is provided for future use
if separate wake word processing is needed.
"""

import os
import sys
import time
import logging
import signal

# Import wake word engine from current directory
sys.path.insert(0, os.path.dirname(__file__))

from wake_word import WakeWordEngine


class WakeWordService:
    """Wake word detection service"""
    
    def __init__(self):
        """Initialize wake word service"""
        self.engine = WakeWordEngine()
        self.running = False
        self.logger = logging.getLogger(__name__)
        
        # Register wake word callback
        self.engine.register_callback(self.on_wake_word_detected)
    
    def on_wake_word_detected(self):
        """Callback when wake word is detected"""
        self.logger.info("Wake word detected - voice capture armed")
        # In a full implementation, this would trigger audio capture
        # and forward to STT service
    
    def start(self):
        """Start the wake word service"""
        self.running = True
        self.logger.info("Wake word service started")
        self.logger.info(f"Monitoring for wake word: {self.engine.config.wake_word}")
        
        # In a real implementation, this would continuously process audio
        # For now, this is a placeholder that demonstrates the structure
        while self.running:
            # Check status and log periodically
            if self.engine.is_armed():
                status = self.engine.get_status()
                self.logger.debug(f"Voice capture armed, time remaining: {status['time_remaining']:.1f}s")
            
            time.sleep(1)
    
    def stop(self):
        """Stop the wake word service"""
        self.logger.info("Wake word service stopping...")
        self.running = False


def main():
    """Main entry point for wake word service"""
    # Configure logging
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    
    logger = logging.getLogger(__name__)
    
    # Create service
    service = WakeWordService()
    
    # Handle signals for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        service.stop()
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start service
    try:
        service.start()
    except Exception as e:
        logger.error(f"Wake word service error: {e}")
        sys.exit(1)
    
    logger.info("Wake word service stopped")
    sys.exit(0)


if __name__ == '__main__':
    main()
