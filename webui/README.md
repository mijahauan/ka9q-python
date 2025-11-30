# radiod Web UI

A modern web interface for controlling and monitoring ka9q-radio (radiod) instances on your network.

## Features

### 🔍 **Discovery**
- Automatically discovers radiod instances on your LAN using Avahi/mDNS
- Pull-down selector to choose which radiod to control

### 📡 **Channel List**
- Displays all active channels (SSRCs) from the selected radiod
- Shows frequency, mode/preset, sample rate, and RTP destination
- Sorted by frequency for easy navigation
- Click any channel to view detailed information

### 📊 **Channel Details**
- **Tuning**: Frequency, mode, SSRC
- **Filter**: Low/high edges, bandwidth
- **Output**: Sample rate, encoding, RTP destination
- **Gain & AGC**: All gain controls and AGC status
- **Signal**: Live SNR, baseband power, noise density
- **Auto-refresh**: Updates every second with live data

## Screenshots

```
┌──────────────────────────────────────────────────────────┐
│ 📻 radiod Control Panel                                  │
│ radiod Instance: [airspyhf-ka9q.local ▼] [🔄 Refresh]   │
├─────────────┬────────────────────────────────────────────┤
│ Channels    │  Channel 14074000                          │
│             │  ─────────────────────────────────────     │
│ 14.074 MHz  │  Tuning                                    │
│ usb • 12000 │  Frequency: 14.074 MHz                     │
│ 239.1.2.3   │  Mode/Preset: usb                          │
│ SSRC: 14074 │  SSRC: 14074000                            │
│             │                                            │
│ 7.074 MHz   │  Filter                                    │
│ usb • 12000 │  Low Edge: -3,000 Hz                       │
│ 239.1.2.3   │  High Edge: 3,000 Hz                       │
│ SSRC: 7074  │  Bandwidth: 6,000 Hz                       │
│             │                                            │
│ 3.573 MHz   │  Signal                                    │
│ usb • 12000 │  SNR: 12.5 dB ⬤                            │
│             │  Baseband Power: -45.3 dB                  │
└─────────────┴────────────────────────────────────────────┘
```

## Installation

### 1. Install Dependencies

```bash
cd webui
pip install -r requirements.txt
```

### 2. Install ka9q-python

The web UI requires ka9q-python to be installed:

```bash
cd ..
pip install -e .
```

## Usage

### Start the Web Server

```bash
cd webui
python app.py
```

Or make it executable:

```bash
chmod +x app.py
./app.py
```

### Access the Web UI

Open your browser to:
```
http://localhost:5000
```

The web UI is accessible from any device on your network at:
```
http://<server-ip>:5000
```

## Workflow

### 1. **Discover radiod Instances**
- On page load, the UI automatically discovers radiod instances on your LAN
- If needed, click "🔄 Refresh" to re-discover

### 2. **Select radiod Instance**
- Use the pull-down menu to select which radiod you want to control
- The channel list will automatically populate

### 3. **View Channels**
- The left sidebar shows all active channels
- Each entry displays:
  - Frequency (sorted)
  - Mode/preset
  - Sample rate
  - RTP destination
  - SSRC

### 4. **Select Channel**
- Click any channel in the list to view detailed information
- The right panel displays comprehensive channel status
- Data auto-refreshes every second

### 5. **Monitor Signals**
- Watch live SNR, power, and noise measurements
- All parameters update in real-time
- Click "✕ Close" to deselect the channel

## API Endpoints

The web UI exposes a REST API:

### Discovery
```
GET /api/discover
Returns: List of radiod instances
```

### Channels
```
GET /api/channels/<radiod_address>
Returns: List of channels for the specified radiod
```

### Channel Status
```
GET /api/channel/<radiod_address>/<ssrc>
Returns: Detailed status for a specific channel
```

### Tune Channel
```
POST /api/tune/<radiod_address>/<ssrc>
Body: JSON with tuning parameters
Returns: Updated channel status
```

## Architecture

```
┌──────────────┐
│   Browser    │
│  (Frontend)  │
└──────┬───────┘
       │ HTTP/JSON
       │
┌──────▼───────┐
│    Flask     │
│  (Backend)   │
└──────┬───────┘
       │ ka9q-python
       │
┌──────▼───────┐
│   radiod     │
│ (ka9q-radio) │
└──────────────┘
```

**Frontend**: HTML, CSS, JavaScript (vanilla, no frameworks)
**Backend**: Flask (Python) + ka9q-python
**Protocol**: REST API with JSON
**Updates**: Polling (1 second interval for selected channel)

## Configuration

### Change Port

Edit `app.py`:
```python
app.run(host='0.0.0.0', port=5000, debug=True)
#                       ^^^^ Change this
```

### Change Refresh Rate

Edit `static/app.js`:
```javascript
refreshInterval = setInterval(() => loadChannelDetails(ssrc), 1000);
//                                                             ^^^^ milliseconds
```

### Enable Production Mode

For production deployment:
```python
app.run(host='0.0.0.0', port=5000, debug=False)
```

Or use a production WSGI server like gunicorn:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Security Considerations

⚠️ **This web UI is intended for LAN use only**

- No authentication is implemented
- All API endpoints are publicly accessible
- Do not expose to the internet without adding:
  - User authentication
  - HTTPS/TLS
  - Rate limiting
  - Input validation

## Troubleshooting

### No radiod Instances Found

1. Check that radiod is running on your network
2. Verify Avahi/mDNS is working:
   ```bash
   avahi-browse -r _ka9q-ctl._udp
   ```
3. Check firewall settings (ports 5006, 5007)

### Channels Not Loading

1. Verify radiod is sending status messages
2. Check that channels are actually running
3. Use the command-line tools to test:
   ```bash
   python -c "from ka9q.discovery import discover_channels; print(discover_channels('radiod.local'))"
   ```

### Auto-Refresh Not Working

1. Check browser console for JavaScript errors
2. Verify the API endpoint is responding
3. Try manually refreshing the page

## Browser Compatibility

Tested on:
- ✅ Chrome/Chromium 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

## Development

### File Structure
```
webui/
├── app.py                 # Flask backend
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── templates/
│   └── index.html        # Main HTML template
└── static/
    ├── style.css         # Styling
    └── app.js            # Frontend logic
```

### Adding Features

1. **Backend**: Add new endpoints in `app.py`
2. **Frontend**: Update `app.js` for new API calls
3. **UI**: Modify `index.html` and `style.css` for layout changes

## License

Same as ka9q-python (refer to parent directory)

## Credits

- Built on ka9q-python library
- Designed to complement ka9q-radio by Phil Karn, KA9Q
- Inspired by the ncurses `control` utility
