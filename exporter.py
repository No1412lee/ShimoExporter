import aiohttp
import asyncio
import time
import json
import os
import re
import sys
from datetime import datetime, date
import time
import shutil
from shimo_file_info import FolderInfo, ShimoInfo, ShimoStatus

# 读取配置文件
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)
    config['Sleep'] /= 1000

# 设置headers
headers_options = {
    'Cookie': config['Cookie'],
    'Referer': 'https://shimo.im/folder/123',
}

desktop_headers_options = {
    'Cookie': config['Cookie'],
    'Referer': 'https://shimo.im/desktop',
}


async def get_file_list(folder_info, folder='', base_path=''):
    try:
        params_options = {'collaboratorCount': 'true', 'folder': folder} if folder else {'collaboratorCount': 'true'}
        headers = headers_options if folder else desktop_headers_options

        async with aiohttp.ClientSession() as session:
            async with session.get('https://shimo.im/lizard-api/files', params=params_options, headers=headers) as response:
                data = await response.json()

        for item in data:
            await asyncio.sleep(config['Sleep'])
            atime = time.mktime(datetime.strptime(item['updatedAt'], "%Y-%m-%dT%H:%M:%S.%fZ").timetuple())

            if atime > config['Lasttime']:
                print(item['name'], item['type'], item['updatedAt'])

                if item['is_folder'] != 1:
                    res = -1
                    for j in range(config['Retry'] + 1):
                        if j > 0:
                            print(f"retry {j} times...")
                            await asyncio.sleep(config['Sleep'] * 2)

                        res = await create_export_task(item, base_path)
                        if res in [0, 1]:
                            break

                    if res != 0:
                        print(f'[Error] Failed to export: {item["name"]}')
                    else:
                        folder_info.files_info[item['name']] = ShimoInfo(item['updatedAt'], False)
                else:
                    if config['Recursive']:
                        sub_folder_info = FolderInfo()
                        sub_folder_info.folder_info = ShimoInfo(item['updatedAt'], True)
                        folder_info.sub_folders[item['name']] = sub_folder_info
                        await get_file_list(sub_folder_info, item['guid'], os.path.join(base_path, item['name']))
            else:
                print('the end')
                return
    except Exception as error:
        print(f'[Error] {str(error)}')


async def create_export_task(item, base_path=''):
    try:
        file_type = ''
        name = replace_bad_char(item['name'])
        download_url = ''
        if item['type'] in ['docx', 'doc'] or item['name'].endswith('rtf') or item['type'] in ['pptx', 'ppt', 'pdf']:
            download_url = 'https://shimo.im/lizard-api/files/' + item['guid'] + '/download'
        else:
            if item['type'] in ['newdoc', 'document', 'modoc']:
                file_type = 'docx'
            elif item['type'] in ['sheet', 'mosheet', 'spreadsheet']:
                file_type = 'xlsx'
            elif item['type'] in ['slide', 'presentation']:
                file_type = 'pptx'
            elif item['type'] == 'mindmap':
                file_type = 'xmind'
            else:
                print(f'[Error] {item["name"]} has unsupported type: {item["type"]}')
                return 1

            url = 'https://shimo.im/lizard-api/files/' + item['guid'] + '/export'

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params={'type': file_type, 'file': item['guid'], 'returnJson': '1', 'name': name, 'isAsync': '0'}, headers=headers_options) as response:
                    data = await response.json()
                    download_url = data.get('redirectUrl', data['data'].get('downloadUrl'))

        if not download_url:
            print(f'[Error] {item["name"]} failed, error: ', data)
            return 2

        options = {
            'headers': headers_options
        }
        await download(download_url, base_path, options)
    except Exception as error:
        print(f'[Error] {item["name"]} failed, error: {str(error)}')
        return 3

    return 0


async def download(url, path, options):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=options['headers']) as response:
            if not os.path.exists(path):
                os.makedirs(path)
            filename = os.path.join(path, response.content_disposition.filename)
            with open(filename, 'wb') as f:
                while True:
                    chunk = await response.content.read(1024)
                    if not chunk:
                        break
                    f.write(chunk)


def replace_bad_char(file_name):
    # 去掉文件名中的无效字符,如 \ / : * ? " < > |
    file_name = re.sub(r"[\'\"\\\/\b\f\n\r\t]", '_', file_name)
    return file_name


if __name__ == "__main__":
    root_folder_info = FolderInfo()
    loop = asyncio.get_event_loop()
    export_path = os.path.join(config['Path'], 'Export')
    loop.run_until_complete(get_file_list(root_folder_info, config['Folder'], export_path))

    if os.path.exists(export_path):
        files_info_path = os.path.join(config['Path'], 'files_info.json')
        if os.path.exists(files_info_path):
            pre_folder_info = FolderInfo.from_json(files_info_path)
            root_folder_info.compare(pre_folder_info)
            root_folder_info.filter_empty_folders()

        root_folder_info.save_json(files_info_path)
        shutil.copyfile(files_info_path, os.path.join(export_path, 'files_info.json'))
        with open(os.path.join(export_path, 'diff.log'), 'w', encoding='utf-8') as f:
            root_folder_info.print_diff(f)

        today = str(date.today()).replace('-', '')
        today_dir = os.path.join(config['Path'], today)
        if os.path.exists(today_dir):
            i = 1
            while os.path.exists(today_dir + f'_{i}'):
                i += 1
            today_dir = today_dir + f'_{i}'
        shutil.move(export_path, today_dir)
        print(f'[Done] Exported to {today_dir}')
