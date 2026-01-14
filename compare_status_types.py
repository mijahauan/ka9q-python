#!/usr/bin/env python3
"""
Compare ka9q-radio status.h enum with ka9q-python types.py StatusType class
to identify any missing or mismatched values.
"""

import re
import subprocess

def parse_c_enum(file_path):
    """Parse C enum from status.h and return ordered list of (name, value, comment)"""
    result = subprocess.run(['cat', file_path], capture_output=True, text=True)
    content = result.stdout
    
    # Find the enum status_type block
    enum_match = re.search(r'enum status_type\s*\{(.*?)\};', content, re.DOTALL)
    if not enum_match:
        raise ValueError("Could not find enum status_type in file")
    
    enum_content = enum_match.group(1)
    
    entries = []
    current_value = 0
    
    for line in enum_content.split('\n'):
        line = line.strip()
        if not line or line.startswith('//'):
            continue
            
        # Extract name and comment
        match = re.match(r'([A-Z_][A-Z0-9_]*)\s*(?:=\s*(\d+))?\s*,?\s*(?://\s*(.*))?', line)
        if match:
            name = match.group(1)
            explicit_value = match.group(2)
            comment = match.group(3) or ""
            
            if explicit_value:
                current_value = int(explicit_value)
            
            entries.append((name, current_value, comment.strip()))
            current_value += 1
    
    return entries

def parse_python_class():
    """Parse Python StatusType class from types.py"""
    from ka9q.types import StatusType
    
    entries = {}
    for attr in dir(StatusType):
        if not attr.startswith('_'):
            value = getattr(StatusType, attr)
            if isinstance(value, int):
                entries[attr] = value
    
    return entries

def main():
    print("=" * 80)
    print("KA9Q-RADIO STATUS TYPE COMPARISON")
    print("=" * 80)
    print()
    
    # Parse C enum
    c_enum_path = '/Users/mjh/Sync/GitHub/ka9q-radio/src/status.h'
    c_entries = parse_c_enum(c_enum_path)
    
    # Parse Python class
    py_entries = parse_python_class()
    
    # Create lookup by value for C enum
    c_by_value = {value: (name, comment) for name, value, comment in c_entries}
    c_by_name = {name: value for name, value, comment in c_entries}
    
    # Find missing in Python
    print("MISSING IN PYTHON (present in C):")
    print("-" * 80)
    missing_count = 0
    for name, value, comment in c_entries:
        if name not in py_entries:
            print(f"  {name:30} = {value:3}  // {comment}")
            missing_count += 1
    
    if missing_count == 0:
        print("  None - all C enum values are present in Python")
    print()
    
    # Find extra in Python
    print("EXTRA IN PYTHON (not in C):")
    print("-" * 80)
    extra_count = 0
    for name, value in sorted(py_entries.items(), key=lambda x: x[1]):
        if name not in c_by_name:
            print(f"  {name:30} = {value:3}")
            extra_count += 1
    
    if extra_count == 0:
        print("  None - no extra values in Python")
    print()
    
    # Find mismatches
    print("VALUE MISMATCHES (same name, different value):")
    print("-" * 80)
    mismatch_count = 0
    for name, py_value in sorted(py_entries.items(), key=lambda x: x[1]):
        if name in c_by_name:
            c_value = c_by_name[name]
            if c_value != py_value:
                c_comment = next((comment for n, v, comment in c_entries if n == name), "")
                print(f"  {name:30} C={c_value:3}  Python={py_value:3}  // {c_comment}")
                mismatch_count += 1
    
    if mismatch_count == 0:
        print("  None - all matching names have correct values")
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY:")
    print(f"  C enum entries:        {len(c_entries)}")
    print(f"  Python class entries:  {len(py_entries)}")
    print(f"  Missing in Python:     {missing_count}")
    print(f"  Extra in Python:       {extra_count}")
    print(f"  Value mismatches:      {mismatch_count}")
    print()
    
    if missing_count > 0 or mismatch_count > 0:
        print("⚠️  ACTION REQUIRED: Python types.py needs updates")
    else:
        print("✅ Python types.py is in sync with C status.h")
    print("=" * 80)
    
    # Show the latest value in C enum
    max_c_value = max(value for name, value, comment in c_entries)
    max_c_name = next(name for name, value, comment in c_entries if value == max_c_value)
    print(f"\nLatest C enum value: {max_c_name} = {max_c_value}")
    
    return missing_count, mismatch_count

if __name__ == '__main__':
    missing, mismatches = main()
    exit(0 if (missing == 0 and mismatches == 0) else 1)
