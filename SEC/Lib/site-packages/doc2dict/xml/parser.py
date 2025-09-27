import xmltodict
from ..mapping import JSONTransformer

def remove_namespace_and_none(path, key, value):
    # Skip this key-value pair if value is None
    if value is None:
        return None  # Return None to exclude this key-value pair
    
    # Remove xmlns attribute altogether
    if key == '@xmlns':
        return None
    
    # Remove namespace from keys
    if ':' in key:
        # Keep only the part after the last colon
        return key.split(':')[-1], value
    
    return key, value

def xml2dict(content, mapping_dict=None):
    data = xmltodict.parse(
        content,
        postprocessor=remove_namespace_and_none,
        process_namespaces=True,  # Handle namespaces
        namespaces={}
    )

    if mapping_dict is None:
        return data
    
    transformer = JSONTransformer(mapping_dict)
    transformed_data = transformer.transform(data)
    return transformed_data