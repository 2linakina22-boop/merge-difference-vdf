import os
import glob


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
    original_key_value_lines = {}  # 存储每个键的完整原始行（包括注释）
    key_value_spacing = {}  # 存储每个键值对等号前后的空格信息
    comment_spacing = {}  # 存储数值与分号之间的空格信息

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
                    # 解析键值对，完全保持原有的格式
                    key = extract_key_from_line(line)
                    if key:
                        value = extract_value_from_line(line)
                        comment = extract_comment_from_line(line)
                        spacing_info = extract_spacing_info(line)
                        comment_space_info = extract_comment_spacing_info(line)

                        result[current_section][key] = value

                        if key not in key_order[current_section]:
                            key_order[current_section].append(key)

                        # 存储完整的原始行（包括所有空格和注释）
                        original_key_value_lines[current_section][key] = original_line
                        # 存储注释
                        line_comments[current_section][key] = comment
                        # 存储等号前后的空格信息
                        key_value_spacing[current_section][key] = spacing_info
                        # 存储注释前的空格信息
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
        'original_key_value_lines': original_key_value_lines,  # 存储完整的原始行
        'key_value_spacing': key_value_spacing,  # 存储等号前后的空格信息
        'comment_spacing': comment_spacing,  # 存储注释前的空格信息
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


def is_section_line(line):
    """判断是否为章节行"""
    stripped = line.strip()
    return stripped.startswith('[') and stripped.endswith(']')


def extract_section_name(line):
    """提取章节名"""
    stripped = line.strip()
    if stripped.startswith('[') and stripped.endswith(']'):
        return stripped[1:-1].strip()
    return None


def extract_key_from_line(line):
    """提取键名，不改变原始格式"""
    if not line or '=' not in line:
        return None

    # 分离注释部分
    if ';' in line:
        main_part = line.split(';', 1)[0]
    else:
        main_part = line

    if '=' in main_part:
        key_part = main_part.split('=', 1)[0]
        return key_part.strip()
    return None


def extract_value_from_line(line):
    """提取值，不改变原始格式"""
    if not line or '=' not in line:
        return None

    # 分离注释部分
    if ';' in line:
        main_part = line.split(';', 1)[0]
    else:
        main_part = line

    if '=' in main_part:
        value_part = main_part.split('=', 1)[1]
        return value_part.strip()
    return None


def extract_comment_from_line(line):
    """提取注释内容（不含分号）"""
    if ';' in line:
        comment_part = line.split(';', 1)[1]
        # 返回注释内容（不含分号，但保留注释内容前后的空格）
        return comment_part
    return ''


def extract_spacing_info(line):
    """提取等号前后的空格信息"""
    if ';' in line:
        main_part = line.split(';', 1)[0]
    else:
        main_part = line

    if '=' in main_part:
        key_part, value_part = main_part.split('=', 1)

        # 计算等号前的空格（键和等号之间）
        before_equals_spaces = len(key_part) - len(key_part.rstrip())

        # 计算等号后的空格（等号和值之间）
        after_equals_spaces = len(value_part) - len(value_part.lstrip())

        return {
            'before_equals': before_equals_spaces,
            'after_equals': after_equals_spaces
        }
    return {'before_equals': 1, 'after_equals': 1}  # 默认值


def extract_comment_spacing_info(line):
    """提取数值与分号之间以及分号前后的空格信息"""
    if ';' not in line:
        return {'before_comment': 0, 'after_semicolon': 0}

    # 分离主部分和注释部分
    main_part, comment_part = line.split(';', 1)

    # 计算数值与分号之间的空格
    before_comment_spaces = len(main_part) - len(main_part.rstrip())

    # 计算分号与注释内容之间的空格
    after_semicolon_spaces = len(comment_part) - len(comment_part.lstrip())

    return {
        'before_comment': before_comment_spaces,
        'after_semicolon': after_semicolon_spaces
    }


def create_merged_line_with_vdf2_spacing(key, value, v2_spacing_info, v2_comment_spacing_info, use_comment=None):
    """使用vdf2的等号前后空格和分号前后空格格式"""
    # 构建空格字符串
    before_equals_spaces = ' ' * v2_spacing_info.get('before_equals', 1)
    after_equals_spaces = ' ' * v2_spacing_info.get('after_equals', 1)
    before_comment_spaces = ' ' * v2_comment_spacing_info.get('before_comment', 0)
    after_semicolon_spaces = ' ' * v2_comment_spacing_info.get('after_semicolon', 1)

    # 构建主部分
    main_part = f"{key}{before_equals_spaces}={after_equals_spaces}{value}"

    # 添加注释
    if use_comment:
        # 清理注释内容（移除可能的分号和前后空格）
        clean_comment = use_comment.strip()
        if clean_comment.startswith(';'):
            clean_comment = clean_comment[1:].strip()

        if clean_comment:
            # 使用vdf2的分号前后空格格式
            comment_part = f"{before_comment_spaces};{after_semicolon_spaces}{clean_comment}"
            return main_part + comment_part
        else:
            # 如果注释内容为空，只保留分号和前面的空格（如果有的话）
            if v2_comment_spacing_info.get('before_comment', 0) > 0:
                return main_part + ' ' * v2_comment_spacing_info['before_comment'] + ';'
            else:
                return main_part
    else:
        # 没有注释
        return main_part


def create_merged_line_with_vdf1_comment_spacing(key, value, v2_spacing_info, v1_comment_spacing_info,
                                                 use_comment=None):
    """使用vdf2的等号前后空格，但使用vdf1的分号前后空格格式"""
    # 构建空格字符串
    before_equals_spaces = ' ' * v2_spacing_info.get('before_equals', 1)
    after_equals_spaces = ' ' * v2_spacing_info.get('after_equals', 1)
    before_comment_spaces = ' ' * v1_comment_spacing_info.get('before_comment', 0)
    after_semicolon_spaces = ' ' * v1_comment_spacing_info.get('after_semicolon', 1)

    # 构建主部分
    main_part = f"{key}{before_equals_spaces}={after_equals_spaces}{value}"

    # 添加注释
    if use_comment:
        # 清理注释内容（移除可能的分号和前后空格）
        clean_comment = use_comment.strip()
        if clean_comment.startswith(';'):
            clean_comment = clean_comment[1:].strip()

        if clean_comment:
            # 使用vdf1的分号前后空格格式
            comment_part = f"{before_comment_spaces};{after_semicolon_spaces}{clean_comment}"
            return main_part + comment_part
        else:
            # 如果注释内容为空，只保留分号和前面的空格（如果有的话）
            if v1_comment_spacing_info.get('before_comment', 0) > 0:
                return main_part + ' ' * v1_comment_spacing_info['before_comment'] + ';'
            else:
                return main_part
    else:
        # 没有注释
        return main_part


def print_vdf_section_details(vdf_parsed, vdf_name):
    print(f"\n=== {vdf_name} Details ===")
    for section in vdf_parsed['section_order']:
        print(f"\n[{section}]")
        for line in vdf_parsed['section_content'][section]:
            print(f"  {repr(line)}")  # 使用repr显示原始格式


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
    """Use v1 value if component counts differ; use v2 if counts are equal"""
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
        v2_section_order = vdf2_parsed.get('section_order', [])

        merged_data = {}
        merged_key_order = {}
        merged_section_content = {}
        merged_original_lines = {}

        # 只保留vdf1中存在的章节（删除vdf2独有的章节）
        merged_section_order = [section for section in v1_section_order]

        # 只保留vdf1的独立注释（删除vdf2独有的独立注释）
        merged_standalone_comments = vdf1_parsed.get('standalone_comments', [])

        for section in merged_section_order:
            merged_data[section] = {}
            merged_key_order[section] = []
            merged_section_content[section] = []
            merged_original_lines[section] = {}

            v1_has_section = section in v1_content
            v2_has_section = section in v2_content

            # 只处理vdf1中存在的章节
            if v1_has_section:
                # 首先处理v1的内容（保持顺序）
                for line in v1_content[section]:
                    if is_key_value_line(line):
                        key = extract_key_from_line(line)
                        if key:
                            v1_val = v1_data[section][key]
                            v1_original_line = v1_original.get(section, {}).get(key, line)
                            v1_comment = v1_comments.get(section, {}).get(key, '')
                            v1_comment_spacing_info = v1_comment_spacing.get(section, {}).get(key, {'before_comment': 0,
                                                                                                    'after_semicolon': 1})

                            # 只保留vdf1中存在的键（删除vdf2独有的键）
                            if v2_has_section and key in v2_data[section]:
                                # 键在两个文件中都存在
                                v2_val = v2_data[section][key]
                                v2_comment = v2_comments.get(section, {}).get(key, '')
                                v2_spacing_info = v2_spacing.get(section, {}).get(key, {'before_equals': 1,
                                                                                        'after_equals': 1})
                                v2_comment_spacing_info = v2_comment_spacing.get(section, {}).get(key,
                                                                                                  {'before_comment': 0,
                                                                                                   'after_semicolon': 1})

                                final_val = merge_values_by_count(v1_val, v2_val)

                                # 检查注释是否相同，如果不同则使用vdf1的注释内容
                                # 并使用对应的分号前后空格格式
                                if v1_comment.strip() != v2_comment.strip():
                                    # 使用vdf1的注释内容和分号前后空格格式
                                    final_comment = v1_comment
                                    merged_line = create_merged_line_with_vdf1_comment_spacing(
                                        key, final_val, v2_spacing_info, v1_comment_spacing_info, final_comment)
                                    comment_source = "vdf1 (with vdf1 semicolon spacing)"
                                else:
                                    # 使用vdf2的注释内容和分号前后空格格式
                                    final_comment = v2_comment
                                    merged_line = create_merged_line_with_vdf2_spacing(
                                        key, final_val, v2_spacing_info, v2_comment_spacing_info, final_comment)
                                    comment_source = "vdf2 (with vdf2 semicolon spacing)"

                                merged_section_content[section].append(merged_line)
                                merged_data[section][key] = final_val
                                merged_key_order[section].append(key)
                                merged_original_lines[section][key] = merged_line

                                # 输出调试信息
                                print(
                                    f"Key '{key}': before_equals={v2_spacing_info['before_equals']}, after_equals={v2_spacing_info['after_equals']}, comment_source={comment_source}")
                            else:
                                # 键只在v1中存在，保留（vdf2中没有这个键）
                                merged_section_content[section].append(v1_original_line)
                                merged_data[section][key] = v1_val
                                merged_key_order[section].append(key)
                                merged_original_lines[section][key] = v1_original_line
                    else:
                        # 非键值行（注释、空行等），直接添加（只保留vdf1中的非键值行）
                        merged_section_content[section].append(line)

        # 分离键值行和非键值行
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
            'section_non_kv_lines': merged_non_kv_lines,
            'standalone_comments': merged_standalone_comments,
            'original_key_value_lines': merged_original_lines
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise


def save_vdf_file(parsed_data, output_path):
    content = generate_vdf_content(parsed_data)
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)


def find_vdf_files(folder_path):
    """查找文件夹中的所有vdf文件"""
    vdf_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith('.vdf'):
                vdf_files.append(os.path.join(root, file))
    return vdf_files


def batch_merge_folders(folder1_path, folder2_path, output_folder_path):
    """批量合并两个文件夹中的vdf文件"""
    # 查找两个文件夹中的所有vdf文件
    vdf1_files = find_vdf_files(folder1_path)
    vdf2_files = find_vdf_files(folder2_path)

    # 提取文件名（不含路径）用于匹配
    vdf1_dict = {os.path.basename(file): file for file in vdf1_files}
    vdf2_dict = {os.path.basename(file): file for file in vdf2_files}

    # 找到两个文件夹中都存在的文件
    common_files = set(vdf1_dict.keys()) & set(vdf2_dict.keys())

    print(f"Found {len(vdf1_files)} VDF files in folder 1")
    print(f"Found {len(vdf2_files)} VDF files in folder 2")
    print(f"Found {len(common_files)} common VDF files to merge")

    # 创建输出文件夹
    os.makedirs(output_folder_path, exist_ok=True)

    merged_count = 0
    skipped_count = 0

    for filename in common_files:
        try:
            vdf1_path = vdf1_dict[filename]
            vdf2_path = vdf2_dict[filename]
            output_path = os.path.join(output_folder_path, filename)

            print(f"\n=== Merging {filename} ===")
            print(f"Folder1 file: {vdf1_path}")
            print(f"Folder2 file: {vdf2_path}")
            print(f"Output file: {output_path}")

            # 读取并解析文件
            vdf1_parsed = read_vdf_file(vdf1_path)
            vdf2_parsed = read_vdf_file(vdf2_path)

            # 合并文件
            merged_parsed = merge_vdf_data(vdf1_parsed, vdf2_parsed)

            # 保存合并后的文件
            save_vdf_file(merged_parsed, output_path)

            print(f"✓ Successfully merged {filename}")
            merged_count += 1

        except Exception as e:
            print(f"✗ Failed to merge {filename}: {e}")
            skipped_count += 1
            continue

    # 复制folder1中独有的文件到输出文件夹
    unique_to_folder1 = set(vdf1_dict.keys()) - set(vdf2_dict.keys())
    for filename in unique_to_folder1:
        try:
            source_path = vdf1_dict[filename]
            output_path = os.path.join(output_folder_path, filename)

            # 确保目标目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 复制文件
            import shutil
            shutil.copy2(source_path, output_path)
            print(f"✓ Copied unique file from folder1: {filename}")
            merged_count += 1

        except Exception as e:
            print(f"✗ Failed to copy {filename}: {e}")
            skipped_count += 1

    print(f"\n=== Merge Summary ===")
    print(f"Total files processed: {len(common_files) + len(unique_to_folder1)}")
    print(f"Successfully merged: {merged_count}")
    print(f"Skipped/Failed: {skipped_count}")
    print(f"Output folder: {output_folder_path}")


def main():
    # 配置文件夹路径
    folder1_path = "1"  # 第一个文件夹路径
    folder2_path = "2"  # 第二个文件夹路径
    output_folder_path = "merged_folder"  # 输出文件夹路径

    # 检查文件夹是否存在
    if not os.path.exists(folder1_path):
        print(f"Error: Folder '{folder1_path}' does not exist!")
        return
    if not os.path.exists(folder2_path):
        print(f"Error: Folder '{folder2_path}' does not exist!")
        return

    try:
        # 批量合并文件夹
        batch_merge_folders(folder1_path, folder2_path, output_folder_path)

        print("\nBatch merge completed!")
        print("All original spacing and formatting preserved exactly!")
        print("Comments from folder1 are used when comments differ between files!")
        print("Sections and keys that only exist in folder2 have been deleted!")
        print("Spacing around equals sign from folder2 is preserved exactly!")
        print("When using folder1 comments, folder1's semicolon spacing is maintained!")
        print("When using folder2 comments, folder2's semicolon spacing is maintained!")

    except Exception as e:
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()