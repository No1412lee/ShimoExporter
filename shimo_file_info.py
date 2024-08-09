import json
from enum import Enum


class ShimoStatus(Enum):
    NEW = 0
    SAME = 1
    UPDATE = 2
    DELETE = 3

    def __str__(self):
        return self.name


class ShimoInfo:
    def __init__(self, updated_time:str, is_folder:bool, status:str=str(ShimoStatus.NEW)):
        self.updated_time = updated_time
        self.is_folder = is_folder
        self.status = ShimoStatus[status]

    def to_dict(self):
        return {
            'updated_time': self.updated_time,
            'is_folder': self.is_folder,
            'status': self.status.name,
        }

    def to_json(self):
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    def compare(self, pre_folder_info: 'ShimoInfo'):
        if self.updated_time != pre_folder_info.updated_time:
            self.status = ShimoStatus.UPDATE
        else:
            self.status = ShimoStatus.SAME


class FolderInfo:
    def __init__(self, folder_info:dict = None):
        if folder_info is None:
            self.folder_info = ShimoInfo('', True)
            self.sub_folders = {}
            self.files_info = {}
        else:
            self.folder_info = ShimoInfo(**folder_info['folder_info'])
            self.sub_folders = {k: FolderInfo(v) for k, v in folder_info['sub_folders'].items()}
            self.files_info = {k: ShimoInfo(**v) for k, v in folder_info['files_info'].items()}

    def to_dict(self):
        return {
            'folder_info': self.folder_info.to_dict(),
            'sub_folders': {k: v.to_dict() for k, v in self.sub_folders.items()},
            'files_info': {k: v.to_dict() for k, v in self.files_info.items()},
        }

    def to_json(self):
        f = lambda o: int(o) if isinstance(o, ShimoStatus) else o.to_dict()
        return json.dumps(self.__dict__, default=f, ensure_ascii=False)

    def save_json(self, json_file:str):
        with open(json_file, 'w', encoding='utf-8') as f:
            f.write(self.to_json())

    @classmethod
    def from_json(cls, json_file:str):
        with open(json_file, 'r', encoding='utf-8') as f:
            json_str = f.read()
            json_dict = json.loads(json_str)
            return cls(json_dict)
        
    def compare(self, pre_folder_info: 'FolderInfo'):
        if self.folder_info.updated_time != pre_folder_info.folder_info.updated_time:
            self.folder_info.status = ShimoStatus.UPDATE
        else:
            self.folder_info.status = ShimoStatus.SAME

        for k, v in self.sub_folders.items():
            if k in pre_folder_info.sub_folders and pre_folder_info.sub_folders[k].folder_info.status != ShimoStatus.DELETE:
                self.sub_folders[k].compare(pre_folder_info.sub_folders[k])
        for k, v in pre_folder_info.sub_folders.items():
            if not k in self.sub_folders and v.folder_info.status != ShimoStatus.DELETE:
                sub_folder_info = FolderInfo()
                sub_folder_info.folder_info.updated_time = v.folder_info.updated_time
                sub_folder_info.folder_info.status = ShimoStatus.DELETE
                self.sub_folders[k] = sub_folder_info

        for k, v in self.files_info.items():
            if k in pre_folder_info.files_info and pre_folder_info.files_info[k].status != ShimoStatus.DELETE:
                self.files_info[k].compare(pre_folder_info.files_info[k])
        for k, v in pre_folder_info.files_info.items():
            if not k in self.files_info and v.status != ShimoStatus.DELETE:
                file_info = ShimoInfo(v.updated_time, False, str(ShimoStatus.DELETE))
                self.files_info[k] = file_info
    
    def filter_empty_folders(self):
        filter_k = []
        for k, v in self.sub_folders.items():
            if v.filter_empty_folders():
                filter_k.append(k)
        for k in filter_k:
            self.sub_folders.pop(k)
        if len(self.files_info) + len (self.sub_folders) == 0:
            return True
        return False

    def print_diff(self, log_file, depth:int=0):
        for k, v in sorted(self.sub_folders.items()):
            log_file.write(f'{" "*depth*2}{k} {v.folder_info.updated_time} {v.folder_info.status}\n')
            v.print_diff(log_file, depth + 1)

        for k, v in sorted(self.files_info.items()):
            log_file.write(f'{(" "*depth*2)}{k} {v.updated_time} {v.status}\n')
