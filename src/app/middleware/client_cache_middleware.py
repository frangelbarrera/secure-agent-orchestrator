from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class ClientCacheMiddleware(BaseHTTPMiddleware):
    """Middleware that sets a conservative `Cache-Control` header on responses.

    Previous behavior set `Cache-Control: public, max-age=60` on every response,
    including authenticated ones. That is a cache-poisoning risk when a CDN or
    shared proxy is in front of the app: a response generated for one
    authenticated user could be served to another.

    The new behavior:

    - If the request carried an `Authorization` header (i.e. it was
      authenticated), the response is marked `private, no-store`.
    - If the response status is an error (>= 400), it is marked
      `private, no-store` as well, so failed auth attempts are not cached.
    - Otherwise the response keeps the `public, max-age=<n>` directive, which
      is safe for genuinely public, idempotent endpoints (health, public
      listings).

    Parameters
    ----------
    app: FastAPI
        The FastAPI application instance.
    max_age: int, optional
        Duration (in seconds) for which public responses may be cached.
        Defaults to 60 seconds.
    """

    def __init__(self, app: FastAPI, max_age: int = 60) -> None:
        super().__init__(app)
        self.max_age = max_age

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response: Response = await call_next(request)

        has_authorization = request.headers.get("Authorization") is not None
        is_error = response.status_code >= 400

        if has_authorization or is_error:
            response.headers["Cache-Control"] = "private, no-store"
        else:
            response.headers["Cache-Control"] = f"public, max-age={self.max_age}"

        return response
