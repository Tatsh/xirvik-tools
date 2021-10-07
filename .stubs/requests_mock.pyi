from typing import Any, Callable, Mapping, Optional


class Request:
    text: Optional[str]


class Matcher:
    called_once: bool
    last_request: Optional[Request]


class Mocker:
    def __call__(self, f: Callable[..., Any]) -> Callable[..., Any]:
        ...

    def post(self,
             url: str,
             json: Optional[Any] = ...,
             status_code: Optional[int] = ...,
             headers: Optional[Mapping[str, str]] = ...) -> Matcher:
        ...

    def get(self,
            url: str,
            headers: Optional[Mapping[str, str]] = ...,
            status_code: Optional[int] = ...,
            text: Optional[str] = ...) -> Matcher:
        ...
