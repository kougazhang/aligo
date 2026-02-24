from _project_imports import use_project_packages
use_project_packages()

from aligo import Aligo

if __name__ == '__main__':
    ali = Aligo()
    for i in ali.list_to_clean(ali.album_info.drive_id, 30):
        print(i)
