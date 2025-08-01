from argparse import ArgumentParser
from asyncio import Runner
from dataclasses import dataclass
from pathlib import Path
from shutil import copy, rmtree

from demo import UIBasedPlatform


@dataclass
class ScriptArgs:
    preset: str = ""
    secret: str = ""

    override_config: bool = False

    debug_server: bool = False
    log_server_info: bool = False

    ui_host: str = "0.0.0.0"
    ui_port: int = 58000

    enable_intro: bool = False
    enable_full_config_ui: bool = False


def main() -> None:
    arg_parser = ArgumentParser(description="Debatrix UI demo")

    arg_parser.add_argument("preset", help="select debate & config preset")
    arg_parser.add_argument("secret", help="NiceGUI storage secret seed")

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

    arg_parser.add_argument("-I", "--ui-host", default="0.0.0.0", help="set UI demo host")
    arg_parser.add_argument("-P", "--ui-port", default=58000, type=int, help="set UI demo port")
    arg_parser.add_argument("-i", "--enable-intro", action="store_true", help="enable intro dialog")

    arg_parser.add_argument(
        "-f", "--enable-full-config-ui", action="store_true", help="enable full config UI"
    )

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

    try:
        Runner(debug=True).run(
            UIBasedPlatform(
                Path("resource"),
                fast_api_debug=args.debug_server,
                fast_api_log_info=args.log_server_info,
                ui_host=args.ui_host,
                ui_port=args.ui_port,
                enable_intro=args.enable_intro,
                enable_full_config_ui=args.enable_full_config_ui,
                storage_secret=args.secret,
            ).serve()
        )
    except KeyboardInterrupt:
        pass
    finally:
        print("Cleaning up ...")
        for target in ("motion", "speech"):
            (resource_path / target).unlink()


if __name__ == "__main__":
    main()
