from argparse import ArgumentParser
from asyncio import Runner
from dataclasses import dataclass
from pathlib import Path
from shutil import copy, rmtree

from demo import UIBasedPlatform


@dataclass
class ScriptArgs:
    preset: str = ""
    override_config: bool = False

    debug_server: bool = False
    log_server_info: bool = False

    ui_host: str = "0.0.0.0"
    ui_port: int = 58000


if __name__ in {"__main__", "__mp_main__"}:
    arg_parser = ArgumentParser(description="Debatrix UI demo (singleton application)")

    arg_parser.add_argument("preset", help="select debate & config preset")

    arg_parser.add_argument(
        "-o",
        "--override-config",
        action="store_true",
        help="override current config with preset ones",
    )

    arg_parser.add_argument(
        "-v", "--debug-server", action="store_true", help="enable FastAPI & NiceGUI debug mode"
    )

    arg_parser.add_argument(
        "-l", "--log-server-info", action="store_true", help="display FastAPI info log"
    )

    arg_parser.add_argument("-i", "--ui-host", default="0.0.0.0", help="set UI demo host")
    arg_parser.add_argument("-p", "--ui-port", default=58000, type=int, help="set UI demo port")

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
        UIBasedPlatform(
            Path("resource"),
            fast_api_debug=args.debug_server,
            fast_api_log_info=args.log_server_info,
            ui_host=args.ui_host,
            ui_port=args.ui_port,
        ).serve()
    )

    print("Cleaning up ...")
    for target in ("motion", "speech"):
        (resource_path / target).unlink()
