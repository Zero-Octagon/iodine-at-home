import os
import hashlib
from pathlib import Path
from core.types import FileObject
from core.logger import logger

# 从 GitHub 仓库获取最新版本，并下载到 files 目录下
class Upstream:
    # 接收 url、directory 等参数
    def __init__(self, url, directory: Path):
        self.url = url
        self.directory = directory

    # 下载文件
    def fetch(self) -> None:
        logger.info(f"正在同步 {self.url} 仓库内文件")
        # 检查目录是否存在，不存在则创建
        try:
            if not os.path.exists(self.directory):
                os.makedirs(self.directory)
                # 下载文件
                result = os.system(f"git clone {self.url} {self.directory}")
            else:
                current_dir = os.getcwd()
                os.chdir(self.directory)
                result = os.system("git pull")
                os.chdir(current_dir)
            logger.success(f"仓库 {self.url} 文件同步完成")
            return result
        except Exception as e:
            ... # 记录异常信息
            logger.error(e)
            return -1
        
    def get_file_list(self) -> list[FileObject]:
        return Upstream.iterate_directory(self.directory, self.directory)

    @staticmethod
    def iterate_directory(root : str, subroot : str) -> list[FileObject]:
        file_list = []
        for current, directories, files in os.walk(subroot):
            
            directories[:] = [d for d in directories if not d.startswith('.')]

            for directory in directories:
                file_list += Upstream.iterate_directory(root, os.path.join(current, directory))
            for file in files:
                path = os.path.join(current, file)[len(root):]
                path = path.replace("\\", "/")
                path = path if path.startswith("/") else ("/" + path)
                file = FileObject(os.path.join(current, file))
                file.path = path
                file_list.append(file)
        return file_list

# def main():
#     upstream = Upstream('https://github.com/Mxmilu666/bangbang93HUB', 'files')
#     upstream.fetch()
#     files = upstream.get_file_list()
#     for file in files:
#         print(file)

# if __name__ == '__main__':
#     main()