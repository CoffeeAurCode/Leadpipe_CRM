INFO:     70.29.139.170:0 - "OPTIONS /complaints HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /complaints HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /appointments?start_date=2026-04-06&end_date=2026-08-04 HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "OPTIONS /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /complaints HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /appointments?start_date=2026-04-06&end_date=2026-08-04 HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "OPTIONS /tenants?sort_order=asc HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /tenants?sort_order=asc HTTP/1.1" 500 Internal Server Error
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
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 377, in app
    content = await serialize_response(
              ^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<10 lines>...
    )
    ^
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 215, in serialize_response
    raise ResponseValidationError(
    ...<3 lines>...
    )
fastapi.exceptions.ResponseValidationError: 30 validation errors:
  {'type': 'value_error', 'loc': ('response', 0, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '15149841671', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 1, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0130', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 2, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0129', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 3, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0128', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 4, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0127', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 5, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0126', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 6, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0125', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 7, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0124', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 8, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0123', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 9, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0122', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 10, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0121', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 11, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0120', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 12, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0119', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 13, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0118', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 14, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0117', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 15, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0116', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 16, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0115', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 17, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0114', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 18, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0113', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 19, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0112', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 20, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0111', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 21, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0110', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 22, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0109', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 23, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0108', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 24, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0107', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 25, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0106', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 26, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0105', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 27, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0104', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 28, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0103', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 29, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0102', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  File "/opt/render/project/src/backend/app/routes/tenants.py", line 270, in get_all_tenants
    GET /tenants
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /complaints HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /appointments?start_date=2026-04-06&end_date=2026-08-04 HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /tenants?sort_order=asc HTTP/1.1" 500 Internal Server Error
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
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 377, in app
    content = await serialize_response(
              ^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<10 lines>...
    )
    ^
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 215, in serialize_response
    raise ResponseValidationError(
    ...<3 lines>...
    )
fastapi.exceptions.ResponseValidationError: 30 validation errors:
  {'type': 'value_error', 'loc': ('response', 0, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '15149841671', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 1, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0130', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 2, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0129', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 3, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0128', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 4, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0127', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 5, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0126', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 6, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0125', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 7, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0124', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 8, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0123', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 9, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0122', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 10, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0121', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 11, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0120', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 12, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0119', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 13, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0118', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 14, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0117', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 15, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0116', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 16, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0115', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 17, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0114', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 18, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0113', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 19, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0112', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 20, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0111', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 21, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0110', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 22, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0109', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 23, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0108', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 24, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0107', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 25, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0106', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 26, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0105', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 27, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0104', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 28, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0103', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 29, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0102', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  File "/opt/render/project/src/backend/app/routes/tenants.py", line 270, in get_all_tenants
    GET /tenants
INFO:     70.29.139.170:0 - "OPTIONS /leasing/leads HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "OPTIONS /leasing/metrics HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "OPTIONS /property-groups/users/me/vapi-config HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "OPTIONS /leasing/listings HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /leasing/metrics HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "OPTIONS /voice/agent-info HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "OPTIONS /call_logs/stats?days=30 HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /leasing/listings HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /leasing/leads HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /property-groups/users/me/vapi-config HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/agent-info HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /leasing/listings HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "OPTIONS /tenants HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /call_logs/stats?days=30 HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /leasing/leads HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /leasing/metrics HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /property-groups/users/me/vapi-config HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /complaints HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /appointments?start_date=2026-04-06&end_date=2026-08-04 HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "OPTIONS /rents/summary HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /tenants HTTP/1.1" 500 Internal Server Error
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
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 377, in app
    content = await serialize_response(
              ^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<10 lines>...
    )
    ^
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 215, in serialize_response
    raise ResponseValidationError(
    ...<3 lines>...
    )
fastapi.exceptions.ResponseValidationError: 30 validation errors:
  {'type': 'value_error', 'loc': ('response', 0, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '15149841671', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 1, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0130', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 2, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0129', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 3, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0128', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 4, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0127', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 5, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0126', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 6, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0125', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 7, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0124', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 8, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0123', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 9, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0122', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 10, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0121', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 11, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0120', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 12, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0119', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 13, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0118', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 14, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0117', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 15, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0116', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 16, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0115', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 17, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0114', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 18, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0113', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 19, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0112', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 20, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0111', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 21, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0110', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 22, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0109', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 23, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0108', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 24, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0107', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 25, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0106', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 26, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0105', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 27, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0104', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 28, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0103', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 29, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0102', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  File "/opt/render/project/src/backend/app/routes/tenants.py", line 270, in get_all_tenants
    GET /tenants
INFO:     70.29.139.170:0 - "OPTIONS /property-groups HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "OPTIONS /buildings HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /rents/summary HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "OPTIONS /complaints HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "OPTIONS /appointments?start_date=2026-04-07&end_date=2026-08-05 HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "OPTIONS /notifications HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /property-groups HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /buildings HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /complaints HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /appointments?start_date=2026-04-07&end_date=2026-08-05 HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "OPTIONS /tenants?sort_order=asc HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /tenants?sort_order=asc HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /leasing/leads HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /leasing/metrics HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /leasing/listings HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /property-groups/users/me/vapi-config HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "OPTIONS /voice/call-status HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /complaints HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /appointments?start_date=2026-04-07&end_date=2026-08-05 HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /tenants?sort_order=asc HTTP/1.1" 500 Internal Server Error
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
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 377, in app
    content = await serialize_response(
              ^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<10 lines>...
    )
    ^
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 215, in serialize_response
    raise ResponseValidationError(
    ...<3 lines>...
    )
fastapi.exceptions.ResponseValidationError: 30 validation errors:
  {'type': 'value_error', 'loc': ('response', 0, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '15149841671', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 1, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0130', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 2, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0129', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 3, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0128', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 4, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0127', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 5, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0126', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 6, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0125', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 7, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0124', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 8, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0123', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 9, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0122', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 10, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0121', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 11, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0120', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 12, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0119', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 13, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0118', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 14, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0117', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 15, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0116', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 16, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0115', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 17, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0114', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 18, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0113', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 19, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0112', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 20, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0111', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 21, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0110', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 22, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0109', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 23, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0108', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 24, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0107', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 25, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0106', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 26, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0105', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 27, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0104', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 28, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0103', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 29, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0102', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  File "/opt/render/project/src/backend/app/routes/tenants.py", line 270, in get_all_tenants
    GET /tenants
INFO:     205.254.163.150:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "OPTIONS /flats?vacant=true HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /flats?vacant=true HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /tenants?sort_order=asc HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "POST /tenants HTTP/1.1" 500 Internal Server Error
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /tenants HTTP/1.1" 500 Internal Server Error
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
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 377, in app
    content = await serialize_response(
              ^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<10 lines>...
    )
    ^
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 215, in serialize_response
    raise ResponseValidationError(
    ...<3 lines>...
    )
fastapi.exceptions.ResponseValidationError: 30 validation errors:
  {'type': 'value_error', 'loc': ('response', 0, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '15149841671', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 1, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0130', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 2, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0129', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 3, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0128', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 4, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0127', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 5, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0126', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 6, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0125', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 7, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0124', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 8, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0123', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 9, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0122', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 10, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0121', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 11, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0120', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 12, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0119', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 13, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0118', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 14, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0117', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 15, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0116', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 16, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0115', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 17, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0114', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 18, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0113', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 19, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0112', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 20, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0111', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 21, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0110', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 22, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0109', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 23, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0108', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 24, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0107', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 25, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0106', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 26, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0105', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 27, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0104', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 28, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0103', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 29, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0102', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  File "/opt/render/project/src/backend/app/routes/tenants.py", line 270, in get_all_tenants
    GET /tenants
INFO:     205.254.163.150:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /leasing/leads HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /leasing/listings HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /leasing/metrics HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "OPTIONS /buildings HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /property-groups/users/me/vapi-config HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "OPTIONS /property-groups HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /buildings HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /property-groups HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /tenants?sort_order=asc HTTP/1.1" 500 Internal Server Error
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
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 377, in app
    content = await serialize_response(
              ^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<10 lines>...
    )
    ^
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 215, in serialize_response
    raise ResponseValidationError(
    ...<3 lines>...
    )
fastapi.exceptions.ResponseValidationError: 30 validation errors:
  {'type': 'value_error', 'loc': ('response', 0, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '15149841671', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 1, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0130', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 2, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0129', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 3, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0128', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 4, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0127', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 5, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0126', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 6, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0125', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 7, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0124', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 8, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0123', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 9, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0122', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 10, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0121', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 11, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0120', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 12, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0119', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 13, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0118', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 14, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0117', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 15, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0116', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 16, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0115', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 17, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0114', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 18, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0113', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 19, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0112', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 20, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0111', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 21, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0110', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 22, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0109', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 23, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0108', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 24, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0107', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 25, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0106', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 26, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '450-555-0105', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 27, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0104', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 28, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '438-555-0103', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  {'type': 'value_error', 'loc': ('response', 29, 'phone'), 'msg': 'Value error, Phone must be E.164 format, e.g. +16135551234', 'input': '514-555-0102', 'ctx': {'error': ValueError('Phone must be E.164 format, e.g. +16135551234')}}
  File "/opt/render/project/src/backend/app/routes/tenants.py", line 270, in get_all_tenants
    GET /tenants
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/agent-info HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /call_logs/stats?days=30 HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /rents/summary HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/agent-info HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /call_logs/stats?days=30 HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /tenants?sort_order=asc HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /leasing/listings HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /leasing/leads HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /leasing/metrics HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /property-groups/users/me/vapi-config HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/agent-info HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /call_logs/stats?days=30 HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /leasing/leads HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /leasing/metrics HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /property-groups/users/me/vapi-config HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /leasing/listings HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     205.254.163.150:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "OPTIONS /notifications HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "OPTIONS /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "OPTIONS /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "OPTIONS /notifications HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     70.29.139.170:0 - "GET /voice/call-status HTTP/1.1" 200 OK