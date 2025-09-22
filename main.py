import os
import shutil

def read_vdf_file(file_path):
    if not os.path.exists(file_path):
        raise IOError("File not found: " + str(file_path))

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return parse_vdf_content(content, file_path)


def parse_vdf_content(content, file_name="unknown"):
    result = {}
    section_order = []
    key_order = {}
    line_comments = {}
    original_key_value_lines = {}
    key_value_spacing = {}
    comment_spacing = {}

    section_content = {}
    section_key_value_lines = {}
    section_non_key_value_lines = {}

    standalone_comments = []

    current_section = None
    current_section_lines = []

    lines = content.split('\n')
    for i, line in enumerate(lines):
        try:
            original_line = line.rstrip('\r\n')
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
                    original_key_value_lines[section_name] = {}
                    line_comments[section_name] = {}
                    key_value_spacing[section_name] = {}
                    comment_spacing[section_name] = {}

                current_section_lines = [original_line]
                continue

            if current_section is None:
                standalone_comments.append(original_line)
            else:
                current_section_lines.append(original_line)

                if '=' in line and not stripped_line.startswith(';'):
                    key = extract_key_from_line(line)
                    if key:
                        value = extract_value_from_line(line)
                        comment = extract_comment_from_line(line)
                        spacing_info = extract_spacing_info(line)
                        comment_space_info = extract_comment_spacing_info(line)

                        result[current_section][key] = value

                        if key not in key_order[current_section]:
                            key_order[current_section].append(key)

                        original_key_value_lines[current_section][key] = original_line
                        line_comments[current_section][key] = comment
                        key_value_spacing[current_section][key] = spacing_info
                        comment_spacing[current_section][key] = comment_space_info

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
        'original_key_value_lines': original_key_value_lines,
        'key_value_spacing': key_value_spacing,
        'comment_spacing': comment_spacing,
        'file_name': file_name
    }


def separate_key_value_lines(lines):
    kv_lines = []
    non_kv_lines = []
    for line in lines:
        stripped = line.strip()
        if '=' in line and not stripped.startswith(';'):
            kv_lines.append(line)
        else:
            non_kv_lines.append(line)
    return kv_lines, non_kv_lines


def is_key_value_line(line):
    if not line:
        return False
    stripped = line.strip()
    return '=' in line and not stripped.startswith(';')


def extract_key_from_line(line):
    if not line or '=' not in line:
        return None
    if ';' in line:
        main_part = line.split(';', 1)[0]
    else:
        main_part = line
    if '=' in main_part:
        key_part = main_part.split('=', 1)[0]
        return key_part.strip()
    return None


def extract_value_from_line(line):
    if not line or '=' not in line:
        return None
    if ';' in line:
        main_part = line.split(';', 1)[0]
    else:
        main_part = line
    if '=' in main_part:
        value_part = main_part.split('=', 1)[1]
        return value_part.strip()
    return None


def extract_comment_from_line(line):
    if ';' in line:
        comment_part = line.split(';', 1)[1]
        return comment_part
    return ''


def extract_spacing_info(line):
    if ';' in line:
        main_part = line.split(';', 1)[0]
    else:
        main_part = line
    if '=' in main_part:
        key_part, value_part = main_part.split('=', 1)
        before_equals_spaces = len(key_part) - len(key_part.rstrip())
        after_equals_spaces = len(value_part) - len(value_part.lstrip())
        return {
            'before_equals': before_equals_spaces,
            'after_equals': after_equals_spaces
        }
    return {'before_equals': 1, 'after_equals': 1}


def extract_comment_spacing_info(line):
    if ';' not in line:
        return {'before_comment': 0, 'after_semicolon': 0}
    main_part, comment_part = line.split(';', 1)
    before_comment_spaces = len(main_part) - len(main_part.rstrip())
    after_semicolon_spaces = len(comment_part) - len(comment_part.lstrip())
    return {
        'before_comment': before_comment_spaces,
        'after_semicolon': after_semicolon_spaces
    }


def create_merged_line_with_vdf2_spacing(key, value, v2_spacing_info, v2_comment_spacing_info, use_comment=None):
    before_equals_spaces = ' ' * v2_spacing_info.get('before_equals', 1)
    after_equals_spaces = ' ' * v2_spacing_info.get('after_equals', 1)
    before_comment_spaces = ' ' * v2_comment_spacing_info.get('before_comment', 0)
    after_semicolon_spaces = ' ' * v2_comment_spacing_info.get('after_semicolon', 1)

    main_part = key + before_equals_spaces + '=' + after_equals_spaces + value

    if use_comment:
        clean_comment = use_comment.strip()
        if clean_comment.startswith(';'):
            clean_comment = clean_comment[1:].strip()
        if clean_comment:
            comment_part = before_comment_spaces + ';' + after_semicolon_spaces + clean_comment
            return main_part + comment_part
        else:
            if v2_comment_spacing_info.get('before_comment', 0) > 0:
                return main_part + ' ' * v2_comment_spacing_info['before_comment'] + ';'
            else:
                return main_part
    else:
        return main_part


def create_merged_line_with_vdf1_comment_spacing(key, value, v2_spacing_info, v1_comment_spacing_info, use_comment=None):
    before_equals_spaces = ' ' * v2_spacing_info.get('before_equals', 1)
    after_equals_spaces = ' ' * v2_spacing_info.get('after_equals', 1)
    before_comment_spaces = ' ' * v1_comment_spacing_info.get('before_comment', 0)
    after_semicolon_spaces = ' ' * v1_comment_spacing_info.get('after_semicolon', 1)

    main_part = key + before_equals_spaces + '=' + after_equals_spaces + value

    if use_comment:
        clean_comment = use_comment.strip()
        if clean_comment.startswith(';'):
            clean_comment = clean_comment[1:].strip()
        if clean_comment:
            comment_part = before_comment_spaces + ';' + after_semicolon_spaces + clean_comment
            return main_part + comment_part
        else:
            if v1_comment_spacing_info.get('before_comment', 0) > 0:
                return main_part + ' ' * v1_comment_spacing_info['before_comment'] + ';'
            else:
                return main_part
    else:
        return main_part


def generate_vdf_content(parsed_data):
    section_order = parsed_data['section_order']
    section_content = parsed_data.get('section_content', {})
    standalone_comments = parsed_data.get('standalone_comments', [])

    lines = []
    for line in standalone_comments:
        lines.append(line)

    for section in section_order:
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
        v1_original = vdf1_parsed.get('original_key_value_lines', {})
        v2_original = vdf2_parsed.get('original_key_value_lines', {})
        v1_spacing = vdf1_parsed.get('key_value_spacing', {})
        v2_spacing = vdf2_parsed.get('key_value_spacing', {})
        v1_comment_spacing = vdf1_parsed.get('comment_spacing', {})
        v2_comment_spacing = vdf2_parsed.get('comment_spacing', {})

        v1_content = vdf1_parsed.get('section_content', {})
        v2_content = vdf2_parsed.get('section_content', {})

        v1_section_order = vdf1_parsed.get('section_order', [])

        merged_data = {}
        merged_key_order = {}
        merged_section_content = {}
        merged_original_lines = {}

        merged_section_order = [section for section in v1_section_order]
        merged_standalone_comments = vdf1_parsed.get('standalone_comments', [])

        for section in merged_section_order:
            merged_data[section] = {}
            merged_key_order[section] = []
            merged_section_content[section] = []
            merged_original_lines[section] = {}

            v1_has_section = section in v1_content
            v2_has_section = section in v2_content

            if v1_has_section:
                for line in v1_content[section]:
                    if is_key_value_line(line):
                        key = extract_key_from_line(line)
                        if key:
                            v1_val = v1_data[section][key]
                            v1_original_line = v1_original.get(section, {}).get(key, line)
                            v1_comment = v1_comments.get(section, {}).get(key, '')
                            v1_comment_spacing_info = v1_comment_spacing.get(section, {}).get(key, {'before_comment': 0,
                                                                                                    'after_semicolon': 1})

                            if v2_has_section and key in v2_data[section]:
                                v2_val = v2_data[section][key]
                                v2_comment = v2_comments.get(section, {}).get(key, '')
                                v2_spacing_info = v2_spacing.get(section, {}).get(key, {'before_equals': 1,
                                                                                        'after_equals': 1})
                                v2_comment_spacing_info = v2_comment_spacing.get(section, {}).get(key,
                                                                                                  {'before_comment': 0,
                                                                                                   'after_semicolon': 1})

                                final_val = merge_values_by_count(v1_val, v2_val)

                                if v1_comment.strip() != v2_comment.strip():
                                    final_comment = v1_comment
                                    merged_line = create_merged_line_with_vdf1_comment_spacing(
                                        key, final_val, v2_spacing_info, v1_comment_spacing_info, final_comment)
                                else:
                                    final_comment = v2_comment
                                    merged_line = create_merged_line_with_vdf2_spacing(
                                        key, final_val, v2_spacing_info, v2_comment_spacing_info, final_comment)

                                merged_section_content[section].append(merged_line)
                                merged_data[section][key] = final_val
                                merged_key_order[section].append(key)
                                merged_original_lines[section][key] = merged_line
                            else:
                                merged_section_content[section].append(v1_original_line)
                                merged_data[section][key] = v1_val
                                merged_key_order[section].append(key)
                                merged_original_lines[section][key] = v1_original_line
                    else:
                        merged_section_content[section].append(line)

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
            'section_content': merged_section_content,
            'section_key_value_lines': merged_kv_lines,
            'section_non_key_value_lines': merged_non_kv_lines,
            'standalone_comments': merged_standalone_comments,
            'original_key_value_lines': merged_original_lines
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise


def save_vdf_file(parsed_data, output_path):
    content = generate_vdf_content(parsed_data)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)


def merge_vdf_folders(folder1, folder2, output_folder):
    if not os.path.isdir(folder1):
        raise IOError("Folder not found: " + folder1)
    if not os.path.isdir(folder2):
        raise IOError("Folder not found: " + folder2)

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    files1 = {f.lower(): os.path.join(folder1, f) for f in os.listdir(folder1) if f.lower().endswith('.vdf')}
    files2 = {f.lower(): os.path.join(folder2, f) for f in os.listdir(folder2) if f.lower().endswith('.vdf')}

    common_files = set(files1.keys()) & set(files2.keys())

    for fname_lower in sorted(common_files):
        f1_path = files1[fname_lower]
        f2_path = files2[fname_lower]

        vdf1_parsed = read_vdf_file(f1_path)
        vdf2_parsed = read_vdf_file(f2_path)

        merged_parsed = merge_vdf_data(vdf1_parsed, vdf2_parsed)

        output_path = os.path.join(output_folder, fname_lower)
        save_vdf_file(merged_parsed, output_path)


def main():
    folder1 = "1"
    folder2 = "2"
    output_folder = "3"

    try:
        merge_vdf_folders(folder1, folder2, output_folder)
    except Exception as e:
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()