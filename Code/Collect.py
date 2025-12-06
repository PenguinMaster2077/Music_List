import os
import re
import csv
from collections import defaultdict
import sys
import argparse
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), './Heads'))
import Heads.Head_Collect as Collect

def main():
    parser = argparse.ArgumentParser(
        description="音乐文件夹处理工具",
        formatter_class=argparse.RawTextHelpFormatter,  
        epilog="""示例：
        1) 模式 S：整理单个歌手
            python3 Collect.py -s "/mnt/e/Music/milet" (最佳条目)
            python3 Collect.py -s "/mnt/e/Music/milet" -m All (强制重新生成)

        2) 模式 A：整理多个歌手（目录下每个子目录为一个歌手）
            python3 Collect.py -s "/mnt/e/Music" -a (最佳条目)
            python3 Collect.py -s "/mnt/e/Music" -a -m All (强制重新生成)

        3) 模式 C：整理 CloudMusic 目录
            TBD

        说明：
        -s / -a / -c 只能三选一
        -m All     覆盖 CSV
        -m Partial 只追加，不覆盖（默认）
        """
    )
    parser.add_argument("path", help="音乐文件夹路径")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-s", action="store_true", help="启动模式 S，整理单个歌手")
    group.add_argument("-a", action="store_true", help="启动模式 A，整理所有歌手")
    group.add_argument("-c", action="store_true", help="启动模式 C，整理CloudMusic")
    parser.add_argument("-m", "--mode", choices=["All", "Partial"], default="Partial",
                    help="CSV 更新模式: All=完整覆盖, Partial=只新增条目 (默认)")

    args = parser.parse_args()
    base_folder = args.path
    scan_mode = args.mode

    if not os.path.isdir(base_folder):
        print(f"❌ 错误: 路径 {base_folder} 不存在或不是目录")
        sys.exit(1)

    if args.s:
        Collect.mode_s(base_folder, scan_mode=scan_mode)
    elif args.a:
        Collect.mode_a(base_folder, scan_mode=scan_mode)
    elif args.c:
        Collect.mode_c(base_folder)

    print("✅ 完成")

if __name__ == "__main__":
    main()