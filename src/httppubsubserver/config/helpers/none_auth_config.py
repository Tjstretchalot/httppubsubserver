from typing import Literal, Optional, TYPE_CHECKING, Type

if TYPE_CHECKING:
    from httppubsubserver.config.auth_config import (
        IncomingAuthConfig,
        OutgoingAuthConfig,
    )


class IncomingNoneAuth:
    """Allows all incoming requests

    In order for this to be secure it must only be possible for trusted clients
    to connect to the server (e.g., by setting up TLS mutual auth at the binding
    level)
    """

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def is_subscribe_exact_allowed(
        self, /, *, url: str, exact: bytes, now: float, authorization: Optional[str]
    ) -> Literal["ok", "unauthorized", "forbidden", "unavailable"]:
        return "ok"

    async def is_subscribe_glob_allowed(
        self, /, *, url: str, glob: str, now: float, authorization: Optional[str]
    ) -> Literal["ok", "unauthorized", "forbidden", "unavailable"]:
        return "ok"

    async def is_notify_allowed(
        self,
        /,
        *,
        topic: bytes,
        message_sha512: bytes,
        now: float,
        authorization: Optional[str],
    ) -> Literal["ok", "unauthorized", "forbidden", "unavailable"]:
        return "ok"


class OutgoingNoneAuth:
    """Doesn't set any authorization header. In order for this to be secure, the
    subscribers must only be able to receive messages from trusted clients.
    """

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def setup_authorization(
        self, /, *, url: str, topic: bytes, message_sha512: bytes, now: float
    ) -> Optional[str]:
        return None


if TYPE_CHECKING:
    _: Type[IncomingAuthConfig] = IncomingNoneAuth
    __: Type[OutgoingAuthConfig] = OutgoingNoneAuth