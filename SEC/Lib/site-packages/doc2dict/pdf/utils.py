
# TODO, modify for e.g. BOLD AND ITALIC or IT etc name variations
def get_font_attributes(font_name):
    dct = {}
    attribute = font_name.split('-')
    if len(attribute) > 1:
        key = attribute[-1].lower()
        dct[key] = True
    return dct

def get_font_size(coords_tuple):
    left = coords_tuple[0]
    bottom = coords_tuple[1]
    right = coords_tuple[2]
    top = coords_tuple[3]
    height = top - bottom
    font_size = height / 2
    return font_size * 4 # Multiplying just because why not?

# TODO REMOVE. we do need to find how to get actual font size
def standardize_font_size(instructions_stream):
    """
    Standardize font sizes in the instructions stream by merging font sizes that are close to each other.
    
    Args:
        instructions_stream (list): List of dictionaries containing text elements with font-size information
        
    Returns:
        list: The instructions stream with standardized font sizes
    """
    if not instructions_stream:
        return []
    
    # First, extract all unique font sizes
    font_sizes = []
    for item in instructions_stream:
        if 'font-size' in item:
            font_sizes.append(item['font-size'])
    
    # If no font sizes found, return original stream
    if not font_sizes:
        return instructions_stream
    
    # Sort font sizes
    font_sizes = sorted(set(font_sizes))
    
    # Group similar font sizes
    standardized_sizes = []
    current_group = [font_sizes[0]]
    
    for i in range(1, len(font_sizes)):
        # Calculate relative difference between consecutive font sizes
        current_size = font_sizes[i]
        prev_size = font_sizes[i-1]
        relative_diff = abs(current_size - prev_size) / max(current_size, prev_size)
        
        # If the difference is less than a threshold (e.g., 5%), group them
        if relative_diff < 0.05:
            current_group.append(current_size)
        else:
            # Calculate average for the current group
            avg_size = sum(current_group) / len(current_group)
            standardized_sizes.append((current_group, avg_size))
            current_group = [current_size]
    
    # Add the last group
    if current_group:
        avg_size = sum(current_group) / len(current_group)
        standardized_sizes.append((current_group, avg_size))
    
    # Create a mapping from original sizes to standardized sizes
    size_mapping = {}
    for group, avg_size in standardized_sizes:
        for size in group:
            size_mapping[size] = avg_size
    
    # Apply the mapping to the instructions stream
    for item in instructions_stream:
        if 'font-size' in item and item['font-size'] in size_mapping:
            item['font-size'] = size_mapping[item['font-size']]
    
    return instructions_stream

def assign_line(instructions_stream):
    """
    Assign line numbers to text elements that are positioned on the same line.
    Only compares with the next neighbor in the list.
    """
    
    # Initialize with first element
    current_line = 0
    instructions_list = []
    instructions = [instructions_stream[0]]
    
    # Process remaining elements
    for i in range(len(instructions_stream) - 1):
        current = instructions_stream[i]
        next_item = instructions_stream[i + 1]
        
        # Extract y-coordinates (bottom of text)
        current_y = current['coords'][1]  # bottom y of current
        next_y = next_item['coords'][1]   # bottom y of next
        
        # Get font sizes for tolerance calculation
        current_font_size = current['font-size']
        next_font_size = next_item['font-size']
        
        # Calculate tolerance based on larger font size
        tolerance = max(current_font_size, next_font_size) * 0.5
        
        # Check if next item is on the same line
        if abs(current_y - next_y) <= tolerance:
            # if font-name and font-size are the same, then we can merge them. We can do this, because font name contains bold/italic
            if current['font-name'] == next_item['font-name'] and current['font-size'] == next_item['font-size']:
                # Merge the two items
                current['text'] += next_item['text']
                current['coords'] = (
                    min(current['coords'][0], next_item['coords'][0]),  # left
                    min(current['coords'][1], next_item['coords'][1]),  # bottom
                    max(current['coords'][2], next_item['coords'][2]),  # right
                    max(current['coords'][3], next_item['coords'][3])   # top
                )
            else:
                instructions.append(next_item)
        else:
            instructions_list.append(instructions)
            instructions = [next_item]
    
    return instructions_list

# so these need to be modified to look at all the dicts.
def get_left_indent(coords_tuple):
    return

def get_is_centered(coords_tuple):
    return