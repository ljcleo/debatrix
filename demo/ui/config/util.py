from collections.abc import Callable

VALIDATIONS: dict[str, Callable[[str], bool]] = {"Cannot be empty": lambda v: len(v) > 0}
