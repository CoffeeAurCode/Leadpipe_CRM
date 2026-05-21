INFO:     49.43.26.105:0 - "POST /voice/call/outbound HTTP/1.1" 500 Internal Server Error
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/uvicorn/protocols/http/h11_impl.py", line 410, in run_asgi
    result = await app(  # type: ignore[func-returns-value]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        self.scope, self.receive, self.send
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/uvicorn/middleware/proxy_headers.py", line 60, in __call__
    return await self.app(scope, receive, send)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/applications.py", line 1135, in __call__
    await super().__call__(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/applications.py", line 107, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/middleware/errors.py", line 186, in __call__
    raise exc
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/middleware/errors.py", line 164, in __call__
    await self.app(scope, receive, _send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/middleware/cors.py", line 93, in __call__
    await self.simple_response(scope, receive, send, request_headers=headers)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/middleware/cors.py", line 144, in simple_response
    await self.app(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/middleware/exceptions.py", line 63, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/middleware/asyncexitstack.py", line 18, in __call__
    await self.app(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/routing.py", line 716, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/routing.py", line 736, in app
    await route.handle(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/routing.py", line 290, in handle
    await self.app(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 115, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 101, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 355, in app
    raw_response = await run_endpoint_function(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<3 lines>...
    )
    ^
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 243, in run_endpoint_function
    return await dependant.call(**values)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/backend/app/routes/voice.py", line 605, in make_outbound_call
    call = client.calls.create(
        assistant_id=assistant_id,
    ...<2 lines>...
        assistant_overrides=overrides,
    )
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/vapi/calls/client.py", line 265, in create
    _response = self._raw_client.create(
        customers=customers,
    ...<16 lines>...
        request_options=request_options,
    )
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/vapi/calls/raw_client.py", line 330, in create
    raise ApiError(status_code=_response.status_code, headers=dict(_response.headers), body=_response_json)
vapi.core.api_error.ApiError: headers: {'date': 'Thu, 21 May 2026 13:09:24 GMT', 'content-type': 'application/json; charset=utf-8', 'content-length': '228', 'connection': 'keep-alive', 'x-powered-by': 'Express', 'access-control-allow-origin': '*', 'content-security-policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; form-action 'self'; frame-ancestors 'self'; connect-src 'self' https:; worker-src 'self' blob:", 'x-robots-tag': 'noindex', 'etag': 'W/"e4-/uhLUiSU8+6ZBjzW3nXFaK27/pk"', 'cf-cache-status': 'DYNAMIC', 'set-cookie': '_cfuvid=ymY5ucndZ7Ju_gbqXu3ESNoJVH2FZVKVEXyh3Qiiy7s-1779368962.4123218-1.0.1.1-OCf1DbvR2Byj6Umyn5YB_7NxzO2fFbrmFv3c6RqZwpU; HttpOnly; SameSite=None; Secure; Path=/; Domain=vapi.ai', 'server': 'cloudflare', 'cf-ray': '9ff3d0af1c3ad6dd-IAD', 'alt-svc': 'h3=":443"; ma=86400'}, status_code: 400, body: {'statusCode': 400, 'message': "Couldn't start call. Free Vapi numbers do not support international calls.", 'error': 'Bad Request', 'subscriptionLimits': {'concurrencyBlocked': False, 'concurrencyLimit': 10, 'remainingConcurrentCalls': 9}}
INFO:     49.43.26.105:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.105:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.105:0 - "OPTIONS /complaints HTTP/1.1" 200 OK
INFO:     49.43.26.105:0 - "OPTIONS /appointments?start_date=2026-02-20&end_date=2026-06-20 HTTP/1.1" 200 OK
INFO:     49.43.26.105:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     49.43.26.105:0 - "GET /appointments?start_date=2026-02-20&end_date=2026-06-20 HTTP/1.1" 200 OK
INFO:     49.43.26.105:0 - "GET /complaints HTTP/1.1" 200 OK
INFO:     49.43.26.105:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.105:0 - "POST /voice/call/outbound HTTP/1.1" 500 Internal Server Error
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/uvicorn/protocols/http/h11_impl.py", line 410, in run_asgi
    result = await app(  # type: ignore[func-returns-value]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        self.scope, self.receive, self.send
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/uvicorn/middleware/proxy_headers.py", line 60, in __call__
    return await self.app(scope, receive, send)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/applications.py", line 1135, in __call__
    await super().__call__(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/applications.py", line 107, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/middleware/errors.py", line 186, in __call__
    raise exc
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/middleware/errors.py", line 164, in __call__
    await self.app(scope, receive, _send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/middleware/cors.py", line 93, in __call__
    await self.simple_response(scope, receive, send, request_headers=headers)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/middleware/cors.py", line 144, in simple_response
    await self.app(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/middleware/exceptions.py", line 63, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/middleware/asyncexitstack.py", line 18, in __call__
    await self.app(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/routing.py", line 716, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/routing.py", line 736, in app
    await route.handle(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/routing.py", line 290, in handle
    await self.app(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 115, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 101, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 355, in app
    raw_response = await run_endpoint_function(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<3 lines>...
    )
    ^
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 243, in run_endpoint_function
    return await dependant.call(**values)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/backend/app/routes/voice.py", line 605, in make_outbound_call
    call = client.calls.create(
        assistant_id=assistant_id,
    ...<2 lines>...
        assistant_overrides=overrides,
    )
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/vapi/calls/client.py", line 265, in create
    _response = self._raw_client.create(
        customers=customers,
    ...<16 lines>...
        request_options=request_options,
    )
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/vapi/calls/raw_client.py", line 330, in create
    raise ApiError(status_code=_response.status_code, headers=dict(_response.headers), body=_response_json)
vapi.core.api_error.ApiError: headers: {'date': 'Thu, 21 May 2026 13:09:43 GMT', 'content-type': 'application/json; charset=utf-8', 'content-length': '228', 'connection': 'keep-alive', 'x-powered-by': 'Express', 'access-control-allow-origin': '*', 'content-security-policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; form-action 'self'; frame-ancestors 'self'; connect-src 'self' https:; worker-src 'self' blob:", 'x-robots-tag': 'noindex', 'etag': 'W/"e4-/uhLUiSU8+6ZBjzW3nXFaK27/pk"', 'cf-cache-status': 'DYNAMIC', 'set-cookie': '_cfuvid=HTU7YuCAleH4iT7BPhkolFDqZ6Q0fVLJLLwV78cNCHc-1779368983.4144497-1.0.1.1-ifEAoBYARFJXEVIqolLwZbT5yJkgMVPn9LKsEjqhCOQ; HttpOnly; SameSite=None; Secure; Path=/; Domain=vapi.ai', 'server': 'cloudflare', 'cf-ray': '9ff3d1325de4e5bc-IAD', 'alt-svc': 'h3=":443"; ma=86400'}, status_code: 400, body: {'statusCode': 400, 'message': "Couldn't start call. Free Vapi numbers do not support international calls.", 'error': 'Bad Request', 'subscriptionLimits': {'concurrencyBlocked': False, 'concurrencyLimit': 10, 'remainingConcurrentCalls': 9}}
INFO:     49.43.26.105:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.105:0 - "POST /voice/call/outbound HTTP/1.1" 500 Internal Server Error
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/uvicorn/protocols/http/h11_impl.py", line 410, in run_asgi
    result = await app(  # type: ignore[func-returns-value]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        self.scope, self.receive, self.send
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/uvicorn/middleware/proxy_headers.py", line 60, in __call__
    return await self.app(scope, receive, send)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/applications.py", line 1135, in __call__
    await super().__call__(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/applications.py", line 107, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/middleware/errors.py", line 186, in __call__
    raise exc
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/middleware/errors.py", line 164, in __call__
    await self.app(scope, receive, _send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/middleware/cors.py", line 93, in __call__
    await self.simple_response(scope, receive, send, request_headers=headers)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/middleware/cors.py", line 144, in simple_response
    await self.app(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/middleware/exceptions.py", line 63, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/middleware/asyncexitstack.py", line 18, in __call__
    await self.app(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/routing.py", line 716, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/routing.py", line 736, in app
    await route.handle(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/routing.py", line 290, in handle
    await self.app(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 115, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 101, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 355, in app
    raw_response = await run_endpoint_function(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<3 lines>...
    )
    ^
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 243, in run_endpoint_function
    return await dependant.call(**values)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/backend/app/routes/voice.py", line 605, in make_outbound_call
    call = client.calls.create(
        assistant_id=assistant_id,
    ...<2 lines>...
        assistant_overrides=overrides,
    )
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/vapi/calls/client.py", line 265, in create
    _response = self._raw_client.create(
        customers=customers,
    ...<16 lines>...
        request_options=request_options,
    )
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/vapi/calls/raw_client.py", line 330, in create
    raise ApiError(status_code=_response.status_code, headers=dict(_response.headers), body=_response_json)
vapi.core.api_error.ApiError: headers: {'date': 'Thu, 21 May 2026 13:09:51 GMT', 'content-type': 'application/json; charset=utf-8', 'content-length': '228', 'connection': 'keep-alive', 'x-powered-by': 'Express', 'access-control-allow-origin': '*', 'content-security-policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; form-action 'self'; frame-ancestors 'self'; connect-src 'self' https:; worker-src 'self' blob:", 'x-robots-tag': 'noindex', 'etag': 'W/"e4-/uhLUiSU8+6ZBjzW3nXFaK27/pk"', 'cf-cache-status': 'DYNAMIC', 'set-cookie': '_cfuvid=PhpqNu8LYLmgT79Wl3l5jRoiqHlMGtLbL2BEMWQ9PhA-1779368988.9422884-1.0.1.1-5GvDCimE1dDXhJ2PSKsrXAI420WYUUTb2JDeeUKflE4; HttpOnly; SameSite=None; Secure; Path=/; Domain=vapi.ai', 'server': 'cloudflare', 'cf-ray': '9ff3d154eda7910b-IAD', 'alt-svc': 'h3=":443"; ma=86400'}, status_code: 400, body: {'statusCode': 400, 'message': "Couldn't start call. Free Vapi numbers do not support international calls.", 'error': 'Bad Request', 'subscriptionLimits': {'concurrencyBlocked': False, 'concurrencyLimit': 10, 'remainingConcurrentCalls': 9}}
INFO:     49.43.26.105:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     49.43.26.105:0 - "GET /voice/call-status HTTP/1.1" 200 OK