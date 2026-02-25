import unittest

from aligo.cli import _resolve_sync_remote_folder


class FakeFolder:
    def __init__(self, file_id, name, file_type="folder"):
        self.file_id = file_id
        self.name = name
        self.type = file_type


class FakeAli:
    def __init__(self):
        self._seq = 0
        self.children = {"root": []}
        self.created = []

    def _new_id(self):
        self._seq += 1
        return f"id-{self._seq}"

    def add_folder(self, parent_file_id, name, file_id=None):
        if file_id is None:
            file_id = self._new_id()
        folder = FakeFolder(file_id=file_id, name=name)
        self.children.setdefault(parent_file_id, []).append(folder)
        self.children.setdefault(file_id, [])
        return folder

    def get_file(self, file_id, drive_id=None):
        if file_id == "root":
            return FakeFolder(file_id="root", name="/", file_type="folder")
        for folders in self.children.values():
            for folder in folders:
                if folder.file_id == file_id:
                    return folder
        raise FileNotFoundError(file_id)

    def get_file_list(self, parent_file_id, drive_id=None, type=None):
        if type != "folder":
            raise AssertionError("test double only supports folder listing")
        return list(self.children.get(parent_file_id, []))

    def create_folder(self, name, parent_file_id="root", drive_id=None, check_name_mode="auto_rename"):
        existing = [f for f in self.children.get(parent_file_id, []) if f.name == name]
        if existing and check_name_mode == "refuse":
            raise RuntimeError(f"already exists: {name}")
        folder = self.add_folder(parent_file_id=parent_file_id, name=name)
        self.created.append((parent_file_id, name, check_name_mode))
        return folder


class SyncResolverTests(unittest.TestCase):
    def test_reuses_exact_existing_folder(self):
        ali = FakeAli()
        exact = ali.add_folder("root", "vocabulary", file_id="folder-vocabulary")
        ali.add_folder("root", "vocabulary(1)", file_id="folder-vocabulary-1")

        resolved = _resolve_sync_remote_folder(ali, "/vocabulary")

        self.assertEqual(resolved.file_id, exact.file_id)
        self.assertEqual(ali.created, [])

    def test_creates_missing_nested_path_without_auto_rename(self):
        ali = FakeAli()

        resolved = _resolve_sync_remote_folder(ali, "/backup/vocabulary")

        self.assertEqual(resolved.name, "vocabulary")
        self.assertEqual(len(ali.created), 2)
        self.assertEqual(ali.created[0], ("root", "backup", "refuse"))
        self.assertEqual(ali.created[1][1], "vocabulary")
        self.assertEqual(ali.created[1][2], "refuse")

    def test_fails_when_only_auto_renamed_siblings_exist(self):
        ali = FakeAli()
        ali.add_folder("root", "vocabulary(1)")
        ali.add_folder("root", "vocabulary(2)")

        with self.assertRaises(RuntimeError) as ctx:
            _resolve_sync_remote_folder(ali, "/vocabulary")

        message = str(ctx.exception)
        self.assertIn("ambiguous", message)
        self.assertIn("vocabulary(1)", message)
        self.assertIn("vocabulary(2)", message)


if __name__ == "__main__":
    unittest.main()
