import os
import re
import csv
from collections import defaultdict
import sys

def extract_tracks(folder_path, folder_type='album'):
    """
    提取文件夹下音频/视频文件信息，适应专辑、单曲、演唱会三类目录。
    
    album / single / live 模式都会返回 release_date 字段。
    live 模式会提取 live_name。
    album 模式会提取 album_name（兼容 Album 和 EP 命名）。
    
    返回字段：
        - track_no (album)
        - track_name (album / single)
        - file_name
        - folder_type
        - parent_folder (single)
        - release_date (album / single / live)
        - live_name (live)
        - album_name (album)
    """
    tracks = []

    if folder_type == 'single':
        # 遍历单曲目录下的每个子文件夹
        for subfolder in os.listdir(folder_path):
            subfolder_path = os.path.join(folder_path, subfolder)
            if os.path.isdir(subfolder_path):
                # 提取子文件夹开头的日期
                release_date = ''
                parts = subfolder.split('_', 1)
                if len(parts) > 1:
                    date_candidate = parts[0]
                    if len(date_candidate) == 10 and date_candidate.count('.') == 2:
                        release_date = date_candidate

                # 调用 album 逻辑提取每个子文件夹
                sub_tracks = extract_tracks(subfolder_path, folder_type='album')
                for t in sub_tracks:
                    t['parent_folder'] = subfolder
                    t['release_date'] = release_date
                    t['folder_type'] = 'single'
                    tracks.append(t)
        return tracks

    if folder_type == 'live':
        # 遍历演唱会文件夹的文件
        for file in os.listdir(folder_path):
            full_path = os.path.join(folder_path, file)
            if not os.path.isfile(full_path):
                continue

            name, ext = os.path.splitext(file)
            if ext.lower() not in ['.mp4', '.mkv', '.avi']:
                continue  # 只处理视频文件

            if 'cover' in name.lower():
                continue  # 跳过封面或非正式文件

            # 提取开头日期和 live_name
            release_date = ''
            live_name = name
            if '-' in name:
                parts = name.split('-', 1)
                date_candidate = parts[0]
                if len(date_candidate) == 10 and date_candidate.count('.') == 2:
                    release_date = date_candidate
                    live_name = parts[1]

            tracks.append({
                'file_name': file,
                'folder_type': 'live',
                'release_date': release_date,
                'live_name': live_name
            })
        return tracks

    # album 模式
    release_date = ''
    album_name = ''
    folder_name = os.path.basename(folder_path)

    # 提取日期
    date_candidate = folder_name.split('_', 1)[0]
    release_date = date_candidate if len(date_candidate) == 10 and date_candidate.count('.') == 2 else ''

    # 提取专辑名
    last_underscore_idx = folder_name.rfind('_')
    if last_underscore_idx != -1:
        name_part = folder_name[last_underscore_idx + 1:]
    else:
        name_part = folder_name
    # 去掉末尾方括号及其内容
    if '[' in name_part:
        name_part = name_part.split('[', 1)[0].strip()
    album_name = name_part.strip()

    for file in os.listdir(folder_path):
        full_path = os.path.join(folder_path, file)
        if not os.path.isfile(full_path):
            continue
        name, ext = os.path.splitext(file)
        if ext.lower() not in ['.flac', '.mp3', '.wav']:
            continue
        if 'cover' in name.lower():
            continue  # 跳过封面

        if '.' in name:
            parts = name.split('.', 1)
            track_no, track_name = parts[0].strip(), parts[1].strip()
        else:
            track_no, track_name = '', name.strip()

        tracks.append({
            'track_no': track_no,
            'track_name': track_name,
            'file_name': file,
            'folder_type': 'album',
            'release_date': release_date,
            'album_name': album_name
        })

    return tracks

def scan_artist_folder(artist_folder):
    """扫描歌手文件夹下一级子目录，并根据命名调用 extract_tracks"""
    all_tracks = []
    for sub in os.listdir(artist_folder):
        sub_path = os.path.join(artist_folder, sub)
        if not os.path.isdir(sub_path):
            continue

        if sub == '单曲':
            tracks = extract_tracks(sub_path, folder_type='single')
        elif sub == '演唱会':
            tracks = extract_tracks(sub_path, folder_type='live')
        else:
            tracks = extract_tracks(sub_path, folder_type='album')

        all_tracks.extend(tracks)
    return all_tracks

def generate_csv(all_tracks, artist_folder):
    """生成 CSV，Album 字段 album 使用 album_name，single/live 用 '-'"""
    artist_name = os.path.basename(os.path.normpath(artist_folder))
    output_dir = os.path.abspath(os.path.join(os.getcwd(), "..", "List", artist_name))
    os.makedirs(output_dir, exist_ok=True)
    csv_file = os.path.join(output_dir, f"{artist_name}.csv")

    with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Type','Date','Album','No','Name'])

        for t in all_tracks:
            Type = t.get('folder_type', '-')
            Date = t.get('release_date', '-') or '-'

            if Type == 'album':
                Album = t.get('album_name', '-') or '-'
                No = t.get('track_no', '-') or '-'
                Name = t.get('track_name', '-') or '-'
            else:
                Album = '-'
                No = '-'
                if Type == 'single':
                    Name = t.get('track_name', '-') or '-'
                elif Type == 'live':
                    Name = t.get('live_name', '-') or '-'
                else:
                    Name = '-'

            writer.writerow([Type, Date, Album, No, Name])
            
    # 删除结尾多余换行
    with open(csv_file, 'rb+') as file:
        file.seek(-2, os.SEEK_END)
        file.truncate()

    print(f"CSV 已生成：{csv_file}")
    return csv_file

def csv_to_markdown_grouped(csv_path):
    """
    从音乐 CSV 文件生成美化的 README.md。
    Albums 分块显示曲目列表，Singles/Lives 按时间排序直接列出。
    CSV 应包含字段: Type, Date, Album, No, Name, Parent_Folder (可选)
    """
    import os
    import csv
    from collections import defaultdict

    output_md_path = os.path.join(os.path.dirname(csv_path), "README.md")
    albums = defaultdict(list)
    singles = []
    lives = []

    # 读取 CSV 并分类
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            type_key = row['Type']
            if type_key == 'album':
                release_date = row['Date']
                album_name = row['Album']
                albums[(release_date, album_name)].append((row['No'].zfill(3), row['Name']))
            elif type_key == 'single':
                release_date = row['Date']
                track_name = row['Name']
                singles.append((release_date, track_name))
            elif type_key == 'live':
                release_date = row['Date']
                track_name = row['Name']
                lives.append((release_date, track_name))

    # 写入 Markdown
    with open(output_md_path, 'w', encoding='utf-8') as f:
        artist_name = os.path.splitext(os.path.basename(csv_path))[0]
        f.write(f"# 🎵 {artist_name} 歌曲列表\n\n")

        # Albums
        if albums:
            f.write("## 📀 Albums\n\n")
            for (date, album_name) in sorted(albums.keys()):
                f.write(f"### 📁 ({date}) {album_name} \n\n")
                for no, name in sorted(albums[(date, album_name)], key=lambda x: x[0]):
                    f.write(f"- **[{no}]** {name}\n")
                f.write("\n")

        # Singles
        if singles:
            f.write("## 🎵 Singles\n\n")
            for date, name in sorted(singles, key=lambda x: x[0]):
                f.write(f"- **[{date}]** {name}\n")
            f.write("\n")

        # Lives
        if lives:
            f.write("## 🎤 Lives\n\n")
            for date, name in sorted(lives, key=lambda x: x[0]):
                display_date = date if date else "-"
                f.write(f"- **[{display_date}]** {name}\n")
            f.write("\n")

    # 删除结尾多余换行
    with open(output_md_path, 'rb+') as file:
        file.seek(-2, os.SEEK_END)
        file.truncate()
        
    print(f"README.md 已生成：{output_md_path}")
    return output_md_path

def process_all_artists_interactive(base_folder):
    """
    遍历 base_folder 下的所有歌手文件夹，
    对每个歌手执行 scan → CSV → Markdown，
    并在交互时让用户选择是否处理。
    """
    results = {}
    process_all = False  # 标志位：如果用户选择全部处理，就跳过交互

    for artist in os.listdir(base_folder):
        artist_folder = os.path.join(base_folder, artist)
        if not os.path.isdir(artist_folder):
            continue  # 跳过非文件夹

        if not process_all:
            choice = input(f"\n=== 检测到歌手: {artist}，是否处理？(Y/N/A[全部处理]) >>> ").strip().lower()
            if choice == 'n':
                print(f"⏭️ 跳过 {artist}")
                continue
            elif choice == 'a':
                process_all = True
                print("✅ 后续将自动处理所有歌手。")

        print(f"\n🎶 开始处理歌手: {artist} ...")
        try:
            all_tracks = scan_artist_folder(artist_folder)
            csv_path = generate_csv(all_tracks, artist_folder)
            md_path = csv_to_markdown_grouped(csv_path)
            results[artist] = {
                "csv": csv_path,
                "markdown": md_path
            }
            print(f"✅ {artist} 处理完成！")
        except Exception as e:
            print(f"❌ {artist} 处理失败: {e}")
            results[artist] = {"error": str(e)}

    print("\n🎉 所有歌手处理完成！")
    return results

def scan_and_export_summary(folder_path):
    """
    扫描给定目录下的子文件夹，收集形如 '歌手-歌名_来源.mp3' 的信息，
    输出 CSV 文件到 ../List/Summary.csv
    CSV 字段: Singer, Name, From
    """
    records = []

    def process_file(file):
        name, ext = os.path.splitext(file)
        if ext.lower() != ".mp3":
            return None
        # 解析 "歌手-歌名_来源"
        if "-" not in name or "_" not in name:
            return None
        try:
            singer, rest = name.split("-", 1)
            track_name, source = rest.rsplit("_", 1)
            return {"Singer": singer.strip(), "Name": track_name.strip(), "From": source.strip()}
        except ValueError:
            return None

    # 只扫描子文件夹
    for subfolder in os.listdir(folder_path):
        subfolder_path = os.path.join(folder_path, subfolder)
        if os.path.isdir(subfolder_path):
            for file in os.listdir(subfolder_path):
                full_path = os.path.join(subfolder_path, file)
                if os.path.isfile(full_path):
                    record = process_file(file)
                    if record:
                        records.append(record)

    # 确保输出目录存在
    output_dir = os.path.abspath(os.path.join(os.getcwd(), "..", "List"))
    os.makedirs(output_dir, exist_ok=True)
    output_csv = os.path.join(output_dir, "Summary.csv")

    # 写 CSV
    with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["Singer", "Name", "From"])
        writer.writeheader()
        writer.writerows(records)

    # 删除结尾多余换行
    with open(output_csv, 'rb+') as file:
        file.seek(-2, os.SEEK_END)
        file.truncate()
    
    print(f"✅ Summary.csv 已生成: {output_csv}")
    return output_csv

def summary_csv_to_markdown(csv_path):
    """
    根据 Summary.csv 生成 README.md
    - 顶部给出“歌手统计”，并注明每位歌手在正文中“从第几行开始”
    - 正文按歌手分区、每首歌按 Name 排序
    输出地址：与 CSV 同目录的 README.md
    """
    import os, csv
    from collections import defaultdict

    # 读取
    records = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)

    # 分组
    grouped = defaultdict(list)
    for r in records:
        grouped[r["Singer"]].append(r)

    singers = sorted(grouped.keys())
    total_tracks = sum(len(grouped[s]) for s in singers)

    # ---------- 先生成“正文内容”，精确计算每个歌手标题在正文中的相对行号 ----------
    content_lines = []  # 每个元素是一整行（不含结尾换行符）
    singer_rel_line = {}  # 歌手 -> 在“正文部分”中的起始行号（从1开始）

    current_rel = 1
    for singer in singers:
        singer_rel_line[singer] = current_rel  # 标题的行号
        content_lines.append(f"## {singer} (共 {len(grouped[singer])} 首)")
        content_lines.append("")  # 空行
        for r in sorted(grouped[singer], key=lambda x: x["Name"]):
            content_lines.append(f"- {r['Name']} （{r['From']}）")
        content_lines.append("")  # 分段空行
        current_rel = len(content_lines) + 1  # 下一段标题所在行

    # ---------- 根据最终文档结构计算偏移量（正文前共有多少行） ----------
    # 头部固定4行：
    # 1: "# 🎶 歌手歌曲汇总"
    # 2: ""（空行）
    # 3: "## 歌手统计"
    # 4: ""（空行）
    # 统计表每位歌手各1行；然后：
    # +1 空行
    # +1 "**总计：X 首**"
    # +1 空行
    header_lines_count = 4
    stats_lines_count = len(singers)         # 每个歌手一行
    tail_after_stats = 3                     # 空行 + 总计 + 空行
    offset = header_lines_count + stats_lines_count + tail_after_stats  # 正文首行的实际行号 - 1

    # 计算每位歌手在最终文档中的绝对起始行号
    singer_abs_line = {s: singer_rel_line[s] + offset for s in singers}

    # ---------- 组装整份 Markdown ----------
    lines = []
    lines.append("# 🎶 歌手歌曲汇总")
    lines.append("")
    lines.append("## 歌手统计")
    lines.append("")

    # 统计块（带行号）
    for s in singers:
        lines.append(f"- {s}：{len(grouped[s])} 首 （从第 {singer_abs_line[s]} 行开始）")
    lines.append("")
    lines.append(f"**总计：{total_tracks} 首**")
    lines.append("")

    # 正文
    lines.extend(content_lines)

    output_md = os.path.join(os.path.dirname(csv_path), "README.md")
    with open(output_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")  # 统一用 \n，结尾保留1个换行

    print(f"✅ README.md 已生成: {output_md}")
    return output_md

def main():
    if len(sys.argv) != 2:
        print("用法: python3 generate_summary.py <音乐文件夹路径>")
        sys.exit(1)

    base_folder = sys.argv[1]
    if not os.path.isdir(base_folder):
        print(f"错误: 路径 {base_folder} 不存在或不是目录")
        sys.exit(1)

    print(f"扫描目录: {base_folder}")
    process_all_artists_interactive(base_folder)
    
    print(f"\n🎶 开始处理 Cloud Music ...")
    csv_path = scan_and_export_summary(f"{base_folder}/CloudMusic")
    summary_csv_to_markdown(csv_path)
    print("✅ 完成")

if __name__ == "__main__":
    main()