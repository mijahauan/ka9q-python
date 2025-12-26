### Added
- **ChannelMonitor**: New service that provides automatic recovery from `radiod` restarts. It monitors registered channels and automatically invokes `ensure_channel` to restore them if they disappear.
    - Usage: `monitor = ChannelMonitor(control); monitor.start(); monitor.monitor_channel(...)`
