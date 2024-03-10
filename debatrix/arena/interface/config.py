from pydantic.dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class ArenaInterfaceConfig:
    streaming_delay: float
    streaming_chunk_size: int
