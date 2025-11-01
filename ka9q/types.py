"""
ka9q-radio protocol types and constants

Status types from ka9q-radio/status.h
These MUST match the enum values in status.h exactly!
Verified against https://github.com/phase4ground/ka9q-radio/blob/master/status.h
"""

class StatusType:
    """TLV type identifiers for radiod status/control protocol"""
    
    EOL = 0
    COMMAND_TAG = 1
    COMMANDS = 2
    GPS_TIME = 3
    DESCRIPTION = 4
    INPUT_DATA_SOURCE_SOCKET = 5
    INPUT_DATA_DEST_SOCKET = 6
    INPUT_METADATA_SOURCE_SOCKET = 7
    INPUT_METADATA_DEST_SOCKET = 8
    INPUT_SSRC = 9
    INPUT_SAMPRATE = 10
    INPUT_METADATA_PACKETS = 11
    INPUT_DATA_PACKETS = 12
    INPUT_SAMPLES = 13
    INPUT_DROPS = 14
    INPUT_DUPES = 15
    OUTPUT_DATA_SOURCE_SOCKET = 16
    OUTPUT_DATA_DEST_SOCKET = 17
    OUTPUT_SSRC = 18
    OUTPUT_TTL = 19
    OUTPUT_SAMPRATE = 20
    OUTPUT_METADATA_PACKETS = 21
    OUTPUT_DATA_PACKETS = 22
    AD_LEVEL = 23
    CALIBRATE = 24
    LNA_GAIN = 25
    MIXER_GAIN = 26
    IF_GAIN = 27
    DC_I_OFFSET = 28
    DC_Q_OFFSET = 29
    IQ_IMBALANCE = 30
    IQ_PHASE = 31
    DIRECT_CONVERSION = 32
    RADIO_FREQUENCY = 33
    FIRST_LO_FREQUENCY = 34
    SECOND_LO_FREQUENCY = 35
    SHIFT_FREQUENCY = 36
    DOPPLER_FREQUENCY = 37
    DOPPLER_FREQUENCY_RATE = 38
    LOW_EDGE = 39
    HIGH_EDGE = 40
    KAISER_BETA = 41
    FILTER_BLOCKSIZE = 42
    FILTER_FIR_LENGTH = 43
    NOISE_BANDWIDTH = 44
    IF_POWER = 45
    BASEBAND_POWER = 46
    NOISE_DENSITY = 47
    DEMOD_TYPE = 48
    OUTPUT_CHANNELS = 49
    INDEPENDENT_SIDEBAND = 50
    PLL_ENABLE = 51
    PLL_LOCK = 52
    PLL_SQUARE = 53
    PLL_PHASE = 54
    ENVELOPE = 55
    FM_FLAT = 56
    DEMOD_SNR = 57
    FREQ_OFFSET = 58
    PEAK_DEVIATION = 59
    PL_TONE = 60
    AGC_ENABLE = 61  # Boolean, linear modes only
    HEADROOM = 62
    AGC_HANGTIME = 63
    AGC_RECOVERY_RATE = 64
    AGC_ATTACK_RATE = 65
    GAIN = 66  # AM, Linear only
    OUTPUT_LEVEL = 67
    OUTPUT_SAMPLES = 68
    OPUS_SOURCE_SOCKET = 69
    OPUS_DEST_SOCKET = 70
    OPUS_SSRC = 71
    OPUS_TTL = 72
    OPUS_BITRATE = 73
    OPUS_PACKETS = 74
    PRESET = 85  # Mode/preset name (e.g., "iq", "usb", "lsb")


# Command packet type
CMD = 1
