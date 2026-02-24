"""福利码兑换示例"""

from _project_imports import use_project_packages
use_project_packages()

from aligo import Aligo

if __name__ == '__main__':
    ali = Aligo()
    ali.rewards_space('<福利码>')
