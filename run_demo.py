from argparse import ArgumentParser
from asyncio import Runner
from dataclasses import dataclass
from pathlib import Path
from shutil import copy, rmtree

from demo import PlatformUI


@dataclass
class ScriptArgs:
    preset: str = ""
    override_config: bool = False

    debug_server: bool = False
    log_server_info: bool = False

    ui_host: str = "0.0.0.0"
    ui_port: int = 58000


if __name__ in {"__main__", "__mp_main__"}:
    arg_parser = ArgumentParser()
    arg_parser.add_argument("preset")
    arg_parser.add_argument("-o", "--override-config", action="store_true")
    arg_parser.add_argument("-v", "--debug-server", action="store_true")
    arg_parser.add_argument("-l", "--log-server-info", action="store_true")
    arg_parser.add_argument("-h", "--ui-host", default="0.0.0.0")
    arg_parser.add_argument("-p", "--ui-port", default=58000, type=int)
    args: ScriptArgs = arg_parser.parse_args(namespace=ScriptArgs())

    preset_path: Path = Path("./preset") / args.preset
    resource_path = Path("./resource")
    resource_path.mkdir(exist_ok=True)

    print(f"Loading preset {args.preset} ...")
    config_path: Path = resource_path / "config"
    config_path.mkdir(exist_ok=True)

    for file in (preset_path / "config").iterdir():
        if args.override_config or not (config_path / file.name).exists():
            copy(file, config_path)

    for target in ("motion", "speech"):
        target_path: Path = resource_path / target

        if target_path.exists():
            if target_path.is_symlink() or not target_path.is_dir():
                target_path.unlink()
            else:
                rmtree(target_path, ignore_errors=True)

        target_path.symlink_to((preset_path / target).absolute())

    Runner(debug=True).run(
        PlatformUI(
            Path("resource"),
            debug=args.debug_server,
            log_info=args.log_server_info,
            ui_host=args.ui_host,
            ui_port=args.ui_port,
        ).serve()
    )

    print("Cleaning up ...")
    for target in ("motion", "speech"):
        (resource_path / target).unlink()
