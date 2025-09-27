import re

def flatten_hierarchy(content, sep='\n'):
    result = []
    
    def process_node(node):
        if isinstance(node, str):
            if node.strip():
                result.append(node.strip())
            return
            
        if isinstance(node, list):
            for item in node:
                process_node(item)
            return
            
        if isinstance(node, dict):
            if node.get('text') and not node.get('content'):
                result.append(node['text'].strip())
            
            if node.get('content'):
                process_node(node['content'])
            
            for key, value in node.items():
                if key not in ('type', 'text', 'content'):
                    process_node(value)
    
    process_node(content)
    return sep.join(result)

class JSONTransformer:
    def __init__(self, mapping_dict):
        """Initialize transformer with mapping dictionary."""
        self.mapping_dict = mapping_dict
        self.id_to_text = {}
        self.used_matches = set()

    def _find_refs(self, data, search_key):
        """Find all references based on search key in the data."""
        matches = []
        
        if isinstance(data, dict):
            if search_key in data:
                matches.append(data)
            for value in data.values():
                matches.extend(self._find_refs(value, search_key))
        elif isinstance(data, list):
            for item in data:
                matches.extend(self._find_refs(item, search_key))
                
        return matches

    def _extract_ref_ids(self, ref_data, search_id):
        """Extract reference IDs from either dict or list data."""
        if isinstance(ref_data, dict):
            ref_id = ref_data.get(search_id)
            return [ref_id] if ref_id is not None else []
        elif isinstance(ref_data, list):
            ids = []
            for item in ref_data:
                if isinstance(item, dict):
                    ref_id = item.get(search_id)
                    if ref_id is not None:
                        ids.append(ref_id)
            return ids
        return []

    def _find_content(self, data, match_identifier, match_content):
        """Find all content entries in the data that match the identifier and content pattern."""
        matches = []
        
        if isinstance(data, dict):
            if match_identifier in data and match_content in data:
                matches.append(data)
            for value in data.values():
                matches.extend(self._find_content(value, match_identifier, match_content))
        elif isinstance(data, list):
            for item in data:
                matches.extend(self._find_content(item, match_identifier, match_content))
                
        return matches

    def _build_mapping(self, data, transformation):
        """Build mapping between identifiers and their content."""
        match_rule = transformation['match']
        id_key = match_rule['identifier']
        content_key = match_rule['content']
        
        content_matches = self._find_content(data, id_key, content_key)
        
        for match in content_matches:
            if id_key in match and content_key in match:
                self.id_to_text[match[id_key]] = match[content_key]
                if match_rule.get('remove_after_use', False):
                    self.used_matches.add(match[id_key])

    def _remove_used_content(self, data, match_rule):
        """Remove the used content entries based on match rule."""
        if isinstance(data, dict):
            id_key = match_rule['identifier']
            
            if id_key in data and data.get(id_key) in self.used_matches:
                return None
                
            result = {}
            for k, v in data.items():
                processed = self._remove_used_content(v, match_rule)
                if processed is not None:
                    result[k] = processed
            
            return result if result else None
            
        elif isinstance(data, list):
            result = [item for item in data 
                     if (processed := self._remove_used_content(item, match_rule)) is not None]
            return result if result else None
            
        return data

    def _apply_standardization(self, data, transformation):
        """Apply standardization rules to transform text based on regex pattern."""
        if isinstance(data, dict):
            if data.get('type') == transformation['match']['type'] and 'text' in data:
                pattern = transformation['match']['text_pattern']
                match = re.match(pattern, data['text'])
                if match:
                    value = match.group(1)
                    output_field = transformation['output'].get('field', 'text')
                    data[output_field] = transformation['output']['format'].format(value.lower())
                    
            for value in data.values():
                if isinstance(value, (dict, list)):
                    self._apply_standardization(value, transformation)
                    
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    self._apply_standardization(item, transformation)

    def _apply_trim(self, data, transformation):
        if not isinstance(data, dict) or 'content' not in data:
            return data

        match_type = transformation['match']['type']
        expected = transformation['match'].get('expected')
        output_type = transformation['output']['type']
        
        matches = []
        def find_matches(content, current_path=[]):
            for i, item in enumerate(content):
                if isinstance(item, dict):
                    if item.get('type') == match_type and 'text' in item:
                        matches.append({
                            'path': current_path + [i],
                            'text': item['text']
                        })
                    if 'content' in item:
                        find_matches(item['content'], current_path + [i, 'content'])
        
        find_matches(data['content'])
        if not matches:
            return data
                
        text_groups = {}
        for match in matches:
            text = match['text']
            if text not in text_groups:
                text_groups[text] = []
            text_groups[text].append(match['path'])
        
        result = {'type': output_type}
        for text, paths in text_groups.items():
            if len(paths) > expected:
                if expected == 0:
                    result['content'] = [flatten_hierarchy(data['content'])]
                    data['content'] = [result]
                else:
                    split_path = paths[expected]
                    split_idx = split_path[0]
                    before_content = data['content'][:split_idx]
                    result['content'] = [flatten_hierarchy(before_content)]
                    data['content'] = data['content'][split_idx:]
                    data['content'].insert(0, result)
                break

        return data

    def _apply_consecutive_merge(self, data, transformation):
        """Merge consecutive sections with same type and text."""
        if isinstance(data, dict):
            if 'content' in data and isinstance(data['content'], list):
                new_content = []
                current_section = None
                
                for item in data['content']:
                    if (isinstance(item, dict) and 
                        item.get('type') in transformation['match']['types'] and 
                        'text' in item):
                        if (current_section and 
                            current_section['type'] == item['type'] and 
                            current_section['text'] == item['text']):
                            current_section['content'].extend(item['content'])
                        else:
                            if current_section:
                                new_content.append(current_section)
                            current_section = item
                    else:
                        if current_section:
                            new_content.append(current_section)
                            current_section = None
                        new_content.append(item)
                        
                if current_section:
                    new_content.append(current_section)
                    
                data['content'] = new_content
                
            for value in data.values():
                if isinstance(value, (dict, list)):
                    self._apply_consecutive_merge(value, transformation)
                    
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    self._apply_consecutive_merge(item, transformation)

    def transform(self, data):
        """Transform the data according to the mapping dictionary."""
        result = data.copy()
        
        for transformation in self.mapping_dict['transformations']:
            if transformation.get('type') == 'standardize':
                self._apply_standardization(result, transformation)
            elif transformation.get('type') == 'merge_consecutive':
                self._apply_consecutive_merge(result, transformation)
            elif transformation.get('type') == 'trim':
                self._apply_trim(result, transformation)
            else:
                # Reference replacement logic
                self._build_mapping(result, transformation)
                
                search_key = transformation['search']['key']
                search_id = transformation['search']['identifier']
                output_key = transformation['output']['key']
                
                refs = self._find_refs(result, search_key)
                
                for ref in refs:
                    ref_ids = self._extract_ref_ids(ref[search_key], search_id)
                    if ref_ids:
                        # Create a list of referenced content
                        referenced_content = [
                            self.id_to_text[ref_id]
                            for ref_id in ref_ids
                            if ref_id in self.id_to_text
                        ]
                        if referenced_content:
                            ref[output_key] = referenced_content
                            del ref[search_key]
                
                if transformation['match'].get('remove_after_use', False):
                    result = self._remove_used_content(result, transformation['match'])
        
        return result

class RuleProcessor:
    def __init__(self, rules_dict):
        self.rules = rules_dict
        
    def _apply_remove_rules(self, lines):
        if 'remove' not in self.rules:
            return lines
            
        result = lines.copy()
        for rule in self.rules['remove']:
            pattern = rule['pattern']
            result = [line for line in result if not re.match(pattern, line)]
                
        return result
     
    def _join_consecutive_strings(self, content_list):
        """Join consecutive strings in a content list."""
        if not content_list:
            return content_list
            
        result = []
        current_strings = []
        
        for item in content_list:
            if isinstance(item, str):
                current_strings.append(item)
            else:
                if current_strings:
                    result.append(self.rules.get('join_text').join(current_strings))
                    current_strings = []
                if isinstance(item, dict) and 'content' in item:
                    item['content'] = self._join_consecutive_strings(item['content'])
                result.append(item)
        
        if current_strings:
            result.append(self.rules.get('join_text').join(current_strings))
            
        return result
        
    def _find_matching_end(self, lines, start_idx, end_pattern):
        """Find matching end pattern considering nesting."""
        pattern_name = None
        nesting_level = 1
        
        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            
            if pattern_name and re.match(pattern_name, line):
                nesting_level += 1
            elif re.match(end_pattern, line):
                nesting_level -= 1
                if nesting_level == 0:
                    return i
                    
        return len(lines) - 1
        
    def _process_block(self, lines, start_idx, rule, mappings):
        """Process a block of content, handling nested blocks."""
        content = []
        current_idx = start_idx + 1
        end_idx = None
        
        if rule.get('end'):
            end_idx = self._find_matching_end(lines, start_idx, rule['end'])
        else:
            for i in range(start_idx + 1, len(lines)):
                if any(re.match(r['pattern'], lines[i]) 
                      for r in mappings if r.get('hierarchy') is not None):
                    end_idx = i - 1
                    break
            if end_idx is None:
                end_idx = len(lines) - 1
                
        while current_idx < end_idx:
            line = lines[current_idx]
            matched = False
            
            for nested_rule in mappings:
                if re.match(nested_rule['pattern'], line):
                    nested_content, next_idx = self._process_block(
                        lines, current_idx, nested_rule, mappings
                    )
                    if nested_content:
                        content.append(nested_content)
                    current_idx = next_idx + 1
                    matched = True
                    break
                    
            if not matched:
                content.append(line)
                current_idx += 1
                
        if rule.get('keep_end', False) and end_idx < len(lines):
            content.append(lines[end_idx])
                
        return {
            'type': rule['name'],
            'content': content
        }, end_idx
        
    def _apply_mapping_rules(self, lines):
        if 'mappings' not in self.rules:
            return {'content': lines}
            
        result = {'content': []}
        hierarchy_stack = [result]
        
        mappings = sorted(
            self.rules['mappings'],
            key=lambda x: x.get('hierarchy', float('inf'))
        )
        
        i = 0
        while i < len(lines):
            line = lines[i]
            matched = False
            
            for rule in mappings:
                if re.match(rule['pattern'], line):
                    if rule.get('hierarchy') is not None:
                        new_section = {
                            'type': rule['name'],
                            'text': line,
                            'content': []
                        }
                        
                        while len(hierarchy_stack) > rule['hierarchy'] + 1:
                            hierarchy_stack.pop()
                            
                        parent = hierarchy_stack[-1]
                        if isinstance(parent.get('content'), list):
                            parent['content'].append(new_section)
                        
                        hierarchy_stack.append(new_section)
                        i += 1
                        
                    else:
                        block, end_idx = self._process_block(lines, i, rule, mappings)
                        parent = hierarchy_stack[-1]
                        if isinstance(parent.get('content'), list):
                            parent['content'].append(block)
                        i = end_idx + 1
                        
                    matched = True
                    break
                    
            if not matched:
                parent = hierarchy_stack[-1]
                if isinstance(parent.get('content'), list):
                    parent['content'].append(line)
                i += 1
                
        if self.rules.get('join_text') is not None:
            result['content'] = self._join_consecutive_strings(result['content'])
                
        return result

class DocumentProcessor:
    def __init__(self, config):
        self.rules = config.get('rules', {})
        self.transformations = config.get('transformations', [])
        self.rule_processor = RuleProcessor(self.rules)
        self.json_transformer = JSONTransformer({'transformations': self.transformations}) if self.transformations else None
        
    def process(self, lines):
        filtered_lines = self.rule_processor._apply_remove_rules(lines)
        structured_data = self.rule_processor._apply_mapping_rules(filtered_lines)
        
        if self.json_transformer:
            structured_data = self.json_transformer.transform(structured_data)
            
        return structured_data