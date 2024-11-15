import time
from typing import Annotated, Optional
from fastapi import APIRouter, Header, Request, Response
import io

from httppubsubserver.middleware.config import get_config_from_request


router = APIRouter()


@router.post(
    "/v1/unsubscribe",
    status_code=202,
    responses={
        "400": {"description": "The body was not formatted correctly"},
        "401": {"description": "Authorization header is required but not provided"},
        "403": {"description": "Authorization header is provided but invalid"},
        "409": {"description": "The subscription does not exist"},
        "500": {"description": "Unexpected error occurred"},
        "503": {"description": "Service is unavailable, try again soon"},
    },
)
async def unsubscribe(
    request: Request, authorization: Annotated[Optional[str], Header()] = None
):
    """Unsubscribes the given URL from the given pattern. The body should be
    formatted as the following sequence:

    - 2 bytes: the length of the url, big-endian, unsigned
    - N bytes: the url. must be valid utf-8
    - 1 byte: either 0 or 1 (big-endian, unsigned) to indicate an exact match
      (0) or glob-style match (1).
    - 2 bytes: the length of the pattern or exact match.
    - M bytes: the pattern or exact match. if glob-style, must be utf-8,
      otherwise unrestricted

    The response has an arbitrary body (generally empty) and one of the
    following status codes:

    - 200 Okay: the subscription was removed
    - 400 Bad Request: the body was not formatted correctly
    - 401 Unauthorized: authorization is required but not provided
    - 403 Forbidden: authorization is provided but invalid
    - 409 Conflict: the subscription already exists
    - 500 Internal Server Error: unexpected error occurred
    - 503 Service Unavailable: servce (generally, database) is unavailable
    """
    config = get_config_from_request(request)

    body = await request.body()
    if len(body) < 5 or len(body) > 2 + 65535 + 1 + 2 + 65535:
        return Response(status_code=400)

    body_io = io.BytesIO(body)
    url_len = int.from_bytes(body_io.read(2), "big", signed=False)
    url_bytes = body_io.read(url_len)

    try:
        url = url_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return Response(status_code=400)

    match_type = int.from_bytes(body_io.read(1), "big", signed=False)
    if match_type not in (0, 1):
        return Response(status_code=400)

    is_exact = match_type == 0

    pattern_len = int.from_bytes(body_io.read(2), "big", signed=False)
    pattern_bytes = body_io.read(pattern_len)

    if is_exact:
        pattern = None
        exact = pattern_bytes
    else:
        try:
            pattern = pattern_bytes.decode("utf-8", errors="strict")
            exact = None
        except:
            return Response(status_code=400)

    auth_at = time.time()
    if exact is not None:
        auth_result = await config.is_subscribe_exact_allowed(
            url=url, exact=exact, now=auth_at, authorization=authorization
        )
    elif pattern is not None:
        auth_result = await config.is_subscribe_glob_allowed(
            url=url, glob=pattern, now=auth_at, authorization=authorization
        )
    else:
        raise AssertionError("unreachable")

    if auth_result == "unauthorized":
        return Response(status_code=401)
    elif auth_result == "forbidden":
        return Response(status_code=403)
    elif auth_result == "unavailable":
        return Response(status_code=503)
    elif auth_result != "ok":
        return Response(status_code=500)

    if exact is not None:
        db_result = await config.unsubscribe_exact(url=url, exact=exact)
    elif pattern is not None:
        db_result = await config.unsubscribe_glob(url=url, glob=pattern)
    else:
        raise AssertionError("unreachable")

    if db_result == "conflict":
        return Response(status_code=409)
    elif db_result == "unavailable":
        return Response(status_code=503)
    elif db_result != "ok":
        return Response(status_code=500)

    return Response(status_code=200)
