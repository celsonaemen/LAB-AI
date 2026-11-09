"""Authenticate the dedicated gateway before parsing any internal API body."""
import os
import secrets

from starlette.responses import JSONResponse


class ServiceAuthentication:
    def __init__(self, app):
        self.app = app
        self.enabled = os.getenv("AEGIS_SECURITY_ENABLED", "false").lower() == "true"
        self.token = os.getenv("AEGIS_SERVICE_TOKEN", "")
        environment = os.getenv("AEGIS_ENVIRONMENT", "Development")
        if not self.enabled and environment != "Development":
            raise RuntimeError("Service authentication is required outside Development")
        if self.enabled and (len(self.token) < 32 or not self.token.isascii() or any(ord(c) < 32 for c in self.token)):
            raise RuntimeError("Configure a service token of at least 32 ASCII characters")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not self.enabled:
            return await self.app(scope, receive, send)
        path = scope.get("path", "")
        if path == "/health":
            return await self.app(scope, receive, send)
        values = [value for key, value in scope.get("headers", []) if key.lower() == b"x-aegis-service-token"]
        if len(values) != 1 or not secrets.compare_digest(values[0], self.token.encode("ascii")):
            response = JSONResponse({"detail": "Unauthorized service"}, status_code=401,
                                    headers={"Cache-Control": "no-store"})
            return await response(scope, receive, send)
        return await self.app(scope, receive, send)
