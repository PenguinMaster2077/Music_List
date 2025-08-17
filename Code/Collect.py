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
    parser = argparse.ArgumentParser(description="音乐文件夹处理工具")
    parser.add_argument("path", help="音乐文件夹路径")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-s", action="store_true", help="启动模式 S")
    group.add_argument("-a", action="store_true", help="启动模式 A")
    group.add_argument("-c", action="store_true", help="启动模式 C")
    parser.add_argument("-m", "--mode", choices=["All", "Partial"], default="Partial",
                    help="CSV 更新模式: All=完整覆盖, Partial=只新增条目 (默认: Partial)")

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
        Collect.mode_c(base_folder, scan_mode=scan_mode)

    print("✅ 完成")

if __name__ == "__main__":
    main()