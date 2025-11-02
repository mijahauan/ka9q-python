"""
Tests for the tune.py CLI tool
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'examples'))

from examples.tune import parse_frequency, encoding_from_string, format_frequency, format_socket
from ka9q.types import Encoding


class TestParseFrequency:
    """Tests for parse_frequency function"""
    
    def test_parse_plain_number(self):
        """Test parsing plain number (no suffix)"""
        assert parse_frequency("14074000") == 14074000.0
        assert parse_frequency("10000000") == 10000000.0
    
    def test_parse_scientific_notation(self):
        """Test parsing scientific notation"""
        assert parse_frequency("14.074e6") == 14.074e6
        assert parse_frequency("1.8e6") == 1.8e6
        assert parse_frequency("144e6") == 144e6
    
    def test_parse_kilohertz_suffix(self):
        """Test parsing with k/K suffix"""
        assert parse_frequency("146520k") == 146520e3
        assert parse_frequency("7040K") == 7040e3
        assert parse_frequency("1.8k") == 1.8e3
    
    def test_parse_megahertz_suffix(self):
        """Test parsing with M suffix"""
        assert parse_frequency("14.074M") == 14.074e6
        assert parse_frequency("7.040M") == 7.040e6
        assert parse_frequency("146M") == 146e6
    
    def test_parse_gigahertz_suffix(self):
        """Test parsing with G suffix"""
        assert parse_frequency("1.2G") == 1.2e9
        assert parse_frequency("2.4G") == 2.4e9
    
    def test_parse_lowercase_suffix(self):
        """Test that lowercase suffixes work (should be uppercased)"""
        assert parse_frequency("14.074m") == 14.074e6
        assert parse_frequency("7040k") == 7040e3
        assert parse_frequency("1.2g") == 1.2e9
    
    def test_parse_with_whitespace(self):
        """Test parsing with leading/trailing whitespace"""
        assert parse_frequency("  14.074M  ") == 14.074e6
        assert parse_frequency("\t7.040M\n") == 7.040e6
    
    def test_parse_fractional_multiplier(self):
        """Test parsing fractional values with multipliers"""
        assert parse_frequency("0.5M") == 0.5e6
        assert parse_frequency("146.52M") == 146.52e6
    
    def test_parse_invalid_raises_error(self):
        """Test that invalid strings raise ValueError"""
        with pytest.raises(ValueError):
            parse_frequency("invalid")
        with pytest.raises(ValueError):
            parse_frequency("abc.defM")


class TestEncodingFromString:
    """Tests for encoding_from_string function"""
    
    def test_parse_s16be(self):
        """Test parsing S16BE encoding"""
        result = encoding_from_string("S16BE")
        assert result == Encoding.S16BE
        assert result == 1
    
    def test_parse_s16le(self):
        """Test parsing S16LE encoding"""
        result = encoding_from_string("S16LE")
        assert result == Encoding.S16LE
        assert result == 2
    
    def test_parse_f32(self):
        """Test parsing F32 encoding"""
        result = encoding_from_string("F32")
        assert result == Encoding.F32
        assert result == 3
    
    def test_parse_f16(self):
        """Test parsing F16 encoding"""
        result = encoding_from_string("F16")
        assert result == Encoding.F16
        assert result == 4
    
    def test_parse_opus(self):
        """Test parsing OPUS encoding"""
        result = encoding_from_string("OPUS")
        assert result == Encoding.OPUS
        assert result == 5
    
    def test_parse_lowercase(self):
        """Test that lowercase encoding names work"""
        assert encoding_from_string("s16be") == Encoding.S16BE
        assert encoding_from_string("opus") == Encoding.OPUS
        assert encoding_from_string("f32") == Encoding.F32
    
    def test_parse_invalid_returns_none(self):
        """Test that invalid encoding returns None"""
        result = encoding_from_string("INVALID")
        assert result is None


class TestFormatFrequency:
    """Tests for format_frequency function"""
    
    def test_format_hertz(self):
        """Test formatting frequencies in Hz range"""
        result = format_frequency(500.0)
        assert "500" in result
        assert "Hz" in result
    
    def test_format_kilohertz(self):
        """Test formatting frequencies in kHz range"""
        # Note: 7040e3 = 7.04 MHz, which is >= 1e6, so formats as MHz
        result = format_frequency(7040e3)
        assert "7.04" in result
        assert "MHz" in result
        
        # Test a true kHz value
        result = format_frequency(500e3)
        assert "500" in result
        assert "kHz" in result
    
    def test_format_megahertz(self):
        """Test formatting frequencies in MHz range"""
        result = format_frequency(14.074e6)
        assert "14.074" in result
        assert "MHz" in result
    
    def test_format_gigahertz(self):
        """Test formatting frequencies in GHz range"""
        result = format_frequency(1.296e9)
        assert "1.296" in result
        assert "GHz" in result
    
    def test_format_precision(self):
        """Test that formatting maintains appropriate precision"""
        result = format_frequency(14.074123e6)
        # Should have 6 decimal places for MHz
        assert "14.074123" in result


class TestFormatSocket:
    """Tests for format_socket function"""
    
    def test_format_valid_socket(self):
        """Test formatting valid socket address"""
        socket_dict = {'address': '239.1.2.3', 'port': 5006}
        result = format_socket(socket_dict)
        assert result == "239.1.2.3:5006"
    
    def test_format_localhost(self):
        """Test formatting localhost socket"""
        socket_dict = {'address': '127.0.0.1', 'port': 12345}
        result = format_socket(socket_dict)
        assert result == "127.0.0.1:12345"
    
    def test_format_none_returns_na(self):
        """Test that None returns N/A"""
        result = format_socket(None)
        assert result == "N/A"
    
    def test_format_missing_address(self):
        """Test formatting socket dict without address"""
        socket_dict = {'port': 5006}
        result = format_socket(socket_dict)
        assert result == "N/A"
    
    def test_format_empty_dict(self):
        """Test formatting empty dict"""
        result = format_socket({})
        assert result == "N/A"


class TestCLIArgumentParsing:
    """Tests for CLI argument parsing (integration-style tests)"""
    
    def test_required_arguments(self):
        """Test that required arguments are enforced"""
        import argparse
        from examples.tune import main
        
        # Mock sys.argv to test argument parsing
        # These would fail in actual execution but we're testing the parser
        # In a real test environment, you'd use argparse testing utilities
        pass  # This would require more complex mocking
    
    def test_ssrc_hex_parsing(self):
        """Test that SSRC can be parsed as hex"""
        # Test the lambda function used for SSRC parsing
        ssrc_parser = lambda x: int(x, 0)
        
        # Test decimal
        assert ssrc_parser("14074000") == 14074000
        
        # Test hex with 0x prefix
        assert ssrc_parser("0x12345678") == 0x12345678
        
        # Test octal with 0o prefix
        assert ssrc_parser("0o777") == 0o777


class TestCLIOutputFormatting:
    """Tests for CLI output formatting"""
    
    def test_encoding_names(self):
        """Test encoding name mapping"""
        enc_names = {
            0: 'None', 
            1: 'S16BE', 
            2: 'S16LE', 
            3: 'F32', 
            4: 'F16', 
            5: 'OPUS'
        }
        
        assert enc_names[Encoding.NO_ENCODING] == 'None'
        assert enc_names[Encoding.S16BE] == 'S16BE'
        assert enc_names[Encoding.S16LE] == 'S16LE'
        assert enc_names[Encoding.F32] == 'F32'
        assert enc_names[Encoding.F16] == 'F16'
        assert enc_names[Encoding.OPUS] == 'OPUS'


class TestFrequencyParsingSuite:
    """Comprehensive frequency parsing test suite"""
    
    @pytest.mark.parametrize("freq_str,expected", [
        ("14074000", 14074000.0),
        ("14.074e6", 14.074e6),
        ("14.074M", 14.074e6),
        ("14.074m", 14.074e6),
        ("7040k", 7040e3),
        ("7040K", 7040e3),
        ("7.040M", 7.040e6),
        ("146.52M", 146.52e6),
        ("1.296G", 1.296e9),
        ("440M", 440e6),
        ("10M", 10e6),
        ("3.5M", 3.5e6),
        ("0.5M", 0.5e6),
        ("1800k", 1800e3),
    ])
    def test_parse_frequency_suite(self, freq_str, expected):
        """Test parsing various frequency formats"""
        result = parse_frequency(freq_str)
        assert abs(result - expected) < 1.0, f"Failed for {freq_str}"


class TestEncodingParsingSuite:
    """Comprehensive encoding parsing test suite"""
    
    @pytest.mark.parametrize("enc_str,expected", [
        ("S16BE", Encoding.S16BE),
        ("s16be", Encoding.S16BE),
        ("S16LE", Encoding.S16LE),
        ("s16le", Encoding.S16LE),
        ("F32", Encoding.F32),
        ("f32", Encoding.F32),
        ("F16", Encoding.F16),
        ("f16", Encoding.F16),
        ("OPUS", Encoding.OPUS),
        ("opus", Encoding.OPUS),
    ])
    def test_parse_encoding_suite(self, enc_str, expected):
        """Test parsing various encoding formats"""
        result = encoding_from_string(enc_str)
        assert result == expected


class TestFilterEdgeParsing:
    """Tests for filter edge parsing (uses same parse_frequency)"""
    
    def test_parse_audio_filter_edges(self):
        """Test parsing typical audio filter edges"""
        # USB filter: 300 Hz to 2700 Hz
        low = parse_frequency("300")
        high = parse_frequency("2700")
        assert low == 300.0
        assert high == 2700.0
    
    def test_parse_negative_filter_edges(self):
        """Test parsing negative filter edges (for IQ mode)"""
        # IQ filter: -24 kHz to +24 kHz
        low = parse_frequency("-24k")
        high = parse_frequency("24k")
        assert low == -24e3
        assert high == 24e3
    
    def test_parse_filter_edge_with_decimals(self):
        """Test parsing filter edges with decimal points"""
        low = parse_frequency("1.5k")
        high = parse_frequency("2.4k")
        assert abs(low - 1500.0) < 1.0
        assert abs(high - 2400.0) < 1.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
