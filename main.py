import os

# 块类型常量定义
COMMENT_BLOCK = "comment"
SECTION_BLOCK = "section"
KEY_VALUE_BLOCK = "key_value"


def read_vdf_file(file_path):
    """读取VDF文件并调用解析函数"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return parse_vdf_content(content, file_path)


def parse_vdf_content(content, file_name="unknown"):
    """
    解析VDF内容，为每个独立注释标记章节归属
    - 确保后续合并时能按原章节位置放置
    """
    parsed_result = {
        "blocks": [],  # 有序块列表（保留原始顺序）
        "data": {},  # 章节-键值对数据
        "section_order": [],  # 章节顺序
        "key_order": {},  # 章节内键顺序
        "line_comments": {}  # 键值对行内注释
    }

    current_section = None  # 当前活跃章节
    prev_section = None  # 前一个章节（用于标记章节间注释归属）
    temp_comment_lines = []  # 临时存储连续注释行

    lines = content.split('\n')
    for line in lines:
        original_line = line.rstrip()
        stripped_line = line.strip()

        # 处理独立注释行（空行或;开头）
        if not stripped_line or stripped_line.startswith(';'):
            temp_comment_lines.append(original_line)
            continue

        # 处理暂存的注释块（非注释行出现时）
        if temp_comment_lines:
            # 确定注释归属章节
            comment_belong_to = current_section if current_section else prev_section
            parsed_result["blocks"].append({
                "type": COMMENT_BLOCK,
                "content": temp_comment_lines.copy(),
                "belong_to_section": comment_belong_to
            })
            temp_comment_lines.clear()

        # 解析章节块
        if stripped_line.startswith('[') and stripped_line.endswith(']'):
            section_name = stripped_line[1:-1].strip()
            prev_section = current_section
            current_section = section_name

            if section_name not in parsed_result["data"]:
                parsed_result["data"][section_name] = {}
                parsed_result["key_order"][section_name] = []
                parsed_result["section_order"].append(section_name)

            parsed_result["blocks"].append({
                "type": SECTION_BLOCK,
                "name": section_name,
                "content": original_line,
                "belong_to_section": section_name
            })
            continue

        # 解析键值对块
        if '=' in stripped_line and current_section is not None:
            line_parts = stripped_line.split(';', 1)
            main_part = line_parts[0].strip()
            inline_comment = ';' + line_parts[1] if len(line_parts) > 1 else ''

            key_val = main_part.split('=', 1)
            if len(key_val) == 2:
                key = key_val[0].strip()
                value = key_val[1].strip()

                parsed_result["data"][current_section][key] = value
                if key not in parsed_result["key_order"][current_section]:
                    parsed_result["key_order"][current_section].append(key)
                if inline_comment:
                    parsed_result["line_comments"][f"{current_section}.{key}"] = inline_comment

                parsed_result["blocks"].append({
                    "type": KEY_VALUE_BLOCK,
                    "section": current_section,
                    "key": key,
                    "value": value,
                    "inline_comment": inline_comment,
                    "content": original_line,
                    "belong_to_section": current_section
                })
            continue

        # 处理未知内容（归为独立注释）
        comment_belong_to = current_section if current_section else prev_section
        parsed_result["blocks"].append({
            "type": COMMENT_BLOCK,
            "content": [original_line],
            "belong_to_section": comment_belong_to
        })

    # 处理文件末尾的注释块
    if temp_comment_lines:
        comment_belong_to = current_section if current_section else prev_section
        parsed_result["blocks"].append({
            "type": COMMENT_BLOCK,
            "content": temp_comment_lines,
            "belong_to_section": comment_belong_to
        })

    parsed_result["file_name"] = file_name
    return parsed_result


def generate_vdf_content(parsed_data):
    """根据块列表生成VDF内容"""
    output_lines = []
    for block in parsed_data["blocks"]:
        if isinstance(block["content"], list):
            output_lines.extend(block["content"])
        else:
            output_lines.append(block["content"])

    # 去除末尾多余空行
    while output_lines and not output_lines[-1].strip():
        output_lines.pop()

    return '\n'.join(output_lines)


def get_value_component_count(value):
    """计算键值按逗号分割的组成部分数量"""
    components = [comp.strip() for comp in value.split(',') if comp.strip()]
    return len(components)


def merge_vdf_data(vdf1_parsed, vdf2_parsed):
    """
    合并两个VDF解析结果
    核心：vdf1的独立注释按原章节归属位置合并
    """
    # 1. 按章节归属分组vdf1的独立注释
    v1_comments_by_section = {}
    for block in vdf1_parsed["blocks"]:
        if block["type"] == COMMENT_BLOCK:
            belong_section = block["belong_to_section"]
            if belong_section not in v1_comments_by_section:
                v1_comments_by_section[belong_section] = []
            v1_comments_by_section[belong_section].append(block)

    # 2. 以vdf2的块列表为基础框架
    merged_blocks = vdf2_parsed["blocks"].copy()
    v2_sections = set(vdf2_parsed["section_order"])
    v1_sections = set(vdf1_parsed["section_order"])
    all_sections = v2_sections | v1_sections

    # 3. 为每个章节插入对应归属的v1注释
    for target_section in all_sections:
        v1_target_comments = v1_comments_by_section.get(target_section, [])
        if not v1_target_comments:
            continue

        # 定位章节在vdf2中的位置区域
        section_start_idx = None
        section_end_idx = len(merged_blocks)

        for i, block in enumerate(merged_blocks):
            if block["type"] == SECTION_BLOCK and block["name"] == target_section:
                section_start_idx = i
            elif section_start_idx is not None and block["type"] == SECTION_BLOCK:
                section_end_idx = i
                break

        # 处理v1独有的章节（v2中不存在的章节）
        if section_start_idx is None:
            for comment_block in v1_target_comments:
                merged_blocks.append(comment_block)
            continue

        # 去重并插入注释到章节区域内
        v2_existing_comments = set()
        for i in range(section_start_idx, section_end_idx):
            block = merged_blocks[i]
            if block["type"] == COMMENT_BLOCK:
                v2_existing_comments.add(hash('\n'.join(block["content"])))

        inserted_count = 0
        for comment_block in v1_target_comments:
            comment_hash = hash('\n'.join(comment_block["content"]))
            if comment_hash not in v2_existing_comments:
                insert_pos = section_start_idx + 1 + inserted_count
                merged_blocks.insert(insert_pos, comment_block)
                inserted_count += 1
                section_end_idx += 1

    # 4. 处理全局注释（归属为None）
    v1_global_comments = v1_comments_by_section.get(None, [])
    if v1_global_comments:
        v2_global_comments = set()
        for block in merged_blocks:
            if block["type"] == COMMENT_BLOCK and block["belong_to_section"] is None:
                v2_global_comments.add(hash('\n'.join(block["content"])))

        global_insert_pos = 0
        for comment_block in v1_global_comments:
            comment_hash = hash('\n'.join(block["content"]))
            if comment_hash not in v2_global_comments:
                merged_blocks.insert(global_insert_pos, comment_block)
                global_insert_pos += 1

    # 5. 合并键值对
    merged_data = vdf2_parsed["data"].copy()
    for section in all_sections:
        if section not in merged_data:
            merged_data[section] = {}

        v1_section_data = vdf1_parsed["data"].get(section, {})
        v2_section_data = merged_data.get(section, {})
        for key in v1_section_data.keys() | v2_section_data.keys():
            v1_val = v1_section_data.get(key)
            v2_val = v2_section_data.get(key)

            if v1_val and v2_val:
                v1_count = get_value_component_count(v1_val)
                v2_count = get_value_component_count(v2_val)
                merged_data[section][key] = v1_val if v1_count > v2_count else v2_val
            elif v1_val:
                merged_data[section][key] = v1_val

            # 合并行内注释（v1优先）
            v1_inline_comm = vdf1_parsed["line_comments"].get(f"{section}.{key}")
            if v1_inline_comm:
                vdf2_parsed["line_comments"][f"{section}.{key}"] = v1_inline_comm

    # 6. 补充v1独有的章节和键值对
    v1_unique_sections = v1_sections - v2_sections
    for section in v1_unique_sections:
        # 添加章节块
        has_section_block = any(
            b["type"] == SECTION_BLOCK and b["name"] == section
            for b in merged_blocks
        )
        if not has_section_block:
            merged_blocks.append({
                "type": SECTION_BLOCK,
                "name": section,
                "content": f"[{section}]",
                "belong_to_section": section
            })

        # 添加键值对
        for key in vdf1_parsed["key_order"][section]:
            val = merged_data[section][key]
            inline_comm = vdf2_parsed["line_comments"].get(f"{section}.{key}", "")
            merged_blocks.append({
                "type": KEY_VALUE_BLOCK,
                "section": section,
                "key": key,
                "value": val,
                "inline_comment": inline_comm,
                "content": f"{key} = {val}{inline_comm}",
                "belong_to_section": section
            })

    # 整理元数据
    merged_section_order = vdf2_parsed["section_order"].copy()
    merged_section_order.extend(v1_unique_sections)

    merged_key_order = vdf2_parsed["key_order"].copy()
    for section in v1_unique_sections:
        merged_key_order[section] = vdf1_parsed["key_order"][section].copy()
    for section in v2_sections & v1_sections:
        for key in vdf1_parsed["key_order"][section]:
            if key not in merged_key_order[section]:
                merged_key_order[section].append(key)

    return {
        "blocks": merged_blocks,
        "data": merged_data,
        "section_order": merged_section_order,
        "key_order": merged_key_order,
        "line_comments": vdf2_parsed["line_comments"],
        "file_name": f"merged_{vdf1_parsed['file_name']}_{vdf2_parsed['file_name']}"
    }


def save_vdf_file(parsed_data, output_path):
    """保存合并后的VDF文件"""
    vdf_content = generate_vdf_content(parsed_data)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(vdf_content)
    print(f"合并文件已保存至：{output_path}")


def main():
    """主函数：执行VDF合并流程"""
    # 配置文件路径
    vdf1_path = "config1.vdf"
    vdf2_path = "config2.vdf"
    output_path = "merged_config.vdf"

    try:
        # 读取解析文件
        print(f"正在读取：{vdf1_path}（保留注释章节位置）")
        vdf1 = read_vdf_file(vdf1_path)
        v1_comment_count = sum(1 for b in vdf1["blocks"] if b["type"] == COMMENT_BLOCK)
        print(f"vdf1 独立注释块数量：{v1_comment_count}")

        print(f"\n正在读取：{vdf2_path}（键值基础文件）")
        vdf2 = read_vdf_file(vdf2_path)
        v2_comment_count = sum(1 for b in vdf2["blocks"] if b["type"] == COMMENT_BLOCK)
        print(f"vdf2 独立注释块数量：{v2_comment_count}")

        # 合并数据
        print("\n正在合并VDF数据...")
        merged = merge_vdf_data(vdf1, vdf2)
        merged_comment_count = sum(1 for b in merged["blocks"] if b["type"] == COMMENT_BLOCK)
        print(f"合并后独立注释块数量：{merged_comment_count}")

        # 保存结果
        save_vdf_file(merged, output_path)
        print("\n合并完成！")

    except FileNotFoundError as e:
        print(f"\n错误：{e}")
    except Exception as e:
        print(f"\n处理错误：{str(e)}")


if __name__ == "__main__":
    main()