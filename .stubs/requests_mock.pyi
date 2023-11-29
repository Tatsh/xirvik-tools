from typing import Any
from collections.abc import Callable, Mapping

class Request:
    text: str | None


class Matcher:
    called_once: bool
    last_request: Request | None


class Mocker:
    def __call__(self, f: Callable[..., Any]) -> Callable[..., Any]:
        ...

    def register_uri(self, method: str, url: str, responses: list[Any]) -> Matcher:
        ...

    def post(self,
             url: str,
             json: Any = ...,
             status_code: int | None = ...,
             headers: Mapping[str, str] | None = ...) -> Matcher:
        ...

    def get(self,
            url: str,
            headers: Mapping[str, str] | None = ...,
            status_code: int | None = ...,
            text: str | None = ...) -> Matcher:
        ...
