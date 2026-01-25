import pandas as pd
import json
from pathlib import Path


def csv_to_compound(csv_path):
    """转换单个CSV文件为化合物数据对象（自动检测标题行）"""
    try:
        # 1. 先读取预览，判断是否有标题行
        preview_df = pd.read_csv(csv_path, nrows=5)
        first_value = preview_df.iloc[0, 0]

        # 判断规则：如果第一行第一列是字符串或包含"Wavenumber"，说明有标题
        has_header = (isinstance(first_value, str) or
                      str(first_value).lower().strip() == 'wavenumber' or
                      preview_df.columns[0].lower().strip() == 'wavenumber')

        if has_header:
            print(f"  ℹ️ 检测到标题行，自动跳过")
            # 重新读取，跳过标题行（header=0表示第一行是标题）
            df = pd.read_csv(csv_path, header=0, names=['Wavenumber', 'Transmittance'])
        else:
            # 无标题行，使用自定义列名
            print(f"  ℹ️ 无标题行，使用自定义列名")
            df = pd.read_csv(csv_path, header=None, names=['Wavenumber', 'Transmittance'])

        # 2. 数据清洗：删除空行和非数字行
        df = df.dropna(subset=['Wavenumber', 'Transmittance'])
        df = df[pd.to_numeric(df['Wavenumber'], errors='coerce').notnull()]
        df = df[pd.to_numeric(df['Transmittance'], errors='coerce').notnull()]

        # 3. 获取化合物名并优化显示
        raw_name = Path(csv_path).stem
        compound_name = raw_name.replace('-', ' ').replace('oC', '°C')

        # 4. 分子式（可手动优化）
        formula = input(f"请输入 {compound_name} 的分子式（如C2H6O，留空跳过）: ").strip()
        if not formula:
            formula = "未知"

        # 5. 转换数据
        x_values = df['Wavenumber'].astype(float).tolist()
        y_values = df['Transmittance'].astype(float).tolist()

        # 6. 数据验证
        if len(x_values) == 0:
            print(f"  ❌ {compound_name} 没有有效数据")
            return None

        print(f"  ✅ 成功: {len(x_values)} 个数据点")

        return {
            "name": compound_name,
            "formula": formula,
            "x": x_values,
            "y": y_values
        }

    except Exception as e:
        print(f"  ❌ 转换失败: {e}")
        return None

    except Exception as e:
        print(f"❌ 转换失败 {csv_path}: {e}")
        return None


def batch_convert(folder_path, hot_count=10):
    """
    混合方案：生成索引 + 热数据 + 冷数据文件
    """
    folder = Path(folder_path)
    output_path = Path("spectra")
    output_path.mkdir(exist_ok=True)

    if not folder.exists():
        print(f"❌ 文件夹不存在: {folder_path}")
        return

    csv_files = list(folder.glob("*.csv"))
    if not csv_files:
        print(f"⚠️ 没有找到CSV文件")
        return

    print(f"📂 找到 {len(csv_files)} 个CSV文件")
    print("=" * 60)

    # 转换所有数据
    all_compounds = []
    for i, csv_file in enumerate(csv_files, 1):
        print(f"\n[{i}/{len(csv_files)}] 处理: {csv_file.name}")
        compound = csv_to_compound(csv_file)
        if compound:
            all_compounds.append(compound)

    if not all_compounds:
        print("\n❌ 没有成功转换任何数据")
        return

    # 排序（按名称，可修改规则）
    all_compounds.sort(key=lambda x: x['name'])

    # 分离热/冷数据
    hot_data = all_compounds[:hot_count]
    cold_data = all_compounds[hot_count:]

    print("\n" + "=" * 60)
    print(f"✅ 总共成功: {len(all_compounds)} 个化合物")
    print(f"🔥 热数据: {len(hot_data)} 个（预加载）")
    print(f"❄️ 冷数据: {len(cold_data)} 个（按需加载）")

    # 生成热数据文件（预加载）
    print("\n生成热数据文件: spectra_hot.js")
    with open("spectra_hot.js", 'w', encoding='utf-8') as f:
        f.write(f"const spectraHot = {json.dumps(hot_data, ensure_ascii=False, indent=4)};")

    # 生成冷数据文件（按需加载）
    print("\n生成冷数据文件...")
    for i, compound in enumerate(cold_data, 1):
        safe_name = compound['name'].replace(' ', '_').replace('°', 'C')
        json_file = output_path / f"{safe_name}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(compound, f, ensure_ascii=False, indent=4)
        print(f"  [{i}/{len(cold_data)}] {json_file.name}")

    # 生成索引文件（包含所有）
    print("\n生成索引文件: spectra_index.js")
    index_data = []
    for i, compound in enumerate(all_compounds):
        index_data.append({
            "name": compound['name'],
            "formula": compound['formula'],
            "file": f"{compound['name'].replace(' ', '_').replace('°', 'C')}.json" if i >= hot_count else None,
            "is_hot": i < hot_count
        })

    with open("spectra_index.js", 'w', encoding='utf-8') as f:
        f.write(f"const spectraIndex = {json.dumps(index_data, ensure_ascii=False, indent=4)};")

    print("\n" + "=" * 60)
    print("💾 文件生成完成！")
    print("📁 请上传以下文件到GitHub:")
    print("  1. spectra_index.js")
    print("  2. spectra_hot.js")
    print(f"  3. spectra/ 文件夹 ({len(cold_data)} 个JSON文件)")
    print("=" * 60)


def main():
    print("=" * 60)
    print("红外光谱批量转换工具（混合方案）")
    print("=" * 60)

    raw_data_folder = "raw_data"
    # 热数据数量：可调整，建议10-15个
    batch_convert(raw_data_folder, hot_count=10)

    print("\n转换完成！")


if __name__ == "__main__":
    main()