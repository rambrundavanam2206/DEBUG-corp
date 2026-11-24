from starlette.responses import JSONResponse


class BodyLimit:
    """Bound JSON before parsing; ZIP is streamed and bounded by its authenticated route."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] != "http"
            or scope["method"] not in ("POST", "PATCH")
            or scope["path"].endswith("/import")
        ):
            return await self.app(scope, receive, send)
        messages, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > 180000:
                return await JSONResponse(
                    {"error": {"message": "Request exceeds input limit."}}, status_code=413
                )(scope, receive, send)
            messages.append(message)
            if not message.get("more_body"):
                break

        async def replay():
            return messages.pop(0) if messages else await receive()

        await self.app(scope, replay, send)
