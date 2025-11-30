#!/usr/bin/env python3
"""
Web UI for radiod control
Replicates the workflow of the control utility in a web interface
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import logging
import sys
import os

# Add parent directory to path to import ka9q
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ka9q.discovery import discover_radiod_services, discover_channels
from ka9q.control import RadiodControl

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store active connections
active_controls = {}


@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')


@app.route('/api/discover')
def discover():
    """Discover radiod instances on the network"""
    try:
        logger.info("Discovering radiod instances...")
        instances = discover_radiod_services()
        
        # instances is already a list of dicts with 'name' and 'address' keys
        result = instances
        
        logger.info(f"Found {len(result)} radiod instance(s)")
        return jsonify({
            'success': True,
            'instances': result
        })
    except Exception as e:
        logger.error(f"Discovery error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/channels/<radiod_address>')
def get_channels(radiod_address):
    """Get list of channels for a radiod instance"""
    try:
        logger.info(f"Discovering channels on {radiod_address}...")
        channels = discover_channels(radiod_address, listen_duration=2.0)
        
        result = []
        for ssrc, info in channels.items():
            result.append({
                'ssrc': ssrc,
                'frequency': info.frequency,
                'preset': info.preset,
                'destination': f"{info.multicast_address}:{info.port}",
                'sample_rate': info.sample_rate
            })
        
        # Sort by frequency
        result.sort(key=lambda x: x['frequency'])
        
        logger.info(f"Found {len(result)} channel(s)")
        return jsonify({
            'success': True,
            'channels': result
        })
    except Exception as e:
        logger.error(f"Error getting channels: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/channel/<radiod_address>/<int:ssrc>')
def get_channel_status(radiod_address, ssrc):
    """Get detailed status for a specific channel"""
    try:
        # Create or reuse control connection
        key = f"{radiod_address}:{ssrc}"
        if key not in active_controls:
            active_controls[key] = RadiodControl(radiod_address)
        
        control = active_controls[key]
        
        # Get current status (increased timeout for slower responses)
        status = control.tune(ssrc, timeout=10.0)
        
        # Format for display
        result = {
            'ssrc': status.get('ssrc'),
            'frequency': status.get('frequency', 0),
            'preset': status.get('preset', 'unknown'),
            'sample_rate': status.get('sample_rate', 0),
            'encoding': get_encoding_name(status.get('encoding', 0)),
            'destination': format_destination(status.get('destination')),
            
            # Filter
            'low_edge': status.get('low_edge', 0),
            'high_edge': status.get('high_edge', 0),
            'bandwidth': abs(status.get('high_edge', 0) - status.get('low_edge', 0)),
            
            # Gain & AGC
            'agc_enable': status.get('agc_enable', False),
            'gain': status.get('gain', 0),
            'rf_gain': status.get('rf_gain'),
            'rf_atten': status.get('rf_atten'),
            'rf_agc': status.get('rf_agc'),
            
            # Signal measurements
            'noise_density': status.get('noise_density'),
            'baseband_power': status.get('baseband_power'),
            'snr': status.get('snr')
        }
        
        return jsonify({
            'success': True,
            'status': result
        })
    except TimeoutError:
        logger.warning(f"Timeout getting status for SSRC {ssrc} on {radiod_address}")
        return jsonify({
            'success': False,
            'error': f'Channel {ssrc} not responding (timeout after 10s). Channel may be inactive or not sending status.'
        }), 504
    except Exception as e:
        logger.error(f"Error getting channel status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/tune/<radiod_address>/<int:ssrc>', methods=['POST'])
def tune_channel(radiod_address, ssrc):
    """Tune a channel with new parameters"""
    try:
        data = request.json
        
        # Create or reuse control connection
        key = f"{radiod_address}:{ssrc}"
        if key not in active_controls:
            active_controls[key] = RadiodControl(radiod_address)
        
        control = active_controls[key]
        
        # Build tune parameters
        params = {'ssrc': ssrc}
        
        if 'frequency' in data:
            params['frequency_hz'] = float(data['frequency'])
        if 'preset' in data:
            params['preset'] = data['preset']
        if 'sample_rate' in data:
            params['sample_rate'] = int(data['sample_rate'])
        if 'low_edge' in data:
            params['low_edge'] = float(data['low_edge'])
        if 'high_edge' in data:
            params['high_edge'] = float(data['high_edge'])
        if 'gain' in data:
            params['gain'] = float(data['gain'])
        if 'agc_enable' in data:
            params['agc_enable'] = bool(data['agc_enable'])
        
        # Send tune command
        status = control.tune(**params, timeout=2.0)
        
        return jsonify({
            'success': True,
            'message': 'Channel tuned successfully',
            'status': status
        })
    except Exception as e:
        logger.error(f"Error tuning channel: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def format_destination(dest):
    """Format destination dictionary for display"""
    if not dest:
        return None
    if isinstance(dest, dict):
        return f"{dest.get('address', 'unknown')}:{dest.get('port', 0)}"
    return str(dest)


def get_encoding_name(encoding_id):
    """Convert encoding ID to name"""
    encodings = {
        0: 'None',
        1: 'S16BE',
        2: 'S16LE',
        3: 'F32',
        4: 'F16',
        5: 'OPUS'
    }
    return encodings.get(encoding_id, f'Unknown ({encoding_id})')


if __name__ == '__main__':
    print("=" * 60)
    print("radiod Web UI")
    print("=" * 60)
    print("\nStarting server on http://localhost:5000")
    print("Press Ctrl+C to stop\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
