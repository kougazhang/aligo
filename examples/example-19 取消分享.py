from _project_imports import use_project_packages
use_project_packages()

from aligo import Aligo

if __name__ == '__main__':
    ali = Aligo()
    ali.cancel_share('<share_id>')
