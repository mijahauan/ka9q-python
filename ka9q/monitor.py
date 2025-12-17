"""
ChannelMonitor service for automatic channel recovery.

This module provides a watchdog service that monitors active channels
and automatically re-creates them if they disappear (e.g., due to a
radiod restart).
"""

import threading
import time
import logging
from typing import Dict, Any, Optional

from .control import RadiodControl
from .discovery import discover_channels, ChannelInfo

logger = logging.getLogger(__name__)


class ChannelMonitor:
    """
    Background service to monitor and recover channels.
    
    The ChannelMonitor maintains a list of "desired" channels and their
    configuration. It periodically queries `radiod` to see what channels
    actually exist. If a desired channel is missing, it automatically
    calls `ensure_channel` to restore it.
    
    Usage:
        control = RadiodControl("radiod.local")
        monitor = ChannelMonitor(control)
        monitor.start()
        
        # Register a channel to keep alive
        monitor.monitor_channel(
            frequency_hz=14.074e6,
            preset="usb",
            sample_rate=12000
        )
    """
    
    def __init__(self, control: RadiodControl, check_interval: float = 2.0):
        """
        Initialize the monitor.
        
        Args:
            control: RadiodControl instance to use for discovery and creation
            check_interval: How often to check channel status (seconds)
        """
        self.control = control
        self.check_interval = check_interval
        self._monitored_channels: Dict[int, Dict[str, Any]] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
    def start(self):
        """Start the monitoring thread."""
        if self._running:
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(f"ChannelMonitor started (interval={self.check_interval}s)")
        
    def stop(self):
        """Stop the monitoring thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=self.check_interval * 2)
            self._thread = None
        logger.info("ChannelMonitor stopped")
        
    def monitor_channel(self, **kwargs) -> int:
        """
        Register a channel to be monitored/kept alive.
        
        Calls `ensure_channel` immediately to create/verify the channel,
        then adds it to the monitoring list.
        
        Args:
            **kwargs: Arguments to pass to `ensure_channel`
                     (frequency_hz, preset, sample_rate, encoding, etc.)
                     
        Returns:
            SSRC of the channel
        """
        # First ensure the channel exists
        channel_info = self.control.ensure_channel(**kwargs)
        ssrc = channel_info.ssrc
        
        with self._lock:
            # Store parameters for future recovery
            # We filter out 'timeout' as it's a runtime param, not a channel property
            recovery_params = kwargs.copy()
            if 'timeout' in recovery_params:
                del recovery_params['timeout']
                
            self._monitored_channels[ssrc] = recovery_params
            logger.info(f"Now monitoring channel {ssrc} for recovery")
            
        return ssrc
        
    def unmonitor_channel(self, ssrc: int):
        """Stop monitoring a specific channel."""
        with self._lock:
            if ssrc in self._monitored_channels:
                del self._monitored_channels[ssrc]
                logger.info(f"Stopped monitoring channel {ssrc}")
                
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                self._check_and_recover()
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                
            time.sleep(self.check_interval)
            
    def _check_and_recover(self):
        """Perform one check cycle: discover and recover missing channels."""
        # Get list of desired channels safely
        with self._lock:
            if not self._monitored_channels:
                return
            desired = self._monitored_channels.copy()
            
        # Discover actual running channels
        try:
            # Use quick discovery
            actual_channels = discover_channels(
                self.control.status_address, 
                listen_duration=0.5
            )
        except Exception as e:
            logger.warning(f"Discovery failed during check (radiod down?): {e}")
            return
            
        # Check for missing channels
        for ssrc, params in desired.items():
            if ssrc not in actual_channels:
                logger.warning(f"Channel {ssrc} is missing! Attempting recovery...")
                try:
                    # Attempt to restore
                    self.control.ensure_channel(**params)
                    logger.info(f"Successfully recovered channel {ssrc}")
                except Exception as e:
                    logger.error(f"Failed to recover channel {ssrc}: {e}")
