# Web UI Enhancement Guide: Adding Missing Features from ncurses Control

## Overview
This guide details how to add features from the ncurses `control` utility to the ka9q-python web UI.

## Current Status

### Currently Displayed in Web UI
The web UI currently shows these fields (from `/webui/templates/index.html` and `/webui/static/app.js`):

**Tuning Section:**
- `frequency` - Radio frequency
- `preset` - Mode (usb, lsb, iq, etc.)
- `ssrc` - SSRC identifier

**Filter Section:**
- `low_edge` - Low edge frequency
- `high_edge` - High edge frequency
- `bandwidth` - Calculated from edges

**Output Section:**
- `sample_rate` - Output sample rate
- `encoding` - Output encoding format
- `destination` - Multicast destination

**Signal Section:**
- `snr` - Signal-to-noise ratio
- `baseband_power` - Baseband power
- `noise_density` - Noise density

**Gain & AGC Section:**
- `agc_enable` - AGC on/off
- `gain` - Channel gain
- `rf_gain` - RF gain (if available)
- `rf_atten` - RF attenuation (if available)
- `rf_agc` - RF AGC status (if available)

### Missing Fields Available from Status (Comparing to ncurses display)

#### High Priority (Commonly Used)
1. **Filter Parameters:**
   - `kaiser_beta` (StatusType.KAISER_BETA) - Filter shaping parameter
   - `filter_blocksize` (StatusType.FILTER_BLOCKSIZE) - FFT size
   - `filter_fir_length` (StatusType.FILTER_FIR_LENGTH) - Filter length

2. **AGC Parameters:**
   - `headroom` (StatusType.HEADROOM) - AGC headroom in dB
   - `agc_hangtime` (StatusType.AGC_HANGTIME) - AGC hang time
   - `agc_recovery_rate` (StatusType.AGC_RECOVERY_RATE) - AGC recovery
   - `agc_threshold` (StatusType.AGC_THRESHOLD) - AGC threshold

3. **Demodulation:**
   - `demod_type` (StatusType.DEMOD_TYPE) - Demod type (0=linear, 1=FM, etc.)
   - `pll_enable` (StatusType.PLL_ENABLE) - PLL enabled
   - `pll_lock` (StatusType.PLL_LOCK) - PLL lock status
   - `pll_bw` (StatusType.PLL_BW) - PLL bandwidth
   - `squelch_open` (StatusType.SQUELCH_OPEN) - Squelch threshold (open)
   - `squelch_close` (StatusType.SQUELCH_CLOSE) - Squelch threshold (close)

4. **LO/Frequency Details:**
   - `first_lo_frequency` (StatusType.FIRST_LO_FREQUENCY) - First LO freq
   - `second_lo_frequency` (StatusType.SECOND_LO_FREQUENCY) - Second LO freq
   - `shift_frequency` (StatusType.SHIFT_FREQUENCY) - Frequency shift
   - `doppler_frequency` (StatusType.DOPPLER_FREQUENCY) - Doppler offset
   - `doppler_frequency_rate` (StatusType.DOPPLER_FREQUENCY_RATE) - Doppler rate

5. **Hardware/Calibration:**
   - `calibrate` (StatusType.CALIBRATE) - Calibration value
   - `lna_gain` (StatusType.LNA_GAIN) - LNA gain
   - `mixer_gain` (StatusType.MIXER_GAIN) - Mixer gain
   - `if_gain` (StatusType.IF_GAIN) - IF gain
   - `dc_i_offset` (StatusType.DC_I_OFFSET) - DC I offset
   - `dc_q_offset` (StatusType.DC_Q_OFFSET) - DC Q offset
   - `iq_imbalance` (StatusType.IQ_IMBALANCE) - IQ imbalance
   - `iq_phase` (StatusType.IQ_PHASE) - IQ phase

6. **Statistics:**
   - `output_data_packets` (StatusType.OUTPUT_DATA_PACKETS) - Data packets sent
   - `output_metadata_packets` (StatusType.OUTPUT_METADATA_PACKETS) - Metadata packets
   - `output_errors` (StatusType.OUTPUT_ERRORS) - Output errors
   - `filter_drops` (StatusType.FILTER_DROPS) - Filter drops
   - `ad_over` (StatusType.AD_OVER) - A/D overflows

#### Medium Priority
- `if_power` (StatusType.IF_POWER) - IF power
- `output_level` (StatusType.OUTPUT_LEVEL) - Output level
- `output_samples` (StatusType.OUTPUT_SAMPLES) - Output samples
- `freq_offset` (StatusType.FREQ_OFFSET) - Frequency offset
- `peak_deviation` (StatusType.PEAK_DEVIATION) - Peak deviation (FM)
- `pl_tone` (StatusType.PL_TONE) - PL tone frequency
- `envelope` (StatusType.ENVELOPE) - Envelope detector

## Implementation Plan

### Step 1: Update Backend to Provide Additional Fields

Modify `/webui/app.py` - `get_channel_status()` function:

```python
@app.route('/api/channel/<radiod_address>/<int:ssrc>')
def get_channel_status(radiod_address, ssrc):
    """Get detailed status for a specific channel"""
    try:
        # ... existing code ...
        
        # Format for display - ADD THESE FIELDS
        result = {
            # ... existing fields ...
            
            # Filter details
            'kaiser_beta': status.get('kaiser_beta'),
            'filter_blocksize': status.get('filter_blocksize'),
            'filter_fir_length': status.get('filter_fir_length'),
            
            # AGC details  
            'headroom': status.get('headroom'),
            'agc_hangtime': status.get('agc_hangtime'),
            'agc_recovery_rate': status.get('agc_recovery_rate'),
            'agc_threshold': status.get('agc_threshold'),
            
            # Demodulation
            'demod_type': status.get('demod_type', 0),
            'pll_enable': status.get('pll_enable'),
            'pll_lock': status.get('pll_lock'),
            'pll_bw': status.get('pll_bw'),
            'squelch_open': status.get('squelch_open'),
            'squelch_close': status.get('squelch_close'),
            
            # LO frequencies
            'first_lo_frequency': status.get('first_lo_frequency'),
            'second_lo_frequency': status.get('second_lo_frequency'),
            'shift_frequency': status.get('shift_frequency'),
            'doppler_frequency': status.get('doppler_frequency'),
            
            # Hardware
            'lna_gain': status.get('lna_gain'),
            'mixer_gain': status.get('mixer_gain'),
            'if_gain': status.get('if_gain'),
            'if_power': status.get('if_power'),
            
            # Statistics
            'output_data_packets': status.get('output_data_packets'),
            'output_metadata_packets': status.get('output_metadata_packets'),
            'output_errors': status.get('output_errors'),
            'filter_drops': status.get('filter_drops'),
        }
        
        return jsonify({
            'success': True,
            'status': result
        })
```

### Step 2: Update Frontend HTML Template

Modify `/webui/templates/index.html` to add new sections:

```html
<!-- Add after existing sections-grid div -->

<!-- Advanced Filter Section -->
<div class="section">
    <h3>Filter Details</h3>
    <div class="info-list">
        <div class="info-item">
            <label>Kaiser Beta:</label>
            <span class="value kaiser-beta-value"></span>
        </div>
        <div class="info-item">
            <label>FFT Size:</label>
            <span class="value filter-blocksize-value"></span>
        </div>
        <div class="info-item">
            <label>FIR Length:</label>
            <span class="value filter-fir-length-value"></span>
        </div>
    </div>
</div>

<!-- AGC Details Section -->
<div class="section">
    <h3>AGC Details</h3>
    <div class="info-list">
        <div class="info-item">
            <label>Headroom:</label>
            <span class="value headroom-value"></span>
        </div>
        <div class="info-item">
            <label>Hang Time:</label>
            <span class="value agc-hangtime-value"></span>
        </div>
        <div class="info-item">
            <label>Recovery:</label>
            <span class="value agc-recovery-value"></span>
        </div>
    </div>
</div>

<!-- Demodulation Section -->
<div class="section">
    <h3>Demodulation</h3>
    <div class="info-list">
        <div class="info-item">
            <label>Type:</label>
            <span class="value demod-type-value"></span>
        </div>
        <div class="info-item">
            <label>PLL:</label>
            <span class="value pll-status-value"></span>
        </div>
        <div class="info-item">
            <label>Squelch:</label>
            <span class="value squelch-value"></span>
        </div>
    </div>
</div>

<!-- LO Frequencies Section -->
<div class="section">
    <h3>LO Frequencies</h3>
    <div class="info-list">
        <div class="info-item">
            <label>1st LO:</label>
            <span class="value first-lo-value"></span>
        </div>
        <div class="info-item">
            <label>2nd LO:</label>
            <span class="value second-lo-value"></span>
        </div>
        <div class="info-item">
            <label>Shift:</label>
            <span class="value shift-freq-value"></span>
        </div>
    </div>
</div>

<!-- Statistics Section -->
<div class="section">
    <h3>Statistics</h3>
    <div class="info-list">
        <div class="info-item">
            <label>Data Packets:</label>
            <span class="value data-packets-value"></span>
        </div>
        <div class="info-item">
            <label>Errors:</label>
            <span class="value output-errors-value"></span>
        </div>
        <div class="info-item">
            <label>Drops:</label>
            <span class="value filter-drops-value"></span>
        </div>
    </div>
</div>
```

### Step 3: Update Frontend JavaScript

Modify `/webui/static/app.js` - `displayChannelDetails()` function:

```javascript
function displayChannelDetails(status) {
    const template = document.getElementById('channel-detail-template');
    const clone = template.content.cloneNode(true);
    
    // ... existing field population ...
    
    // Filter Details
    clone.querySelector('.kaiser-beta-value').textContent = 
        status.kaiser_beta !== null ? status.kaiser_beta.toFixed(2) : 'N/A';
    clone.querySelector('.filter-blocksize-value').textContent = 
        status.filter_blocksize || 'N/A';
    clone.querySelector('.filter-fir-length-value').textContent = 
        status.filter_fir_length || 'N/A';
    
    // AGC Details
    clone.querySelector('.headroom-value').textContent = 
        status.headroom !== null ? formatDecimal(status.headroom) + ' dB' : 'N/A';
    clone.querySelector('.agc-hangtime-value').textContent = 
        status.agc_hangtime !== null ? formatDecimal(status.agc_hangtime) + ' s' : 'N/A';
    clone.querySelector('.agc-recovery-value').textContent = 
        status.agc_recovery_rate !== null ? formatDecimal(status.agc_recovery_rate) + ' dB/s' : 'N/A';
    
    // Demodulation
    const demodTypes = {0: 'Linear', 1: 'FM', 2: 'WFM', 3: 'Spectrum'};
    clone.querySelector('.demod-type-value').textContent = 
        demodTypes[status.demod_type] || 'Unknown';
    
    const pllStatus = status.pll_enable 
        ? (status.pll_lock ? 'Locked' : 'Unlocked')
        : 'Disabled';
    clone.querySelector('.pll-status-value').textContent = pllStatus;
    
    const squelchInfo = status.squelch_open !== null 
        ? `${formatDecimal(status.squelch_open)} dB`
        : 'N/A';
    clone.querySelector('.squelch-value').textContent = squelchInfo;
    
    // LO Frequencies
    clone.querySelector('.first-lo-value').textContent = 
        status.first_lo_frequency ? formatFrequency(status.first_lo_frequency) : 'N/A';
    clone.querySelector('.second-lo-value').textContent = 
        status.second_lo_frequency ? formatFrequency(status.second_lo_frequency) : 'N/A';
    clone.querySelector('.shift-freq-value').textContent = 
        status.shift_frequency !== null ? formatNumber(status.shift_frequency) + ' Hz' : 'N/A';
    
    // Statistics
    clone.querySelector('.data-packets-value').textContent = 
        formatNumber(status.output_data_packets || 0);
    clone.querySelector('.output-errors-value').textContent = 
        formatNumber(status.output_errors || 0);
    clone.querySelector('.filter-drops-value').textContent = 
        formatNumber(status.filter_drops || 0);
    
    // ... rest of existing code ...
}
```

### Step 4: Add Styling (Optional)

Modify `/webui/static/style.css` to add styling for new sections:

```css
/* Make the grid responsive for additional sections */
.sections-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
    margin-bottom: 20px;
}

/* Highlight important status indicators */
.pll-status-value {
    font-weight: bold;
}

.pll-status-value:contains("Locked") {
    color: #2ecc71;
}

/* Error/warning highlighting */
.output-errors-value,
.filter-drops-value {
    font-family: monospace;
}
```

## Recommended Implementation Order

1. **Phase 1 - Essential Fields (Start Here)**
   - Kaiser Beta, FFT size, FIR length (filter details)
   - Headroom (AGC detail)
   - Demod type, PLL status
   - First/Second LO frequencies

2. **Phase 2 - Advanced Features**
   - Full AGC parameters
   - Squelch settings
   - Doppler information
   - Hardware gains (LNA, Mixer, IF)

3. **Phase 3 - Statistics & Monitoring**
   - Packet counts
   - Error counts
   - Drop counts
   - A/D overflow monitoring

4. **Phase 4 - Expert Features**
   - Calibration values
   - IQ balance/phase
   - DC offsets
   - Test points

## Testing

After adding fields, test with:
```bash
cd /home/mjh/git/ka9q-python/webui
python3 app.py
```

Navigate to `http://localhost:5000` and verify:
1. All new fields display correctly
2. N/A is shown for unavailable fields
3. Units are displayed properly
4. Auto-refresh updates all fields

## Tips for Best Effect

1. **Group Related Fields** - Keep related parameters together (e.g., all AGC params in one section)

2. **Use Collapsible Sections** - For advanced fields, consider making sections collapsible to reduce clutter

3. **Add Tooltips** - Add `title` attributes to labels for explanations:
   ```html
   <label title="Kaiser window shaping parameter">Kaiser Beta:</label>
   ```

4. **Conditional Display** - Only show fields relevant to the current mode (e.g., PLL fields only for FM)

5. **Visual Indicators** - Use color coding for status fields (green=good, red=error, yellow=warning)

6. **Make it Interactive** - Consider adding controls to adjust parameters directly from the web UI

## Field Availability Notes

Not all fields are available from all radiod instances or modes:
- FM-specific: `peak_deviation`, `pl_tone`, `fm_snr`
- Linear-specific: `gain`, `agc_*` parameters
- Hardware-specific: `lna_gain`, `mixer_gain`, `if_gain` (depends on SDR type)

Always check for `null` values and display 'N/A' appropriately.
