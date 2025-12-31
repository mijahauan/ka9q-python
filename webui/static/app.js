// radiod Web UI - Main Application
const API_BASE = '';
let selectedRadiod = null;
let selectedSSRC = null;
let refreshInterval = null;
let isRefreshing = false; // Prevent overlapping refreshes
let consecutiveErrors = 0; // Track consecutive errors
const MAX_CONSECUTIVE_ERRORS = 3; // Stop refreshing after this many errors
let editMode = false; // Track edit mode state
let currentStatus = null; // Store current channel status for edit mode

// DOM Elements
const radiodSelect = document.getElementById('radiod-select');
const refreshBtn = document.getElementById('refresh-btn');
const channelList = document.getElementById('channel-list');
const channelDetail = document.getElementById('channel-detail');
const statusBar = document.getElementById('status-bar');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    discoverRadiod();
    
    // Event Listeners
    radiodSelect.addEventListener('change', onRadiodSelected);
    refreshBtn.addEventListener('click', discoverRadiod);
});

// Discover radiod instances
async function discoverRadiod() {
    setStatus('Discovering radiod instances...', 'info');
    radiodSelect.disabled = true;
    radiodSelect.innerHTML = '<option value="">Discovering...</option>';
    
    try {
        const response = await fetch(`${API_BASE}/api/discover`);
        const data = await response.json();
        
        if (data.success && data.instances.length > 0) {
            radiodSelect.innerHTML = '<option value="">Select a radiod instance...</option>';
            data.instances.forEach(instance => {
                const option = document.createElement('option');
                option.value = instance.address;
                option.textContent = `${instance.name} (${instance.address})`;
                radiodSelect.appendChild(option);
            });
            radiodSelect.disabled = false;
            setStatus(`Found ${data.instances.length} radiod instance(s)`, 'success');
        } else {
            radiodSelect.innerHTML = '<option value="">No instances found</option>';
            setStatus('No radiod instances found on network', 'error');
        }
    } catch (error) {
        console.error('Discovery error:', error);
        radiodSelect.innerHTML = '<option value="">Error discovering instances</option>';
        setStatus(`Error: ${error.message}`, 'error');
    }
}

// Handle radiod selection
async function onRadiodSelected(event) {
    const address = event.target.value;
    if (!address) {
        clearChannels();
        return;
    }
    
    selectedRadiod = address;
    await loadChannels(address);
}

// Load channels for selected radiod
async function loadChannels(address) {
    setStatus('Loading channels...', 'info');
    channelList.innerHTML = '<div class="empty-state"><p>Loading...</p></div>';
    
    try {
        const response = await fetch(`${API_BASE}/api/channels/${encodeURIComponent(address)}`);
        const data = await response.json();
        
        if (data.success && data.channels.length > 0) {
            displayChannels(data.channels);
            setStatus(`Loaded ${data.channels.length} channel(s)`, 'success');
        } else {
            channelList.innerHTML = '<div class="empty-state"><p>No channels found</p></div>';
            setStatus('No active channels', 'info');
        }
    } catch (error) {
        console.error('Error loading channels:', error);
        channelList.innerHTML = '<div class="empty-state"><p>Error loading channels</p></div>';
        setStatus(`Error: ${error.message}`, 'error');
    }
}

// Display channels in list
function displayChannels(channels) {
    channelList.innerHTML = '';
    
    channels.forEach(channel => {
        const item = document.createElement('div');
        item.className = 'channel-item';
        item.dataset.ssrc = channel.ssrc;
        
        const freq = formatFrequency(channel.frequency);
        const destination = channel.destination || 'N/A';
        const samprate = formatNumber(channel.sample_rate);
        
        item.innerHTML = `
            <div class="freq">${freq}</div>
            <div class="info">${channel.preset} • ${samprate} Hz</div>
            <div class="info">${destination}</div>
            <div class="ssrc">SSRC: ${channel.ssrc}</div>
        `;
        
        item.addEventListener('click', () => selectChannel(channel.ssrc));
        channelList.appendChild(item);
    });
}

// Select and display channel details
async function selectChannel(ssrc) {
    // If clicking the same channel, do nothing
    if (selectedSSRC === ssrc && refreshInterval) {
        return;
    }
    
    // Clear existing refresh interval FIRST
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
    
    // Update UI
    document.querySelectorAll('.channel-item').forEach(item => {
        item.classList.toggle('active', item.dataset.ssrc == ssrc);
    });
    
    // Set the selected SSRC
    selectedSSRC = ssrc;
    
    // Reset error counter for new channel
    consecutiveErrors = 0;
    
    // Load channel details immediately
    await loadChannelDetails(ssrc);
    
    // Start auto-refresh ONLY for this SSRC
    refreshInterval = setInterval(() => {
        // Double-check we're still on this channel
        if (selectedSSRC === ssrc) {
            loadChannelDetails(ssrc);
        }
    }, 1000);
}

// Load detailed channel status
async function loadChannelDetails(ssrc) {
    // Only refresh if this is the currently selected channel
    if (!selectedRadiod || selectedSSRC !== ssrc) {
        return;
    }
    
    // Prevent overlapping refreshes
    if (isRefreshing) {
        return;
    }
    
    isRefreshing = true;
    
    try {
        const response = await fetch(
            `${API_BASE}/api/channel/${encodeURIComponent(selectedRadiod)}/${ssrc}`
        );
        const data = await response.json();
        
        if (data.success) {
            // Only update if still on this channel
            if (selectedSSRC === ssrc) {
                displayChannelDetails(data.status);
                consecutiveErrors = 0; // Reset error counter on success
            }
        } else {
            consecutiveErrors++;
            
            if (response.status === 504) {
                // Timeout error
                setStatus(`Channel ${ssrc} timeout (${consecutiveErrors}/${MAX_CONSECUTIVE_ERRORS})`, 'error');
                
                // Stop auto-refresh after too many timeouts
                if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS && refreshInterval) {
                    clearInterval(refreshInterval);
                    refreshInterval = null;
                    setStatus(`Channel ${ssrc} not responding - auto-refresh stopped. Channel may be inactive.`, 'error');
                }
            } else {
                setStatus(`Error: ${data.error}`, 'error');
            }
        }
    } catch (error) {
        consecutiveErrors++;
        console.error('Error loading channel details:', error);
        setStatus(`Network error (${consecutiveErrors}/${MAX_CONSECUTIVE_ERRORS}): ${error.message}`, 'error');
        
        // Stop refresh on repeated network errors
        if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS && refreshInterval) {
            clearInterval(refreshInterval);
            refreshInterval = null;
            setStatus('Too many errors - auto-refresh stopped. Try selecting the channel again.', 'error');
        }
    } finally {
        isRefreshing = false;
    }
}

// Display channel details
function displayChannelDetails(status) {
    const template = document.getElementById('channel-detail-template');
    const clone = template.content.cloneNode(true);
    
    // Populate values
    clone.querySelector('.ssrc-value').textContent = status.ssrc;
    clone.querySelector('.ssrc-detail-value').textContent = status.ssrc;
    clone.querySelector('.freq-value').textContent = formatFrequency(status.frequency);
    clone.querySelector('.preset-value').textContent = status.preset || 'N/A';
    
    // Filter
    clone.querySelector('.low-edge-value').textContent = formatNumber(status.low_edge) + ' Hz';
    clone.querySelector('.high-edge-value').textContent = formatNumber(status.high_edge) + ' Hz';
    clone.querySelector('.bandwidth-value').textContent = formatNumber(status.bandwidth) + ' Hz';
    clone.querySelector('.kaiser-beta-value').textContent = 
        status.kaiser_beta !== null ? status.kaiser_beta.toFixed(2) : 'N/A';
    clone.querySelector('.filter-blocksize-value').textContent = 
        status.filter_blocksize !== null ? formatNumber(status.filter_blocksize) : 'N/A';
    clone.querySelector('.filter-fir-length-value').textContent = 
        status.filter_fir_length !== null ? formatNumber(status.filter_fir_length) : 'N/A';
    
    // Output
    clone.querySelector('.samprate-value').textContent = formatNumber(status.sample_rate) + ' Hz';
    clone.querySelector('.encoding-value').textContent = status.encoding || 'N/A';
    clone.querySelector('.destination-value').textContent = status.destination || 'N/A';
    
    // Signal
    clone.querySelector('.snr-value').textContent = 
        status.snr !== null ? formatDecimal(status.snr) + ' dB' : 'N/A';
    clone.querySelector('.baseband-value').textContent = 
        status.baseband_power !== null ? formatDecimal(status.baseband_power) + ' dB' : 'N/A';
    clone.querySelector('.noise-value').textContent = 
        status.noise_density !== null ? formatDecimal(status.noise_density) + ' dB/Hz' : 'N/A';
    clone.querySelector('.if-power-value').textContent = 
        status.if_power !== null ? formatDecimal(status.if_power) + ' dB' : 'N/A';
    
    // Demodulation
    const demodTypes = {0: 'Linear', 1: 'FM', 2: 'WFM', 3: 'Spectrum'};
    clone.querySelector('.demod-type-value').textContent = 
        demodTypes[status.demod_type] || 'Unknown';
    
    const pllStatus = status.pll_enable 
        ? (status.pll_lock ? 'Locked' : 'Unlocked')
        : 'Disabled';
    clone.querySelector('.pll-status-value').textContent = pllStatus;
    
    clone.querySelector('.pll-bw-value').textContent = 
        status.pll_bw !== null ? formatDecimal(status.pll_bw) + ' Hz' : 'N/A';
    
    clone.querySelector('.squelch-value').textContent = 
        status.squelch_open !== null ? formatDecimal(status.squelch_open) + ' dB' : 'N/A';
    
    // LO Frequencies
    clone.querySelector('.first-lo-value').textContent = 
        status.first_lo_frequency ? formatFrequency(status.first_lo_frequency) : 'N/A';
    clone.querySelector('.second-lo-value').textContent = 
        status.second_lo_frequency ? formatFrequency(status.second_lo_frequency) : 'N/A';
    clone.querySelector('.shift-freq-value').textContent = 
        status.shift_frequency !== null ? formatNumber(status.shift_frequency) + ' Hz' : 'N/A';
    clone.querySelector('.doppler-freq-value').textContent = 
        status.doppler_frequency !== null ? formatDecimal(status.doppler_frequency) + ' Hz' : 'N/A';
    
    // Hardware
    clone.querySelector('.lna-gain-value').textContent = 
        status.lna_gain !== null ? formatDecimal(status.lna_gain) + ' dB' : 'N/A';
    clone.querySelector('.mixer-gain-value').textContent = 
        status.mixer_gain !== null ? formatDecimal(status.mixer_gain) + ' dB' : 'N/A';
    clone.querySelector('.if-gain-value').textContent = 
        status.if_gain !== null ? formatDecimal(status.if_gain) + ' dB' : 'N/A';
    
    // Statistics
    clone.querySelector('.data-packets-value').textContent = 
        formatNumber(status.output_data_packets || 0);
    clone.querySelector('.meta-packets-value').textContent = 
        formatNumber(status.output_metadata_packets || 0);
    clone.querySelector('.output-errors-value').textContent = 
        formatNumber(status.output_errors || 0);
    clone.querySelector('.filter-drops-value').textContent = 
        formatNumber(status.filter_drops || 0);
    
    // Gain & AGC
    clone.querySelector('.agc-value').textContent = status.agc_enable ? 'ON' : 'OFF';
    clone.querySelector('.gain-value').textContent = formatDecimal(status.gain) + ' dB';
    clone.querySelector('.headroom-value').textContent = 
        status.headroom !== null ? formatDecimal(status.headroom) + ' dB' : 'N/A';
    clone.querySelector('.agc-hangtime-value').textContent = 
        status.agc_hangtime !== null ? formatDecimal(status.agc_hangtime) + ' s' : 'N/A';
    clone.querySelector('.agc-recovery-value').textContent = 
        status.agc_recovery_rate !== null ? formatDecimal(status.agc_recovery_rate) + ' dB/s' : 'N/A';
    clone.querySelector('.rf-gain-value').textContent = 
        status.rf_gain !== null ? formatDecimal(status.rf_gain) + ' dB' : 'N/A';
    clone.querySelector('.rf-atten-value').textContent = 
        status.rf_atten !== null ? formatDecimal(status.rf_atten) + ' dB' : 'N/A';
    clone.querySelector('.rf-agc-value').textContent = 
        status.rf_agc !== null ? (status.rf_agc ? 'ON' : 'OFF') : 'N/A';
    
    // Store current status for edit mode
    currentStatus = status;
    
    // Close button
    clone.querySelector('.close-btn').addEventListener('click', closeChannelDetails);
    
    // Replace content
    channelDetail.innerHTML = '';
    channelDetail.appendChild(clone);
    
    // Add edit mode event listeners after DOM is updated
    const editModeBtn = channelDetail.querySelector('.edit-mode-btn');
    const applyBtn = channelDetail.querySelector('.apply-btn');
    const resetBtn = channelDetail.querySelector('.reset-btn');
    
    if (editModeBtn) {
        editModeBtn.addEventListener('click', toggleEditMode);
    }
    if (applyBtn) {
        applyBtn.addEventListener('click', applyChanges);
    }
    if (resetBtn) {
        resetBtn.addEventListener('click', () => populateEditControls(currentStatus));
    }
    
    // Populate edit controls with current values
    populateEditControls(status);
}

// Toggle edit mode
function toggleEditMode() {
    editMode = !editMode;
    setEditModeUI(editMode);
}

// Set edit mode UI state
function setEditModeUI(enabled) {
    const editModeBtn = channelDetail.querySelector('.edit-mode-btn');
    const editControls = channelDetail.querySelectorAll('.edit-control');
    const viewValues = channelDetail.querySelectorAll('.value');
    const editOnlyElements = channelDetail.querySelectorAll('.edit-only');
    const refreshText = channelDetail.querySelector('.refresh-text');
    
    if (enabled) {
        // Enter edit mode
        editModeBtn.textContent = '👁️ View';
        editModeBtn.classList.add('active');
        
        // Show edit controls, hide view values
        editControls.forEach(el => el.style.display = '');
        viewValues.forEach(el => el.style.display = 'none');
        editOnlyElements.forEach(el => el.style.display = '');
        
        // Pause auto-refresh
        if (refreshInterval) {
            clearInterval(refreshInterval);
            refreshInterval = null;
        }
        if (refreshText) {
            refreshText.textContent = 'Auto-refresh paused (edit mode)';
        }
        
        setStatus('Edit mode enabled - modify parameters and click Apply', 'info');
    } else {
        // Exit edit mode
        editModeBtn.textContent = '✏️ Edit';
        editModeBtn.classList.remove('active');
        
        // Hide edit controls, show view values
        editControls.forEach(el => el.style.display = 'none');
        viewValues.forEach(el => el.style.display = '');
        editOnlyElements.forEach(el => el.style.display = 'none');
        
        // Resume auto-refresh
        if (selectedSSRC && !refreshInterval) {
            refreshInterval = setInterval(() => loadChannelDetails(selectedSSRC), 1000);
        }
        if (refreshText) {
            refreshText.textContent = 'Auto-refreshing every 1s';
        }
        
        setStatus('View mode - monitoring channel', 'success');
    }
}

// Populate edit controls with current values
function populateEditControls(status) {
    if (!status) return;
    
    // Tuning
    const freqInput = channelDetail.querySelector('.freq-input');
    const presetInput = channelDetail.querySelector('.preset-input');
    const samprateInput = channelDetail.querySelector('.samprate-input');
    
    if (freqInput) freqInput.value = (status.frequency / 1e6).toFixed(6);
    if (presetInput) presetInput.value = status.preset || 'iq';
    if (samprateInput) samprateInput.value = status.sample_rate || 12000;
    
    // Filter
    const lowEdgeInput = channelDetail.querySelector('.low-edge-input');
    const highEdgeInput = channelDetail.querySelector('.high-edge-input');
    const kaiserBetaInput = channelDetail.querySelector('.kaiser-beta-input');
    
    if (lowEdgeInput) lowEdgeInput.value = status.low_edge || 0;
    if (highEdgeInput) highEdgeInput.value = status.high_edge || 0;
    if (kaiserBetaInput) kaiserBetaInput.value = status.kaiser_beta || 3.5;
    
    // Output
    const channelsInput = channelDetail.querySelector('.channels-input');
    const outputLevelInput = channelDetail.querySelector('.output-level-input');
    
    if (channelsInput) channelsInput.value = '1'; // Default to mono
    if (outputLevelInput) outputLevelInput.value = 0;
    
    // Shift
    const shiftInput = channelDetail.querySelector('.shift-input');
    if (shiftInput) shiftInput.value = status.shift_frequency || 0;
    
    // AGC
    const agcEnableInput = channelDetail.querySelector('.agc-enable-input');
    const gainInput = channelDetail.querySelector('.gain-input');
    const headroomInput = channelDetail.querySelector('.headroom-input');
    const hangtimeInput = channelDetail.querySelector('.hangtime-input');
    const recoveryInput = channelDetail.querySelector('.recovery-input');
    
    if (agcEnableInput) agcEnableInput.checked = status.agc_enable || false;
    if (gainInput) gainInput.value = status.gain || 0;
    if (headroomInput) headroomInput.value = status.headroom || 5;
    if (hangtimeInput) hangtimeInput.value = status.agc_hangtime || 1;
    if (recoveryInput) recoveryInput.value = status.agc_recovery_rate || 1;
    
    // PLL
    const pllEnableInput = channelDetail.querySelector('.pll-enable-input');
    const pllBwInput = channelDetail.querySelector('.pll-bw-input');
    const pllSquareInput = channelDetail.querySelector('.pll-square-input');
    
    if (pllEnableInput) pllEnableInput.checked = status.pll_enable || false;
    if (pllBwInput) pllBwInput.value = status.pll_bw || 20;
    if (pllSquareInput) pllSquareInput.checked = false;
    
    // Squelch
    const squelchOpenInput = channelDetail.querySelector('.squelch-open-input');
    const squelchCloseInput = channelDetail.querySelector('.squelch-close-input');
    const snrSquelchInput = channelDetail.querySelector('.snr-squelch-input');
    
    if (squelchOpenInput) squelchOpenInput.value = status.squelch_open || -10;
    if (squelchCloseInput) squelchCloseInput.value = status.squelch_close || -11;
    if (snrSquelchInput) snrSquelchInput.checked = false;
    
    // Advanced
    const isbInput = channelDetail.querySelector('.isb-input');
    const envelopeInput = channelDetail.querySelector('.envelope-input');
    const opusBitrateInput = channelDetail.querySelector('.opus-bitrate-input');
    
    if (isbInput) isbInput.checked = false;
    if (envelopeInput) envelopeInput.checked = false;
    if (opusBitrateInput) opusBitrateInput.value = 32000;
}

// Apply changes from edit mode
async function applyChanges() {
    if (!selectedRadiod || !selectedSSRC) {
        setStatus('Error: No channel selected', 'error');
        return;
    }
    
    setStatus('Applying changes...', 'info');
    
    const errors = [];
    const successes = [];
    
    try {
        // Get all input values
        const freqInput = channelDetail.querySelector('.freq-input');
        const presetInput = channelDetail.querySelector('.preset-input');
        const samprateInput = channelDetail.querySelector('.samprate-input');
        const lowEdgeInput = channelDetail.querySelector('.low-edge-input');
        const highEdgeInput = channelDetail.querySelector('.high-edge-input');
        const kaiserBetaInput = channelDetail.querySelector('.kaiser-beta-input');
        const gainInput = channelDetail.querySelector('.gain-input');
        const agcEnableInput = channelDetail.querySelector('.agc-enable-input');
        const shiftInput = channelDetail.querySelector('.shift-input');
        const outputLevelInput = channelDetail.querySelector('.output-level-input');
        const channelsInput = channelDetail.querySelector('.channels-input');
        const headroomInput = channelDetail.querySelector('.headroom-input');
        const hangtimeInput = channelDetail.querySelector('.hangtime-input');
        const recoveryInput = channelDetail.querySelector('.recovery-input');
        const pllEnableInput = channelDetail.querySelector('.pll-enable-input');
        const pllBwInput = channelDetail.querySelector('.pll-bw-input');
        const pllSquareInput = channelDetail.querySelector('.pll-square-input');
        const squelchOpenInput = channelDetail.querySelector('.squelch-open-input');
        const squelchCloseInput = channelDetail.querySelector('.squelch-close-input');
        const snrSquelchInput = channelDetail.querySelector('.snr-squelch-input');
        const isbInput = channelDetail.querySelector('.isb-input');
        const envelopeInput = channelDetail.querySelector('.envelope-input');
        const opusBitrateInput = channelDetail.querySelector('.opus-bitrate-input');
        
        // 1. Basic tuning
        const tuneParams = {};
        let hasTuneChanges = false;
        
        if (freqInput && parseFloat(freqInput.value) !== (currentStatus.frequency / 1e6)) {
            tuneParams.frequency = parseFloat(freqInput.value) * 1e6;
            hasTuneChanges = true;
        }
        if (presetInput && presetInput.value !== currentStatus.preset) {
            tuneParams.preset = presetInput.value;
            hasTuneChanges = true;
        }
        if (samprateInput && parseInt(samprateInput.value) !== currentStatus.sample_rate) {
            tuneParams.sample_rate = parseInt(samprateInput.value);
            hasTuneChanges = true;
        }
        if (lowEdgeInput && parseFloat(lowEdgeInput.value) !== currentStatus.low_edge) {
            tuneParams.low_edge = parseFloat(lowEdgeInput.value);
            hasTuneChanges = true;
        }
        if (highEdgeInput && parseFloat(highEdgeInput.value) !== currentStatus.high_edge) {
            tuneParams.high_edge = parseFloat(highEdgeInput.value);
            hasTuneChanges = true;
        }
        if (gainInput && parseFloat(gainInput.value) !== currentStatus.gain) {
            tuneParams.gain = parseFloat(gainInput.value);
            hasTuneChanges = true;
        }
        if (agcEnableInput && agcEnableInput.checked !== currentStatus.agc_enable) {
            tuneParams.agc_enable = agcEnableInput.checked;
            hasTuneChanges = true;
        }
        
        if (hasTuneChanges) {
            const result = await fetch(`${API_BASE}/api/tune/${encodeURIComponent(selectedRadiod)}/${selectedSSRC}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(tuneParams)
            });
            const data = await result.json();
            if (data.success) {
                successes.push('Tuning updated');
            } else {
                errors.push(`Tuning: ${data.error}`);
            }
        }
        
        // 2. Filter (kaiser beta)
        if (kaiserBetaInput && parseFloat(kaiserBetaInput.value) !== currentStatus.kaiser_beta) {
            const result = await fetch(`${API_BASE}/api/filter/${encodeURIComponent(selectedRadiod)}/${selectedSSRC}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({kaiser_beta: parseFloat(kaiserBetaInput.value)})
            });
            const data = await result.json();
            if (data.success) {
                successes.push('Filter updated');
            } else {
                errors.push(`Filter: ${data.error}`);
            }
        }
        
        // 3. AGC advanced
        if (headroomInput || hangtimeInput || recoveryInput) {
            const agcParams = {
                enable: agcEnableInput ? agcEnableInput.checked : currentStatus.agc_enable
            };
            if (headroomInput) agcParams.headroom = parseFloat(headroomInput.value);
            if (hangtimeInput) agcParams.hangtime = parseFloat(hangtimeInput.value);
            if (recoveryInput) agcParams.recovery_rate = parseFloat(recoveryInput.value);
            
            const result = await fetch(`${API_BASE}/api/agc/${encodeURIComponent(selectedRadiod)}/${selectedSSRC}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(agcParams)
            });
            const data = await result.json();
            if (data.success) {
                successes.push('AGC configured');
            } else {
                errors.push(`AGC: ${data.error}`);
            }
        }
        
        // 4. Shift frequency
        if (shiftInput && parseFloat(shiftInput.value) !== (currentStatus.shift_frequency || 0)) {
            const result = await fetch(`${API_BASE}/api/shift/${encodeURIComponent(selectedRadiod)}/${selectedSSRC}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({shift_hz: parseFloat(shiftInput.value)})
            });
            const data = await result.json();
            if (data.success) {
                successes.push('Shift frequency set');
            } else {
                errors.push(`Shift: ${data.error}`);
            }
        }
        
        // 5. Output level
        if (outputLevelInput && parseFloat(outputLevelInput.value) !== 0) {
            const result = await fetch(`${API_BASE}/api/output_level/${encodeURIComponent(selectedRadiod)}/${selectedSSRC}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({level: parseFloat(outputLevelInput.value)})
            });
            const data = await result.json();
            if (data.success) {
                successes.push('Output level set');
            } else {
                errors.push(`Output level: ${data.error}`);
            }
        }
        
        // 6. Output channels
        if (channelsInput) {
            const result = await fetch(`${API_BASE}/api/output_channels/${encodeURIComponent(selectedRadiod)}/${selectedSSRC}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({channels: parseInt(channelsInput.value)})
            });
            const data = await result.json();
            if (data.success) {
                successes.push('Output channels set');
            } else {
                errors.push(`Output channels: ${data.error}`);
            }
        }
        
        // 7. PLL
        if (pllEnableInput || pllBwInput || pllSquareInput) {
            const pllParams = {};
            if (pllEnableInput) pllParams.enable = pllEnableInput.checked;
            if (pllBwInput) pllParams.bandwidth = parseFloat(pllBwInput.value);
            if (pllSquareInput) pllParams.square = pllSquareInput.checked;
            
            const result = await fetch(`${API_BASE}/api/pll/${encodeURIComponent(selectedRadiod)}/${selectedSSRC}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(pllParams)
            });
            const data = await result.json();
            if (data.success) {
                successes.push('PLL configured');
            } else {
                errors.push(`PLL: ${data.error}`);
            }
        }
        
        // 8. Squelch
        if (squelchOpenInput || squelchCloseInput || snrSquelchInput) {
            const squelchParams = {};
            if (squelchOpenInput) squelchParams.open_threshold = parseFloat(squelchOpenInput.value);
            if (squelchCloseInput) squelchParams.close_threshold = parseFloat(squelchCloseInput.value);
            if (snrSquelchInput) squelchParams.snr_squelch = snrSquelchInput.checked;
            
            const result = await fetch(`${API_BASE}/api/squelch/${encodeURIComponent(selectedRadiod)}/${selectedSSRC}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(squelchParams)
            });
            const data = await result.json();
            if (data.success) {
                successes.push('Squelch configured');
            } else {
                errors.push(`Squelch: ${data.error}`);
            }
        }
        
        // 9. ISB
        if (isbInput && isbInput.checked) {
            const result = await fetch(`${API_BASE}/api/isb/${encodeURIComponent(selectedRadiod)}/${selectedSSRC}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({enable: isbInput.checked})
            });
            const data = await result.json();
            if (data.success) {
                successes.push('ISB configured');
            } else {
                errors.push(`ISB: ${data.error}`);
            }
        }
        
        // 10. Envelope detection
        if (envelopeInput && envelopeInput.checked) {
            const result = await fetch(`${API_BASE}/api/envelope/${encodeURIComponent(selectedRadiod)}/${selectedSSRC}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({enable: envelopeInput.checked})
            });
            const data = await result.json();
            if (data.success) {
                successes.push('Envelope detection configured');
            } else {
                errors.push(`Envelope: ${data.error}`);
            }
        }
        
        // 11. Opus bitrate
        if (opusBitrateInput && parseInt(opusBitrateInput.value) !== 32000) {
            const result = await fetch(`${API_BASE}/api/opus_bitrate/${encodeURIComponent(selectedRadiod)}/${selectedSSRC}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({bitrate: parseInt(opusBitrateInput.value)})
            });
            const data = await result.json();
            if (data.success) {
                successes.push('Opus bitrate set');
            } else {
                errors.push(`Opus: ${data.error}`);
            }
        }
        
        // Show results
        if (errors.length > 0) {
            setStatus(`Applied with errors: ${errors.join(', ')}`, 'error');
        } else if (successes.length > 0) {
            setStatus(`Successfully applied: ${successes.join(', ')}`, 'success');
            // Exit edit mode and refresh
            editMode = false;
            setEditModeUI(false);
            await loadChannelDetails(selectedSSRC);
        } else {
            setStatus('No changes detected', 'info');
        }
        
    } catch (error) {
        console.error('Error applying changes:', error);
        setStatus(`Error applying changes: ${error.message}`, 'error');
    }
}

// Close channel details
function closeChannelDetails() {
    // Clear interval first
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
    
    // Clear selected SSRC and refresh flag
    selectedSSRC = null;
    isRefreshing = false;
    consecutiveErrors = 0;
    editMode = false;
    currentStatus = null;
    
    // Remove active class from all channels
    document.querySelectorAll('.channel-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // Show empty state
    channelDetail.innerHTML = `
        <div class="empty-state">
            <h2>No Channel Selected</h2>
            <p>Select a channel from the list to view details</p>
        </div>
    `;
}

// Clear channels
function clearChannels() {
    // Stop any refresh first
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
    
    // Clear state
    selectedSSRC = null;
    selectedRadiod = null;
    isRefreshing = false;
    consecutiveErrors = 0;
    
    // Clear UI
    document.querySelectorAll('.channel-item').forEach(item => {
        item.classList.remove('active');
    });
    
    channelList.innerHTML = `
        <div class="empty-state">
            <p>Select a radiod instance to view channels</p>
        </div>
    `;
    
    channelDetail.innerHTML = `
        <div class="empty-state">
            <h2>No Channel Selected</h2>
            <p>Select a channel from the list to view details</p>
        </div>
    `;
}

// Format frequency for display
function formatFrequency(freq) {
    if (!freq || freq === 0) return 'N/A';
    
    if (freq >= 1e9) {
        return (freq / 1e9).toFixed(6) + ' GHz';
    } else if (freq >= 1e6) {
        return (freq / 1e6).toFixed(3) + ' MHz';
    } else if (freq >= 1e3) {
        return (freq / 1e3).toFixed(3) + ' kHz';
    } else {
        return freq.toFixed(0) + ' Hz';
    }
}

// Format number with thousand separators
function formatNumber(num) {
    if (num === null || num === undefined || num === 0) return '0';
    return num.toLocaleString('en-US');
}

// Format decimal with precision
function formatDecimal(num, precision = 1) {
    if (num === null || num === undefined) return 'N/A';
    return num.toFixed(precision);
}

// Set status message
function setStatus(message, type = 'info') {
    statusBar.textContent = message;
    statusBar.className = `status-bar ${type}`;
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});
