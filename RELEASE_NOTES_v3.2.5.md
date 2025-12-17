### Added
- **Destination-Aware Channels**: `ka9q-python` now supports unique destination IP addresses per client application. The `ensure_channel` and `create_channel` methods now accept a `destination` parameter.
- **Unique IP Generation**: Added `generate_multicast_ip(unique_id)` helper function to deterministically map application IDs to the `239.0.0.0/8` multicast range.
- **Improved SSRC Allocation**: `allocate_ssrc` now includes the destination address in its hash calculation, ensuring that streams with different destinations get unique SSRCs.
