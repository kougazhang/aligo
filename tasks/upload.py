"""上传文件/文件夹到指定网盘目录/位置"""
from _project_imports import use_project_packages
use_project_packages()

from aligo import Aligo

if __name__ == '__main__':
    ali = Aligo()
    ali.upload_folder('/home/delyan/codes/aligo/tasks')
