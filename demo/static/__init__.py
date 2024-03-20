from base64 import b64encode
from importlib.resources import files

from . import img


def load_img_base64(fn: str) -> str:
    return b64encode(files(img).joinpath(fn).read_bytes()).decode("utf-8")
