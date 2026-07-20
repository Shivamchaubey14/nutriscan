"""Project-level views (health check)."""

from typing import Any

from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Liveness/readiness probe: 200 when the database answers, 503 otherwise."""

    permission_classes = [AllowAny]
    authentication_classes: list[Any] = []

    def get(self, request: Request) -> Response:
        db_ok = True
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:
            db_ok = False
        return Response(
            {"status": "ok" if db_ok else "degraded", "database": db_ok},
            status=200 if db_ok else 503,
        )
