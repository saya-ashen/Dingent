# server/core/middleware.py
import json

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class DebugRequestMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        print("--- Intercepted Request ---")
        print(f"Method: {request.method}")
        print(f"URL: {request.url}")
        print("Headers:")
        for name, value in request.headers.items():
            print(f"  {name}: {value}")

        body_bytes = await request.body()
        if body_bytes:
            try:
                body_json = json.loads(body_bytes)
                print("Body (JSON):")
                print(json.dumps(body_json, indent=2))
            except json.JSONDecodeError:
                print("Body (Raw Text):")
                print(body_bytes.decode(errors="ignore"))
        else:
            print("Body: (Empty)")
        print("--------------------------")

        # To debug, uncomment the following line in your dev environment

        response = await call_next(request)
        return response
