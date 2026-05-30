"""
JWT auth middleware — verifica tokens Supabase.

Rutas públicas (sin token): /health, /perfil/{dni}, /metodologia, docs
Rutas protegidas (requieren token): /buscar, /admin/* (DEC-009 — fase futura)

Por ahora el middleware solo inyecta user_id si el token es válido.
No bloquea rutas aún — eso se implementa en Fase 1 auth (DEC-009).
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


# Prefijos que NO requieren auth (datos públicos del Estado — DEC-002)
_PUBLIC_PREFIXES = (
    "/health",
    "/api/perfil",
    "/api/search",
    "/api/stats",
    "/docs",
    "/openapi",
    "/redoc",
)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.user_id = None
        request.state.user_email = None

        auth_header = request.headers.get("Authorization", "")

        if auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()
            try:
                from app.db.supabase_client import get_supabase_client
                client = get_supabase_client()
                result = client.auth.get_user(token)
                if result and result.user:
                    request.state.user_id = result.user.id
                    request.state.user_email = result.user.email
            except Exception:
                # Token inválido o expirado
                is_public = any(
                    request.url.path.startswith(p) for p in _PUBLIC_PREFIXES
                )
                if not is_public:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Token inválido o expirado"},
                    )

        return await call_next(request)
