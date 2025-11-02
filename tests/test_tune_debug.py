"""
Debug tool for tune functionality

This helps diagnose issues with tune commands by showing exactly what's
being sent and received.

Usage: python tests/test_tune_debug.py radiod.local
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ka9q import RadiodControl, StatusType, Encoding
from ka9q.control import decode_int, decode_double, decode_string, decode_float


def print_status_fields(status):
    """Pretty print all status fields"""
    print("\nStatus fields received:")
    for key, value in sorted(status.items()):
        if key == 'frequency':
            print(f"  {key:20s}: {value/1e6:.6f} MHz ({value} Hz)")
        elif key == 'samprate':
            print(f"  {key:20s}: {value} Hz")
        elif key in ['gain', 'rf_gain', 'rf_atten']:
            print(f"  {key:20s}: {value:.2f} dB")
        elif key in ['low', 'high']:
            print(f"  {key:20s}: {value:.1f} Hz")
        elif key == 'ssrc':
            print(f"  {key:20s}: {value} (0x{value:08x})")
        else:
            print(f"  {key:20s}: {value}")


def test_basic_tune(host):
    """Test basic tune operation with detailed output"""
    print(f"="*70)
    print(f"Connecting to radiod at {host}")
    print(f"="*70)
    
    try:
        control = RadiodControl(host)
        print(f"✓ Connected successfully")
        print(f"  Status address: {control.status_address}")
        print(f"  Control destination: {control.dest_addr[0]}:{control.dest_addr[1]}")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 1: Basic frequency tune
    print(f"\n{'='*70}")
    print(f"TEST 1: Basic Frequency Tune")
    print(f"{'='*70}")
    
    ssrc = 99999001
    freq = 14.074e6
    preset = 'usb'
    
    print(f"\nSending tune command:")
    print(f"  SSRC:      {ssrc} (0x{ssrc:08x})")
    print(f"  Frequency: {freq/1e6:.3f} MHz")
    print(f"  Preset:    {preset}")
    print(f"  Timeout:   5.0 seconds")
    
    try:
        status = control.tune(ssrc=ssrc, frequency_hz=freq, preset=preset, timeout=5.0)
        print(f"\n✓ Tune command succeeded")
        print_status_fields(status)
        
        # Verify frequency
        if 'frequency' in status:
            reported_freq = status['frequency']
            diff = abs(reported_freq - freq)
            print(f"\nFrequency verification:")
            print(f"  Requested: {freq/1e6:.6f} MHz")
            print(f"  Reported:  {reported_freq/1e6:.6f} MHz")
            print(f"  Diff:      {diff:.1f} Hz")
            if diff < 1.0:
                print(f"  ✓ Frequency match!")
            else:
                print(f"  ⚠ Frequency mismatch (diff > 1 Hz)")
        else:
            print(f"\n⚠ Warning: Frequency not in status response")
        
    except Exception as e:
        print(f"\n✗ Tune command failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Gain change
    print(f"\n{'='*70}")
    print(f"TEST 2: Gain Change")
    print(f"{'='*70}")
    
    gain = 10.0
    print(f"\nSending tune command with gain:")
    print(f"  SSRC:      {ssrc}")
    print(f"  Frequency: {freq/1e6:.3f} MHz")
    print(f"  Gain:      {gain} dB")
    
    try:
        status = control.tune(ssrc=ssrc, frequency_hz=freq, preset=preset, 
                             gain=gain, timeout=5.0)
        print(f"\n✓ Tune command succeeded")
        print_status_fields(status)
        
        # Verify gain
        if 'gain' in status:
            reported_gain = status['gain']
            diff = abs(reported_gain - gain)
            print(f"\nGain verification:")
            print(f"  Requested: {gain:.2f} dB")
            print(f"  Reported:  {reported_gain:.2f} dB")
            print(f"  Diff:      {diff:.2f} dB")
            if diff < 0.1:
                print(f"  ✓ Gain match!")
            else:
                print(f"  ⚠ Gain mismatch (diff > 0.1 dB)")
        else:
            print(f"\n⚠ Warning: Gain not in status response")
        
        # Check AGC
        if 'agc_enable' in status:
            print(f"\nAGC state: {status['agc_enable']}")
            if status['agc_enable']:
                print(f"  ⚠ AGC is enabled (should be disabled with manual gain)")
            else:
                print(f"  ✓ AGC correctly disabled")
        
    except Exception as e:
        print(f"\n✗ Tune command failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Frequency change
    print(f"\n{'='*70}")
    print(f"TEST 3: Frequency Change")
    print(f"{'='*70}")
    
    new_freq = 14.076e6
    print(f"\nChanging frequency:")
    print(f"  From: {freq/1e6:.3f} MHz")
    print(f"  To:   {new_freq/1e6:.3f} MHz")
    
    try:
        time.sleep(0.5)  # Wait a moment
        
        status = control.tune(ssrc=ssrc, frequency_hz=new_freq, preset=preset,
                             gain=gain, timeout=5.0)
        print(f"\n✓ Tune command succeeded")
        print_status_fields(status)
        
        # Verify frequency changed
        if 'frequency' in status:
            reported_freq = status['frequency']
            diff_from_new = abs(reported_freq - new_freq)
            diff_from_old = abs(reported_freq - freq)
            
            print(f"\nFrequency change verification:")
            print(f"  Old freq:     {freq/1e6:.6f} MHz")
            print(f"  New freq:     {new_freq/1e6:.6f} MHz")
            print(f"  Reported:     {reported_freq/1e6:.6f} MHz")
            print(f"  Diff from new: {diff_from_new:.1f} Hz")
            print(f"  Diff from old: {diff_from_old:.1f} Hz")
            
            if diff_from_new < 1.0:
                print(f"  ✓ Frequency changed successfully!")
            else:
                print(f"  ⚠ Frequency didn't match new value")
                
            if diff_from_old < 100:
                print(f"  ⚠ WARNING: Frequency appears unchanged from old value!")
        
    except Exception as e:
        print(f"\n✗ Tune command failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"✓ All debug tests completed")
    print(f"\nIf you see warnings about mismatches, the tune commands may not")
    print(f"be taking effect on the radiod instance. Check:")
    print(f"  1. radiod is running and accessible")
    print(f"  2. radiod has a working hardware interface")
    print(f"  3. radiod logs for any error messages")
    print(f"  4. Network connectivity (multicast working)")
    
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python tests/test_tune_debug.py <radiod-host>")
        print("\nExample: python tests/test_tune_debug.py radiod.local")
        sys.exit(1)
    
    host = sys.argv[1]
    success = test_basic_tune(host)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
