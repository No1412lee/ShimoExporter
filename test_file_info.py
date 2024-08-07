import os
import json
from shimo_file_info import FolderInfo, ShimoInfo, ShimoStatus
from datetime import date

# 读取配置文件
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)
    config['Sleep'] /= 1000

files_info_path = os.path.join(config['Path'], 'files_info.json')
if os.path.exists(files_info_path):
    pre_folder_info = FolderInfo.from_json(files_info_path)
    pre_folder_info.filter_empty_folders()
    pre_folder_info.save_json("test.json")
    with open('diff.log', 'w', encoding='utf-8') as f:
        pre_folder_info.print_diff(f)