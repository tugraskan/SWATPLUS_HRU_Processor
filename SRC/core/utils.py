# core/utils.py

def parse_filter_ids(filter_input):
    """
    Parses a string of HRU IDs and ranges, returning a sorted list of unique IDs.
    Accepts single IDs or ranges in the format "1,3,5-8,10".

    Parameters:
    filter_input (str): A comma-separated string of IDs or ranges.

    Returns:
    list of int: A sorted list of unique HRU IDs.

    Raises:
    ValueError: If the input format is invalid.
    """
    ids = set()  # Use a set to avoid duplicate IDs
    ranges = filter_input.split(',')
    
    for part in ranges:
        part = part.strip()
        if '-' in part:
            # Handle ranges (e.g., "5-8")
            try:
                start, end = map(int, part.split('-'))
                if start > end:
                    raise ValueError(f"Invalid range '{part}': start should be <= end.")
                ids.update(range(start, end + 1))
            except ValueError:
                raise ValueError(f"Invalid range format: '{part}'")
        else:
            # Handle single IDs (e.g., "3")
            try:
                ids.add(int(part))
            except ValueError:
                raise ValueError(f"Invalid ID format: '{part}'")

    return sorted(ids)

