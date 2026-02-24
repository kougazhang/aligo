from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


def _load_local_package(package_name: str, init_file: Path) -> None:
    if package_name in sys.modules:
        return
    spec = spec_from_file_location(
        package_name,
        str(init_file),
        submodule_search_locations=[str(init_file.parent)],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load local package: {package_name}")
    module = module_from_spec(spec)
    sys.modules[package_name] = module
    spec.loader.exec_module(module)


def use_project_packages() -> None:
    project_root = Path(__file__).resolve().parents[1]
    _load_local_package("datclass", project_root / "src" / "datclass" / "__init__.py")
    _load_local_package("aligo", project_root / "src" / "aligo" / "__init__.py")
