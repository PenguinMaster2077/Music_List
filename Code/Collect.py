import os
import re
import csv
from collections import defaultdict

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
    if len(folder_name) >= 10 and folder_name[:10].count('.') == 2:
        release_date = folder_name[:10]
        # 匹配 Album 或 EP 并提取专辑名
        match = re.search(r'\d{4}\.\d{2}\.\d{2}_.*?_(?:Album|EP)_(.*?)\[', folder_name)
        if match:
            album_name = match.group(1).strip()
        else:
            match2 = re.search(r'\d{4}\.\d{2}\.\d{2}_.*?_(?:Album|EP)_(.*)', folder_name)
            if match2:
                album_name = match2.group(1).strip()
            else:
                album_name = folder_name[11:].split('[')[0].strip()

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
            track_no, track_name = parts[0], parts[1]
        else:
            track_no, track_name = '', name

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
    output_dir = os.path.abspath(os.path.join(os.getcwd(), "..", "List", "JP", artist_name))
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

    print(f"CSV 已生成：{csv_file}")
    return csv_file

def generate_readme_from_csv_by_type(csv_file):
    """从 CSV 文件生成 README.md，按 Album / Single / Live 分块"""
    artist_name = os.path.splitext(os.path.basename(csv_file))[0]
    readme_file = os.path.join(os.path.dirname(csv_file), "README.md")

    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        print("CSV 文件为空，无法生成 README.md")
        return None

    headers = rows[0]
    data_rows = rows[1:]

    # 按 Type 分类
    grouped = defaultdict(list)
    for row in data_rows:
        grouped[row[0]].append(row)

    # 输出顺序： album -> single -> live
    type_order = ['album', 'single', 'live']

    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(f"# {artist_name} 歌曲列表\n\n")

        total_tracks = len(data_rows)
        f.write(f"共 {total_tracks} 首歌\n\n")

        for t in type_order:
            if t not in grouped or not grouped[t]:
                continue

            f.write(f"## {t.capitalize()}s\n\n")
            f.write("| " + " | ".join(headers) + " |\n")
            f.write("|" + "|".join(["---"] * len(headers)) + "|\n")

            for row in grouped[t]:
                f.write("| " + " | ".join(row) + " |\n")
            
            f.write("\n")  # 每个类型后加空行

    print(f"README.md 已生成：{readme_file}")
    return readme_file

# 使用示例
artist_folder = "/mnt/e/Music/铃木爱理"
all_tracks = scan_artist_folder(artist_folder)
csv_path = generate_csv(all_tracks, artist_folder)
generate_readme_from_csv_by_type(csv_path)