from typing import Any, Callable, Mapping, Optional


class Mocker:
    def __call__(self, f: Callable[..., Any]) -> Callable[..., Any]:
        ...

    def post(self,
             url: str,
             json: Optional[Any] = ...,
             status_code: Optional[int] = ...,
             headers: Optional[Mapping[str, str]] = ...) -> None:
        ...

    def get(self,
            url: str,
            headers: Optional[Mapping[str, str]] = ...) -> None:
        ...
