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

def clean_name(name):
    """清理文件名，例如去掉扩展名或多余空格"""
    return os.path.splitext(name)[0].strip()

def clean_name(name, folder_type=None):
    """
    清理文件名
    - Albums: 保留所有信息
    - Singles / Lives: 去掉文件扩展名和前后空格，但保留括号
    """
    name = os.path.splitext(name)[0].strip()
    if folder_type == 'album':
        return name
    # Singles / Live 只去掉空格，不去掉括号内容
    return name

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

# 使用示例
artist_folder = "/mnt/e/Music/铃木爱理"
all_tracks = scan_artist_folder(artist_folder)
csv_path = generate_csv(all_tracks, artist_folder)
csv_to_markdown_grouped(csv_path)