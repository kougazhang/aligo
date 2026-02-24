import os
import sys

# Must run before importing argparse/re/enum to avoid stdlib `types` shadowing
# when executed as: python src/aligo/cli.py
if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(script_dir)
    if script_dir in sys.path:
        sys.path.remove(script_dir)
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

import argparse
import json
import logging
from typing import Optional, Tuple

from aligo import Aligo, EMailConfig, __version__, logout


def _normalize_remote_path(path: str) -> str:
    value = (path or "/").strip()
    if "://" in value:
        raise ValueError(f"unsupported remote path format: {value!r}; use filepath-like path such as '/tasks'")
    if ":" in value and not value.startswith("/"):
        raise ValueError(f"unsupported remote path format: {value!r}; use filepath-like path such as 'tasks'")
    if not value.startswith("/"):
        value = f"/{value}"
    return value


def _build_client(args: argparse.Namespace) -> Aligo:
    level = logging.DEBUG if args.debug else logging.INFO
    email = None
    if getattr(args, "email_to", None):
        email = EMailConfig(
            email=args.email_to,
            user=args.email_user,
            password=args.email_password,
            host=args.email_host,
            port=args.email_port,
            content=args.email_content or "",
        )
    return Aligo(
        name=args.profile,
        refresh_token=args.refresh_token,
        level=level,
        port=getattr(args, "port", None),
        email=email,
        re_login=not args.no_relogin,
    )


def _resolve_remote_file(ali: Aligo, remote_path: str, drive_id: str = None):
    path = _normalize_remote_path(remote_path)
    if path == "/":
        return ali.get_file("root", drive_id=drive_id)
    file_obj = ali.get_file_by_path(path, drive_id=drive_id)
    if file_obj is None:
        # `get_file_by_path` only searches type='file'. Fallback to folder path.
        file_obj = ali.get_folder_by_path(path, drive_id=drive_id, create_folder=False)
    if file_obj is None:
        raise FileNotFoundError(f"remote path not found: {path}")
    return file_obj


def _resolve_remote_folder(ali: Aligo, remote_path: str, drive_id: str = None, create: bool = False):
    path = _normalize_remote_path(remote_path)
    if path == "/":
        return ali.get_file("root", drive_id=drive_id)
    folder = ali.get_folder_by_path(path, drive_id=drive_id, create_folder=create, check_name_mode="auto_rename")
    if folder is None:
        raise FileNotFoundError(f"remote folder not found: {path}")
    if folder.type != "folder":
        raise NotADirectoryError(f"remote path is not folder: {path}")
    return folder


def _resolve_target_parent_and_name(
        ali: Aligo, destination: str, drive_id: str = None
) -> Tuple[str, Optional[str]]:
    dst = _normalize_remote_path(destination)
    if dst == "/":
        return "root", None

    if destination.endswith("/"):
        folder = _resolve_remote_folder(ali, dst, drive_id=drive_id, create=True)
        return folder.file_id, None

    maybe_folder = ali.get_folder_by_path(dst, drive_id=drive_id, create_folder=False)
    if maybe_folder and maybe_folder.type == "folder":
        return maybe_folder.file_id, None

    parent_path, new_name = os.path.split(dst.rstrip("/"))
    parent = _resolve_remote_folder(ali, parent_path or "/", drive_id=drive_id, create=True)
    return parent.file_id, new_name or None


def _serialize(data):
    if isinstance(data, list):
        return [_serialize(item) for item in data]
    if isinstance(data, dict):
        return {k: _serialize(v) for k, v in data.items()}
    to_dict = getattr(data, "to_dict", None)
    if callable(to_dict):
        return _serialize(to_dict())
    return data


def _print_json(data):
    print(json.dumps(_serialize(data), ensure_ascii=False, indent=2))


def _cmd_login(args: argparse.Namespace) -> int:
    ali = _build_client(args)
    user = ali.get_user()
    if args.json:
        _print_json(user.to_dict())
    else:
        print(f"login ok: {user.nick_name or user.user_name} ({user.user_id})")
    return 0


def _cmd_logout(args: argparse.Namespace) -> int:
    try:
        logout(args.profile)
    except FileNotFoundError:
        if args.json:
            _print_json({"ok": True, "profile": args.profile, "message": "already logged out"})
        else:
            print(f"already logged out: {args.profile}")
        return 0
    if args.json:
        _print_json({"ok": True, "profile": args.profile})
    else:
        print(f"logout ok: {args.profile}")
    return 0


def _cmd_info(args: argparse.Namespace) -> int:
    ali = _build_client(args)
    user = ali.get_user()
    info = ali.get_personal_info()
    if args.json:
        _print_json(
            {
                "user": user.to_dict(),
                "personal_info": info.to_dict(),
                "default_drive_id": ali.default_drive_id,
            }
        )
    else:
        print(f"user: {user.nick_name or user.user_name} ({user.user_id})")
        print(f"default_drive_id: {ali.default_drive_id}")
    return 0


def _cmd_ls(args: argparse.Namespace) -> int:
    ali = _build_client(args)
    target = _resolve_remote_file(ali, args.path, drive_id=args.drive_id)
    files = [target] if target.type != "folder" else ali.get_file_list(parent_file_id=target.file_id, drive_id=args.drive_id)
    if args.json:
        _print_json([item.to_dict() for item in files])
        return 0

    for item in files:
        if args.long:
            print(f"{item.type:6} {str(item.size or 0):>12} {item.updated_at or '-':24} {item.name}")
        else:
            print(item.name)
    return 0


def _cmd_mb(args: argparse.Namespace) -> int:
    ali = _build_client(args)
    folder = _resolve_remote_folder(ali, args.path, drive_id=args.drive_id, create=True)
    if args.json:
        _print_json(folder.to_dict())
    else:
        print(folder.file_id)
    return 0


def _cmd_put(args: argparse.Namespace) -> int:
    ali = _build_client(args)
    local_path = os.path.abspath(args.local_path)
    if not os.path.exists(local_path):
        raise FileNotFoundError(local_path)
    destination = args.remote_path or "/"
    parent_folder = _resolve_remote_folder(ali, destination, drive_id=args.drive_id, create=True)

    if os.path.isdir(local_path):
        result = ali.upload_folder(local_path, parent_file_id=parent_folder.file_id, drive_id=args.drive_id)
    else:
        result = ali.upload_file(
            local_path,
            parent_file_id=parent_folder.file_id,
            drive_id=args.drive_id,
            check_name_mode=args.check_name_mode,
        )
    if args.json:
        _print_json(result)
    else:
        print("upload done")
    return 0


def _cmd_get(args: argparse.Namespace) -> int:
    ali = _build_client(args)
    remote = _resolve_remote_file(ali, args.remote_path, drive_id=args.drive_id)
    local_dir = os.path.abspath(args.local_path or ".")
    os.makedirs(local_dir, exist_ok=True)
    if remote.type == "folder":
        out = ali.download_folder(remote.file_id, local_folder=local_dir, drive_id=args.drive_id)
    else:
        out = ali.download_file(file=remote, local_folder=local_dir)
    if args.json:
        _print_json({"output": out})
    else:
        print(out)
    return 0


def _cmd_rm(args: argparse.Namespace) -> int:
    ali = _build_client(args)
    target = _resolve_remote_file(ali, args.path, drive_id=args.drive_id)
    result = ali.move_file_to_trash(target.file_id, drive_id=args.drive_id)
    if args.json:
        _print_json(result.to_dict())
    else:
        print(f"moved to trash: {target.name}")
    return 0


def _cmd_cp(args: argparse.Namespace) -> int:
    ali = _build_client(args)
    src = _resolve_remote_file(ali, args.source, drive_id=args.drive_id)
    to_parent_file_id, new_name = _resolve_target_parent_and_name(ali, args.destination, drive_id=args.drive_id)
    result = ali.copy_file(
        src.file_id,
        to_parent_file_id=to_parent_file_id,
        new_name=new_name,
        drive_id=args.drive_id,
    )
    if args.json:
        _print_json(result.to_dict())
    else:
        print(result.file_id)
    return 0


def _cmd_mv(args: argparse.Namespace) -> int:
    ali = _build_client(args)
    src = _resolve_remote_file(ali, args.source, drive_id=args.drive_id)
    to_parent_file_id, new_name = _resolve_target_parent_and_name(ali, args.destination, drive_id=args.drive_id)
    result = ali.move_file(
        src.file_id,
        to_parent_file_id=to_parent_file_id,
        new_name=new_name,
        drive_id=args.drive_id,
    )
    if args.json:
        _print_json(result.to_dict())
    else:
        print(result.file_id)
    return 0


def _cmd_sync(args: argparse.Namespace) -> int:
    ali = _build_client(args)
    remote_folder = _resolve_remote_folder(ali, args.remote_path, drive_id=args.drive_id, create=True)

    flag = None
    if args.mode == "local":
        flag = True
    elif args.mode == "remote":
        flag = False

    ali.sync_folder(
        local_folder=os.path.abspath(args.local_path),
        remote_folder=remote_folder.file_id,
        flag=flag,
        ignore_content=args.ignore_content,
        follow_delete=args.follow_delete,
        drive_id=args.drive_id,
    )
    if not args.json:
        print("sync done")
    return 0


def _add_common_flags(parser: argparse.ArgumentParser):
    parser.add_argument("--profile", default="aligo", help="config profile name")
    parser.add_argument("--drive-id", default=None, help="target drive id")
    parser.add_argument("--refresh-token", default=None, help="use explicit refresh token")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    parser.add_argument("--json", action="store_true", help="json output")
    parser.add_argument("--no-relogin", action="store_true", help="disable relogin when token expired")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aligo", description="Aliyun Drive CLI (s3cmd-like)")
    parser.add_argument("-v", "--version", action="version", version=f"aligo {__version__}")

    sub = parser.add_subparsers(dest="command")
    try:
        sub.required = True  # Python >= 3.7
    except AttributeError:
        pass

    p_login = sub.add_parser("login", help="login and persist token")
    _add_common_flags(p_login)
    p_login.add_argument("--port", type=int, default=None, help="web login port")
    p_login.add_argument("--email-to", default=None, help="send login qrcode to email")
    p_login.add_argument("--email-user", default=None, help="smtp user")
    p_login.add_argument("--email-password", default=None, help="smtp password")
    p_login.add_argument("--email-host", default=None, help="smtp host")
    p_login.add_argument("--email-port", type=int, default=465, help="smtp port")
    p_login.add_argument("--email-content", default="", help="email extra content")
    p_login.set_defaults(func=_cmd_login)

    p_logout = sub.add_parser("logout", help="logout and remove local token")
    _add_common_flags(p_logout)
    p_logout.set_defaults(func=_cmd_logout)

    p_info = sub.add_parser("info", help="show account information")
    _add_common_flags(p_info)
    p_info.set_defaults(func=_cmd_info)

    p_ls = sub.add_parser("ls", help="list remote files")
    _add_common_flags(p_ls)
    p_ls.add_argument("path", nargs="?", default="/", help="remote path, e.g. /Movies")
    p_ls.add_argument("-l", "--long", action="store_true", help="long listing")
    p_ls.set_defaults(func=_cmd_ls)

    p_mb = sub.add_parser("mb", help="make remote folder path")
    _add_common_flags(p_mb)
    p_mb.add_argument("path", help="remote folder path")
    p_mb.set_defaults(func=_cmd_mb)

    p_put = sub.add_parser("put", help="upload local file/folder")
    _add_common_flags(p_put)
    p_put.add_argument("local_path", help="local path to upload")
    p_put.add_argument("remote_path", nargs="?", default="/", help="remote folder path")
    p_put.add_argument(
        "--check-name-mode",
        default="auto_rename",
        choices=["auto_rename", "refuse", "overwrite"],
        help="name conflict strategy",
    )
    p_put.set_defaults(func=_cmd_put)

    p_get = sub.add_parser("get", help="download remote file/folder")
    _add_common_flags(p_get)
    p_get.add_argument("remote_path", help="remote path to download")
    p_get.add_argument("local_path", nargs="?", default=".", help="local destination folder")
    p_get.set_defaults(func=_cmd_get)

    p_rm = sub.add_parser("rm", help="move remote file/folder to trash")
    _add_common_flags(p_rm)
    p_rm.add_argument("path", help="remote path")
    p_rm.set_defaults(func=_cmd_rm)

    p_cp = sub.add_parser("cp", help="copy remote file/folder")
    _add_common_flags(p_cp)
    p_cp.add_argument("source", help="source remote path")
    p_cp.add_argument("destination", help="destination remote path or folder")
    p_cp.set_defaults(func=_cmd_cp)

    p_mv = sub.add_parser("mv", help="move remote file/folder")
    _add_common_flags(p_mv)
    p_mv.add_argument("source", help="source remote path")
    p_mv.add_argument("destination", help="destination remote path or folder")
    p_mv.set_defaults(func=_cmd_mv)

    p_sync = sub.add_parser("sync", help="sync local folder with remote folder")
    _add_common_flags(p_sync)
    p_sync.add_argument("local_path", help="local folder path")
    p_sync.add_argument("remote_path", help="remote folder path")
    p_sync.add_argument(
        "--mode",
        choices=["both", "local", "remote"],
        default="both",
        help="sync mode: both/local/remote",
    )
    p_sync.add_argument("--ignore-content", action="store_true", help="ignore content hash compare")
    p_sync.add_argument("--follow-delete", action="store_true", help="follow delete operations")
    p_sync.set_defaults(func=_cmd_sync)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("cancelled", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        if getattr(args, "debug", False):
            raise
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
