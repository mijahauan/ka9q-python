# Destination-Aware Channels and Unique IPs

Starting with version `3.2.5`, `ka9q-python` introduces advanced features for managing RTP stream destinations. This allows easier integration with client applications that require stream isolation or specific networking setups.

## Feature Overview

1.  **Unique IP Generation**: Deterministically generate a unique multicast IP for your application ID.
2.  **Destination-Aware SSRC**: SSRC numbers now depend on the destination, meaning "Stream X to IP A" and "Stream X to IP B" are treated as distinct channels by `radiod`.
3.  **Client Session Isolation**: Easily ensure your client app gets its own private stream without collisions.

## 1. Unique Multicast IP Generation

The `generate_multicast_ip` function allows you to "claim" a unique address in the `239.0.0.0/8` private multicast range based on a string identifier (e.g., your app name).

```python
from ka9q import generate_multicast_ip

# Generate a consistent IP for your app
my_app_ip = generate_multicast_ip("my-weather-monitor-v2")
print(my_app_ip)
# Output: 239.14.72.19 (deterministic based on hash)
```

This prevents the need for a central database of assigned IPs. As long as your App ID is unique, your IP will be unique (with >99.9999% probability).

## 2. Using Explicit Destinations

You can now pass a `destination` parameter to `ensure_channel` (and `create_channel`).

- **If provided**: `radiod` will be instructed to send the stream to this specific IP.
- **SSRC Generation**: The SSRC will be calculated including this destination in the hash hash. This means the same frequency/mode sent to *different* IPs will result in *different* channels.

### Example: App-Specific Stream

```python
from ka9q import RadiodControl, generate_multicast_ip

# 1. Define your App's unique destination
APP_ID = "superdarn-viewer-instance-1"
APP_IP = generate_multicast_ip(APP_ID)

with RadiodControl("radiod.local") as control:
    # 2. Request a channel sent specifically to your App IP
    channel = control.ensure_channel(
        frequency_hz=10.5e6,
        preset="iq",
        sample_rate=16000,
        destination=APP_IP  # <--- Explicit destination
    )
    
    print(f"Receiving stream at {channel.multicast_address}:{channel.port}")
```

## Benefits

- **Isolation**: Your app receives only its own traffic, not traffic meant for other tools.
- **Networking**: Easier to configure firewalls or routes when destinations are known/static.
- **Parallel Processing**: You can run multiple instances of the same processing pipeline on the same machine (listening to different multicast groups) without them seeing each other's packets.
