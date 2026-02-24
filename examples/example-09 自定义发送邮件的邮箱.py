from _project_imports import use_project_packages
use_project_packages()

from aligo import Aligo, EMailConfig

if __name__ == '__main__':
    email_config = EMailConfig(
        email='',
        # 自配邮箱
        user='',
        password='',
        host='',
        port=0,
    )
    ali = Aligo(email=email_config)
