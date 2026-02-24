from _project_imports import use_project_packages
use_project_packages()

from aligo import Aligo, BaseFile


def handle(path: str, f: BaseFile):
    print(path, f.file_id)


if __name__ == '__main__':
    ali = Aligo()
    ali.walk_files(handle)
