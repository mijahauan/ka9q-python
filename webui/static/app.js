// radiod Web UI - Main Application
const API_BASE = '';
let selectedRadiod = null;
let selectedSSRC = null;
let refreshInterval = null;
let isRefreshing = false; // Prevent overlapping refreshes
let consecutiveErrors = 0; // Track consecutive errors
const MAX_CONSECUTIVE_ERRORS = 3; // Stop refreshing after this many errors

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
    
    // Output
    clone.querySelector('.samprate-value').textContent = formatNumber(status.sample_rate) + ' Hz';
    clone.querySelector('.encoding-value').textContent = status.encoding || 'N/A';
    clone.querySelector('.destination-value').textContent = status.destination || 'N/A';
    
    // Gain & AGC
    clone.querySelector('.agc-value').textContent = status.agc_enable ? 'ON' : 'OFF';
    clone.querySelector('.gain-value').textContent = formatDecimal(status.gain) + ' dB';
    clone.querySelector('.rf-gain-value').textContent = 
        status.rf_gain !== null ? formatDecimal(status.rf_gain) + ' dB' : 'N/A';
    clone.querySelector('.rf-atten-value').textContent = 
        status.rf_atten !== null ? formatDecimal(status.rf_atten) + ' dB' : 'N/A';
    clone.querySelector('.rf-agc-value').textContent = 
        status.rf_agc !== null ? (status.rf_agc ? 'ON' : 'OFF') : 'N/A';
    
    // Signal
    clone.querySelector('.snr-value').textContent = 
        status.snr !== null ? formatDecimal(status.snr) + ' dB' : 'N/A';
    clone.querySelector('.baseband-value').textContent = 
        status.baseband_power !== null ? formatDecimal(status.baseband_power) + ' dB' : 'N/A';
    clone.querySelector('.noise-value').textContent = 
        status.noise_density !== null ? formatDecimal(status.noise_density) + ' dB/Hz' : 'N/A';
    
    // Close button
    clone.querySelector('.close-btn').addEventListener('click', closeChannelDetails);
    
    // Replace content
    channelDetail.innerHTML = '';
    channelDetail.appendChild(clone);
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
