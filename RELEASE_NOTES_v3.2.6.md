### Added
- **Output Encoding Support**: Added complete support for specifying output encoding (e.g., F32, S16LE, OPUS) in `ensure_channel` and `create_channel`.
    - `create_channel` now automatically sends the required follow-up `OUTPUT_ENCODING` command to `radiod`.
    - `ensure_channel` verifies the encoding of existing channels and reconfigures them if different from the requested encoding.
    - `ChannelInfo` now includes the `encoding` field for discovered channels.
