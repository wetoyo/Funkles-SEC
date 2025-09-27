def dict2dict(data):
    result = {}
    
    def process_item(item):
        # If item is a string, return it directly
        if isinstance(item, str):
            return item.strip()
            
        # If item is not a dict, return string version
        if not isinstance(item, dict):
            return str(item).strip()
            
        # Base case: if there's no further content, return the item itself
        if 'content' not in item:
            return item
        
        # If there's a text key, use it as the dict key, otherwise use the type
        key = item.get('text', item.get('type', ''))
        
        # Process the content
        if isinstance(item['content'], list):
            # Check if content contains dictionaries with type/text
            if any(isinstance(x, dict) and ('type' in x or 'text' in x) for x in item['content']):
                nested_result = {}
                for content_item in item['content']:
                    if isinstance(content_item, dict):
                        nested_key = content_item.get('text', content_item.get('type', ''))
                        nested_result[nested_key] = process_item(content_item)
                return nested_result
            # If content items are simple values (strings/numbers), join with newlines and strip
            else:
                return '\n'.join(str(x) for x in item['content']).strip()
        else:
            return str(item['content']).strip()

    # Handle case where data itself might be a string
    if isinstance(data, str):
        return data.strip()
        
    # Handle case where content is a list directly
    if isinstance(data.get('content', []), list):
        for item in data['content']:
            if isinstance(item, dict):
                key = item.get('text', item.get('type', ''))
                result[key] = process_item(item)
            else:
                # If we have a string in content, use it as both key and value
                result[str(item).strip()] = str(item).strip()
                
    return result