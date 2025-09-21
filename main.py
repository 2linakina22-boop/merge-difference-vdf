import os


def read_vdf_file(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError("File not found: " + str(file_path))

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return parse_vdf_content(content, file_path)


def parse_vdf_content(content, file_name="unknown"):
    result = {}
    section_order = []
    key_order = {}
    line_comments = {}

    section_content = {}
    section_key_value_lines = {}
    section_non_key_value_lines = {}

    standalone_comments = []

    current_section = None
    current_section_lines = []

    lines = content.split('\n')
    for i, line in enumerate(lines):
        try:
            original_line = line.rstrip()
            stripped_line = line.strip()

            if stripped_line.startswith('[') and stripped_line.endswith(']'):
                if current_section is not None:
                    section_content[current_section] = current_section_lines.copy()
                    kv_lines, non_kv_lines = separate_key_value_lines(current_section_lines)
                    section_key_value_lines[current_section] = kv_lines
                    section_non_key_value_lines[current_section] = non_kv_lines

                section_name = stripped_line[1:-1].strip()
                current_section = section_name

                if section_name not in result:
                    result[section_name] = {}
                    key_order[section_name] = []
                    section_order.append(section_name)

                current_section_lines = []
                continue

            if current_section is None:
                standalone_comments.append(original_line)
            else:
                current_section_lines.append(original_line)

                if '=' in stripped_line and not stripped_line.startswith(';'):
                    line_parts = stripped_line.split(';', 1)
                    main_part = line_parts[0].strip()
                    comment_part = ';' + line_parts[1] if len(line_parts) > 1 else ''

                    parts = main_part.split('=', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        result[current_section][key] = value

                        if key not in key_order[current_section]:
                            key_order[current_section].append(key)

                        if comment_part:
                            comment_key = current_section + "." + key
                            line_comments[comment_key] = comment_part

        except Exception as e:
            raise

    if current_section is not None:
        section_content[current_section] = current_section_lines
        kv_lines, non_kv_lines = separate_key_value_lines(current_section_lines)
        section_key_value_lines[current_section] = kv_lines
        section_non_key_value_lines[current_section] = non_kv_lines

    return {
        'data': result,
        'section_order': section_order,
        'key_order': key_order,
        'line_comments': line_comments,
        'section_content': section_content,
        'section_key_value_lines': section_key_value_lines,
        'section_non_key_value_lines': section_non_key_value_lines,
        'standalone_comments': standalone_comments,
        'file_name': file_name
    }


def separate_key_value_lines(lines):
    kv_lines = []
    non_kv_lines = []
    for line in lines:
        stripped = line.strip()
        if '=' in stripped and not stripped.startswith(';'):
            kv_lines.append(line)
        else:
            non_kv_lines.append(line)
    return kv_lines, non_kv_lines


def is_key_value_line(line):
    if not line:
        return False
    stripped = line.strip()
    return '=' in stripped and not stripped.startswith(';')


def extract_key_from_line(line):
    if not line:
        return None
    stripped = line.strip()
    if '=' in stripped and not stripped.startswith(';'):
        parts = stripped.split('=', 1)
        if len(parts) >= 1:
            return parts[0].strip()
    return None


def print_vdf_section_details(vdf_parsed, vdf_name):
    pass


def generate_vdf_content(parsed_data):
    section_order = parsed_data['section_order']
    section_content = parsed_data.get('section_content', {})
    standalone_comments = parsed_data.get('standalone_comments', [])

    lines = []
    for line in standalone_comments:
        lines.append(line)

    for section in section_order:
        lines.append('[' + section + ']')
        if section in section_content:
            for content_line in section_content[section]:
                lines.append(content_line)

    return '\n'.join(lines)


def get_value_component_count(value):
    if not value:
        return 0
    components = [comp.strip() for comp in value.split(',')]
    components = [comp for comp in components if comp]
    return len(components)


def merge_values_by_count(v1_val, v2_val):
    """Use v1 value if component counts counts differ; use v2 if counts are equal"""
    if not v1_val:
        return v2_val
    if not v2_val:
        return v1_val
    v1_count = get_value_component_count(v1_val)
    v2_count = get_value_component_count(v2_val)
    return v1_val if v1_count != v2_count else v2_val


def merge_vdf_data(vdf1_parsed, vdf2_parsed):
    try:
        v1_data = vdf1_parsed['data']
        v2_data = vdf2_parsed['data']
        v1_comments = vdf1_parsed.get('line_comments', {})
        v2_comments = vdf2_parsed.get('line_comments', {})

        v1_content = vdf1_parsed.get('section_content', {})
        v2_content = vdf2_parsed.get('section_content', {})

        # Get all sections from both VDF files
        v1_sections = set(vdf1_parsed['section_order'])
        v2_sections = set(vdf2_parsed['section_order'])

        # Determine merged section order, using v1's order as base
        merged_section_order = []
        # First add sections present in v1
        for section in vdf1_parsed['section_order']:
            merged_section_order.append(section)

        # Add v2 unique sections in appropriate position
        v2_unique_sections = v2_sections - v1_sections
        for section in v2_unique_sections:
            # Find insertion position based on alphabetical order
            insert_pos = len(merged_section_order)
            for i, v1_section in enumerate(vdf1_parsed['section_order']):
                if section < v1_section:
                    insert_pos = i
                    break
            merged_section_order.insert(insert_pos, section)

        merged_data = {}
        merged_key_order = {}
        merged_line_comments = {}
        merged_section_content = {}

        merged_standalone_comments = vdf2_parsed.get('standalone_comments', []).copy()

        # Process all sections
        for section in merged_section_order:
            merged_data[section] = {}
            merged_key_order[section] = []
            merged_section_content[section] = []

            v1_has_section = section in v1_content
            v2_has_section = section in v2_content

            # Create mapping of v2 key-value lines
            v2_kv_map = {}
            if v2_has_section:
                for line in v2_content[section]:
                    if is_key_value_line(line):
                        key = extract_key_from_line(line)
                        if key:
                            v2_kv_map[key] = line

            # Build content following v1's line order, preserving non-key-value lines
            if v1_has_section:
                for line in v1_content[section]:
                    if is_key_value_line(line):
                        key = extract_key_from_line(line)
                        if key:
                            if key in v2_kv_map:
                                # Same key, apply value comparison strategy
                                v1_val = v1_data[section][key]
                                v2_val = v2_data[section][key]
                                final_val = merge_values_by_count(v1_val, v2_val)

                                comment_key = section + "." + key
                                final_comment = v1_comments.get(comment_key, v2_comments.get(comment_key, ''))
                                merged_line = key + " = " + final_val + final_comment

                                merged_section_content[section].append(merged_line)
                                merged_data[section][key] = final_val
                                merged_key_order[section].append(key)
                                merged_line_comments[comment_key] = final_comment

                                # Remove processed key from v2 mapping
                                del v2_kv_map[key]
                            else:
                                # Key unique to v1, keep as is
                                merged_section_content[section].append(line)
                                merged_data[section][key] = v1_data[section][key]
                                merged_key_order[section].append(key)
                                cmt_key = section + "." + key
                                if cmt_key in v1_comments:
                                    merged_line_comments[cmt_key] = v1_comments[cmt_key]
                    else:
                        # Keep non-key-value lines as is
                        merged_section_content[section].append(line)

            # Add key-value lines unique to v2 (not present in v1)
            if v2_has_section:
                for key, line in v2_kv_map.items():
                    if key not in merged_data[section]:
                        merged_section_content[section].append(line)
                        merged_data[section][key] = v2_data[section][key]
                        merged_key_order[section].append(key)
                        comment_key = section + "." + key
                        merged_line_comments[comment_key] = v2_comments.get(comment_key, '')

        # Separate key-value lines and non-key-value lines (for compatibility)
        merged_kv_lines = {}
        merged_non_kv_lines = {}
        for section in merged_section_order:
            kv, non_kv = separate_key_value_lines(merged_section_content[section])
            merged_kv_lines[section] = kv
            merged_non_kv_lines[section] = non_kv

        return {
            'data': merged_data,
            'section_order': merged_section_order,
            'key_order': merged_key_order,
            'line_comments': merged_line_comments,
            'section_content': merged_section_content,
            'section_key_value_lines': merged_kv_lines,
            'section_non_key_value_lines': merged_non_kv_lines,
            'standalone_comments': merged_standalone_comments
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise


def save_vdf_file(parsed_data, output_path):
    content = generate_vdf_content(parsed_data)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)


def print_key_value_counts(vdf_parsed, vdf_name):
    """Print the count of value components for each key"""
    pass


def main():
    vdf1_path = "config1.vdf"
    vdf2_path = "config2.vdf"
    output_path = "merged_config.vdf"

    try:
        vdf1_parsed = read_vdf_file(vdf1_path)
        vdf2_parsed = read_vdf_file(vdf2_path)

        print_vdf_section_details(vdf1_parsed, "vdf1")
        print_vdf_section_details(vdf2_parsed, "vdf2")

        # Print value component counts for each key
        print_key_value_counts(vdf1_parsed, "vdf1")
        print_key_value_counts(vdf2_parsed, "vdf2")

        merged_parsed = merge_vdf_data(vdf1_parsed, vdf2_parsed)

        print_vdf_section_details(merged_parsed, "Merged VDF")
        save_vdf_file(merged_parsed, output_path)

    except FileNotFoundError as e:
        pass
    except Exception as e:
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
