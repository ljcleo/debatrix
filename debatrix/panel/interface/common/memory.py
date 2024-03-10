import enum
from asyncio import Lock
from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
from langchain.text_splitter import RecursiveCharacterTextSplitter

from ....core.common import Speech
from ....model import ModelClient


@enum.unique
class MemoryType(enum.StrEnum):
    SPEECH = enum.auto()
    ANALYSIS = enum.auto()


@dataclass(kw_only=True)
class MemoryChunk:
    type: MemoryType
    source: str
    content: str

    def as_pair(self, *, format_source: bool = False) -> tuple[str, str]:
        source: str = self.source

        if format_source:
            if self.type == MemoryType.ANALYSIS:
                source = f"Your Analysis of {source}"

        return source, self.content


class Memory:
    def __init__(self, *, model: ModelClient) -> None:
        self._splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=128)
        self._model = model

    async def reset(self) -> None:
        self._memory: list[MemoryChunk] = []
        self._embedding_matrix: np.ndarray | None = None

        self._buffer: list[MemoryChunk] = []
        self._buffer_lock = Lock()

    async def add_speech(self, speech: Speech, /, *, source: str, cut: bool = True) -> None:
        if cut:
            self._buffer.extend(
                [
                    MemoryChunk(type=MemoryType.SPEECH, source=source, content=doc.page_content)
                    for doc in self._splitter.create_documents([speech.content])
                ]
            )
        else:
            self._buffer.append(
                MemoryChunk(type=MemoryType.SPEECH, source=source, content=speech.content)
            )

    async def add_analyses(self, analyses: list[str], /, *, source: str) -> None:
        self._buffer.extend(
            [
                MemoryChunk(type=MemoryType.ANALYSIS, source=source, content=reflection)
                for reflection in analyses
            ]
        )

    def fetch(
        self,
        *,
        include_types: MemoryType | Iterable[MemoryType] | None = None,
        include_sources: str | Iterable[str] | None = None,
        exclude_sources: str | Iterable[str] | None = None,
        format_source: bool = False,
    ) -> list[tuple[str, str]]:
        result: list[MemoryChunk] = self._memory + self._buffer

        if include_types is not None:
            type_set: set[MemoryType] = (
                {include_types} if isinstance(include_types, MemoryType) else set(include_types)
            )

            result = [chunk for chunk in result if chunk.type in type_set]

        if include_sources is not None:
            source_set: set[str] = (
                {include_sources} if isinstance(include_sources, str) else set(include_sources)
            )

            result = [chunk for chunk in result if chunk.source in source_set]

        if exclude_sources is not None:
            source_set: set[str] = (
                {exclude_sources} if isinstance(exclude_sources, str) else set(exclude_sources)
            )

            result = [chunk for chunk in result if chunk.source not in source_set]

        return [chunk.as_pair(format_source=format_source) for chunk in result]

    async def query(
        self,
        query: str | list[str],
        /,
        *,
        k: int | None = None,
        include_types: MemoryType | Iterable[MemoryType] | None = None,
        include_sources: str | Iterable[str] | None = None,
        exclude_sources: str | Iterable[str] | None = None,
        format_source: bool = False,
    ) -> list[tuple[str, str]]:
        if isinstance(query, str):
            query = [query]

        assert len(query) > 0

        if len(self._buffer) > 0:
            async with self._buffer_lock:
                if len(self._buffer) > 0:
                    self._memory.extend(self._buffer)

                    embeddings: np.ndarray = await self._embed_many(
                        ["\n\n".join(chunk.as_pair(format_source=True)) for chunk in self._buffer]
                    )

                    if self._embedding_matrix is None:
                        self._embedding_matrix = embeddings
                    else:
                        self._embedding_matrix = np.concatenate(
                            [self._embedding_matrix, embeddings], axis=0
                        )

                    self._buffer.clear()

        result_index: list[int] = list(range(len(self._memory)))

        if include_types is not None:
            type_set: set[MemoryType] = (
                {include_types} if isinstance(include_types, MemoryType) else set(include_types)
            )

            result_index = [index for index in result_index if self._memory[index].type in type_set]

        if include_sources is not None:
            source_set: set[str] = (
                {include_sources} if isinstance(include_sources, str) else set(include_sources)
            )

            result_index = [
                index for index in result_index if self._memory[index].source in source_set
            ]

        if exclude_sources is not None:
            source_set: set[str] = (
                {exclude_sources} if isinstance(exclude_sources, str) else set(exclude_sources)
            )

            result_index = [
                index for index in result_index if self._memory[index].source not in source_set
            ]

        if len(result_index) == 0 or self._embedding_matrix is None:
            return []

        qe: np.ndarray = await self._embed_many(query)
        ve: np.ndarray = self._embedding_matrix[result_index, :]
        sim: np.ndarray = np.max(ve @ qe.T, axis=1)
        result_index = [result_index[i] for i in np.argsort(-sim)]

        if k is not None:
            result_index = result_index[:k]

        result_index.sort()
        return [self._memory[index].as_pair(format_source=format_source) for index in result_index]

    async def _embed_one(self, text: str) -> np.ndarray:
        return self._normalize(np.array(await self._model.embed_one(text)))

    async def _embed_many(self, texts: Iterable[str]) -> np.ndarray:
        embeddings: np.ndarray = np.array(await self._model.embed_many(texts))
        embeddings /= np.linalg.norm(embeddings, axis=1, keepdims=True)
        return embeddings

    @staticmethod
    def _normalize(x: np.ndarray) -> np.ndarray:
        v: np.floating = np.linalg.norm(x)
        return x if np.abs(v) < 1e-8 else x / v
