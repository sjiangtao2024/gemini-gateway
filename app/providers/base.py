from abc import ABC, abstractmethod
from typing import AsyncIterator, Union


class BaseProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def chat_completions(self, *args, **kwargs) -> Union[dict, AsyncIterator[dict]]:
        raise NotImplementedError

    @abstractmethod
    async def list_models(self) -> list[dict]:
        raise NotImplementedError
