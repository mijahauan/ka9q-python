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
            'kaiser_beta': status.get('kaiser_beta'),
            'filter_blocksize': status.get('filter_blocksize'),
            'filter_fir_length': status.get('filter_fir_length'),
            
            # Gain & AGC
            'agc_enable': status.get('agc_enable', False),
            'gain': status.get('gain', 0),
            'rf_gain': status.get('rf_gain'),
            'rf_atten': status.get('rf_atten'),
            'rf_agc': status.get('rf_agc'),
            'headroom': status.get('headroom'),
            'agc_hangtime': status.get('agc_hangtime'),
            'agc_recovery_rate': status.get('agc_recovery_rate'),
            'agc_threshold': status.get('agc_threshold'),
            
            # Signal measurements
            'noise_density': status.get('noise_density'),
            'baseband_power': status.get('baseband_power'),
            'snr': status.get('snr'),
            'if_power': status.get('if_power'),
            
            # Demodulation
            'demod_type': status.get('demod_type', 0),
            'pll_enable': status.get('pll_enable'),
            'pll_lock': status.get('pll_lock'),
            'pll_bw': status.get('pll_bw'),
            'squelch_open': status.get('squelch_open'),
            'squelch_close': status.get('squelch_close'),
            
            # LO Frequencies
            'first_lo_frequency': status.get('first_lo_frequency'),
            'second_lo_frequency': status.get('second_lo_frequency'),
            'shift_frequency': status.get('shift_frequency'),
            'doppler_frequency': status.get('doppler_frequency'),
            'doppler_frequency_rate': status.get('doppler_frequency_rate'),
            
            # Hardware
            'lna_gain': status.get('lna_gain'),
            'mixer_gain': status.get('mixer_gain'),
            'if_gain': status.get('if_gain'),
            
            # Statistics
            'output_data_packets': status.get('output_data_packets'),
            'output_metadata_packets': status.get('output_metadata_packets'),
            'output_errors': status.get('output_errors'),
            'filter_drops': status.get('filter_drops')
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


@app.route('/api/agc/<radiod_address>/<int:ssrc>', methods=['POST'])
def set_agc(radiod_address, ssrc):
    """Set AGC parameters for a channel"""
    try:
        data = request.json
        
        key = f"{radiod_address}:{ssrc}"
        if key not in active_controls:
            active_controls[key] = RadiodControl(radiod_address)
        
        control = active_controls[key]
        
        # Build AGC parameters
        enable = data.get('enable', True)
        hangtime = data.get('hangtime')
        headroom = data.get('headroom')
        recovery_rate = data.get('recovery_rate')
        attack_rate = data.get('attack_rate')
        
        control.set_agc(ssrc, enable, hangtime, headroom, recovery_rate, attack_rate)
        
        return jsonify({
            'success': True,
            'message': 'AGC configured successfully'
        })
    except Exception as e:
        logger.error(f"Error setting AGC: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/shift/<radiod_address>/<int:ssrc>', methods=['POST'])
def set_shift(radiod_address, ssrc):
    """Set frequency shift for a channel"""
    try:
        data = request.json
        shift_hz = float(data.get('shift_hz', 0))
        
        key = f"{radiod_address}:{ssrc}"
        if key not in active_controls:
            active_controls[key] = RadiodControl(radiod_address)
        
        control = active_controls[key]
        control.set_shift_frequency(ssrc, shift_hz)
        
        return jsonify({
            'success': True,
            'message': f'Shift frequency set to {shift_hz} Hz'
        })
    except Exception as e:
        logger.error(f"Error setting shift: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/output_level/<radiod_address>/<int:ssrc>', methods=['POST'])
def set_output_level(radiod_address, ssrc):
    """Set output level for a channel"""
    try:
        data = request.json
        level = float(data.get('level', 0))
        
        key = f"{radiod_address}:{ssrc}"
        if key not in active_controls:
            active_controls[key] = RadiodControl(radiod_address)
        
        control = active_controls[key]
        control.set_output_level(ssrc, level)
        
        return jsonify({
            'success': True,
            'message': f'Output level set to {level}'
        })
    except Exception as e:
        logger.error(f"Error setting output level: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/filter/<radiod_address>/<int:ssrc>', methods=['POST'])
def set_filter(radiod_address, ssrc):
    """Set filter parameters for a channel"""
    try:
        data = request.json
        
        key = f"{radiod_address}:{ssrc}"
        if key not in active_controls:
            active_controls[key] = RadiodControl(radiod_address)
        
        control = active_controls[key]
        
        low_edge = data.get('low_edge')
        high_edge = data.get('high_edge')
        kaiser_beta = data.get('kaiser_beta')
        
        control.set_filter(ssrc, low_edge, high_edge, kaiser_beta)
        
        return jsonify({
            'success': True,
            'message': 'Filter parameters set successfully'
        })
    except Exception as e:
        logger.error(f"Error setting filter: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/squelch/<radiod_address>/<int:ssrc>', methods=['POST'])
def set_squelch(radiod_address, ssrc):
    """Set squelch parameters for a channel"""
    try:
        data = request.json
        
        key = f"{radiod_address}:{ssrc}"
        if key not in active_controls:
            active_controls[key] = RadiodControl(radiod_address)
        
        control = active_controls[key]
        
        open_threshold = data.get('open_threshold')
        close_threshold = data.get('close_threshold')
        snr_squelch = data.get('snr_squelch')
        
        control.set_squelch(ssrc, open_threshold, close_threshold, snr_squelch)
        
        return jsonify({
            'success': True,
            'message': 'Squelch configured successfully'
        })
    except Exception as e:
        logger.error(f"Error setting squelch: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/pll/<radiod_address>/<int:ssrc>', methods=['POST'])
def set_pll(radiod_address, ssrc):
    """Set PLL parameters for a channel"""
    try:
        data = request.json
        
        key = f"{radiod_address}:{ssrc}"
        if key not in active_controls:
            active_controls[key] = RadiodControl(radiod_address)
        
        control = active_controls[key]
        
        enable = data.get('enable')
        bandwidth = data.get('bandwidth')
        square = data.get('square')
        
        control.set_pll(ssrc, enable, bandwidth, square)
        
        return jsonify({
            'success': True,
            'message': 'PLL configured successfully'
        })
    except Exception as e:
        logger.error(f"Error setting PLL: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/output_channels/<radiod_address>/<int:ssrc>', methods=['POST'])
def set_output_channels(radiod_address, ssrc):
    """Set output channels (mono/stereo) for a channel"""
    try:
        data = request.json
        channels = int(data.get('channels', 1))
        
        key = f"{radiod_address}:{ssrc}"
        if key not in active_controls:
            active_controls[key] = RadiodControl(radiod_address)
        
        control = active_controls[key]
        control.set_output_channels(ssrc, channels)
        
        return jsonify({
            'success': True,
            'message': f'Output channels set to {channels}'
        })
    except Exception as e:
        logger.error(f"Error setting output channels: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/isb/<radiod_address>/<int:ssrc>', methods=['POST'])
def set_isb(radiod_address, ssrc):
    """Set independent sideband mode for a channel"""
    try:
        data = request.json
        enable = bool(data.get('enable', False))
        
        key = f"{radiod_address}:{ssrc}"
        if key not in active_controls:
            active_controls[key] = RadiodControl(radiod_address)
        
        control = active_controls[key]
        control.set_independent_sideband(ssrc, enable)
        
        return jsonify({
            'success': True,
            'message': f'ISB {"enabled" if enable else "disabled"}'
        })
    except Exception as e:
        logger.error(f"Error setting ISB: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/envelope/<radiod_address>/<int:ssrc>', methods=['POST'])
def set_envelope(radiod_address, ssrc):
    """Set envelope detection for a channel"""
    try:
        data = request.json
        enable = bool(data.get('enable', False))
        
        key = f"{radiod_address}:{ssrc}"
        if key not in active_controls:
            active_controls[key] = RadiodControl(radiod_address)
        
        control = active_controls[key]
        control.set_envelope_detection(ssrc, enable)
        
        return jsonify({
            'success': True,
            'message': f'Envelope detection {"enabled" if enable else "disabled"}'
        })
    except Exception as e:
        logger.error(f"Error setting envelope detection: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/opus_bitrate/<radiod_address>/<int:ssrc>', methods=['POST'])
def set_opus_bitrate(radiod_address, ssrc):
    """Set Opus codec bitrate for a channel"""
    try:
        data = request.json
        bitrate = int(data.get('bitrate', 32000))
        
        key = f"{radiod_address}:{ssrc}"
        if key not in active_controls:
            active_controls[key] = RadiodControl(radiod_address)
        
        control = active_controls[key]
        control.set_opus_bitrate(ssrc, bitrate)
        
        return jsonify({
            'success': True,
            'message': f'Opus bitrate set to {bitrate} bps'
        })
    except Exception as e:
        logger.error(f"Error setting Opus bitrate: {e}")
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
