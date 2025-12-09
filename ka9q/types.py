"""
ka9q-radio protocol types and constants

Status types from ka9q-radio/src/status.h
These MUST match the enum values in status.h exactly!
Verified against https://github.com/ka9q/ka9q-radio (official repository)
"""

class StatusType:
    """TLV type identifiers for radiod status/control protocol"""
    
    EOL = 0
    COMMAND_TAG = 1
    CMD_CNT = 2
    GPS_TIME = 3
    
    DESCRIPTION = 4
    STATUS_DEST_SOCKET = 5
    SETOPTS = 6
    CLEAROPTS = 7
    RTP_TIMESNAP = 8
    UNUSED4 = 9
    INPUT_SAMPRATE = 10
    UNUSED6 = 11
    UNUSED7 = 12
    INPUT_SAMPLES = 13
    UNUSED8 = 14
    UNUSED9 = 15
    
    OUTPUT_DATA_SOURCE_SOCKET = 16
    OUTPUT_DATA_DEST_SOCKET = 17
    OUTPUT_SSRC = 18
    OUTPUT_TTL = 19
    OUTPUT_SAMPRATE = 20
    OUTPUT_METADATA_PACKETS = 21
    OUTPUT_DATA_PACKETS = 22
    OUTPUT_ERRORS = 23
    
    # Hardware
    CALIBRATE = 24
    LNA_GAIN = 25
    MIXER_GAIN = 26
    IF_GAIN = 27
    
    DC_I_OFFSET = 28
    DC_Q_OFFSET = 29
    IQ_IMBALANCE = 30
    IQ_PHASE = 31
    DIRECT_CONVERSION = 32
    
    # Tuning
    RADIO_FREQUENCY = 33
    FIRST_LO_FREQUENCY = 34
    SECOND_LO_FREQUENCY = 35
    SHIFT_FREQUENCY = 36
    DOPPLER_FREQUENCY = 37
    DOPPLER_FREQUENCY_RATE = 38
    
    # Filtering
    LOW_EDGE = 39
    HIGH_EDGE = 40
    KAISER_BETA = 41
    FILTER_BLOCKSIZE = 42
    FILTER_FIR_LENGTH = 43
    FILTER2 = 44
    
    # Signals
    IF_POWER = 45
    BASEBAND_POWER = 46
    NOISE_DENSITY = 47
    
    # Demodulation configuration
    DEMOD_TYPE = 48  # 0 = linear (default), 1 = FM, 2 = WFM/Stereo, 3 = spectrum
    OUTPUT_CHANNELS = 49  # 1 or 2 in Linear, otherwise 1
    INDEPENDENT_SIDEBAND = 50  # Linear only
    PLL_ENABLE = 51
    PLL_LOCK = 52
    PLL_SQUARE = 53
    PLL_PHASE = 54
    PLL_BW = 55
    ENVELOPE = 56
    SNR_SQUELCH = 57
    
    # Demodulation status
    PLL_SNR = 58  # FM, PLL linear
    FREQ_OFFSET = 59
    PEAK_DEVIATION = 60
    PL_TONE = 61
    
    # Settable gain parameters
    AGC_ENABLE = 62  # Boolean, linear modes only
    HEADROOM = 63
    AGC_HANGTIME = 64
    AGC_RECOVERY_RATE = 65
    FM_SNR = 66
    AGC_THRESHOLD = 67
    
    GAIN = 68  # AM, Linear only
    OUTPUT_LEVEL = 69
    OUTPUT_SAMPLES = 70
    
    OPUS_BIT_RATE = 71
    MINPACKET = 72
    FILTER2_BLOCKSIZE = 73
    FILTER2_FIR_LENGTH = 74
    FILTER2_KAISER_BETA = 75
    SPECTRUM_FFT_N = 76
    
    FILTER_DROPS = 77
    LOCK = 78
    
    TP1 = 79  # Test points
    TP2 = 80
    
    GAINSTEP = 81
    AD_BITS_PER_SAMPLE = 82
    SQUELCH_OPEN = 83
    SQUELCH_CLOSE = 84
    PRESET = 85  # Mode/preset name (e.g., "iq", "usb", "lsb")
    DEEMPH_TC = 86
    DEEMPH_GAIN = 87
    CONVERTER_OFFSET = 88
    PL_DEVIATION = 89
    THRESH_EXTEND = 90
    
    # Spectral analysis
    SPECTRUM_KAISER_BETA = 91
    COHERENT_BIN_SPACING = 92
    NONCOHERENT_BIN_BW = 93
    BIN_COUNT = 94
    CROSSOVER = 95
    BIN_DATA = 96
    
    RF_ATTEN = 97
    RF_GAIN = 98
    RF_AGC = 99
    FE_LOW_EDGE = 100
    FE_HIGH_EDGE = 101
    FE_ISREAL = 102
    BLOCKS_SINCE_POLL = 103
    AD_OVER = 104
    RTP_PT = 105
    STATUS_INTERVAL = 106
    OUTPUT_ENCODING = 107
    SAMPLES_SINCE_OVER = 108
    PLL_WRAPS = 109
    RF_LEVEL_CAL = 110


# Command packet type
CMD = 1

# Encoding types - must match enum encoding in ka9q-radio/src/rtp.h
class Encoding:
    """Output encoding types - values must match ka9q-radio/src/rtp.h enum encoding"""
    NO_ENCODING = 0
    S16LE = 1  # Signed 16-bit little-endian
    S16BE = 2  # Signed 16-bit big-endian
    OPUS = 3   # Opus codec
    F32 = 4    # 32-bit float (F32LE in C)
    AX25 = 5   # AX.25 packet
    F16 = 6    # 16-bit float (F16LE in C)
