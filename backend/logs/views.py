"""Meal logging + daily calorie summary."""

from typing import Any

from accounts.models import User
from django.db.models import QuerySet, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import generics
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.views import APIView

from logs.models import MealLog
from logs.serializers import MealLogSerializer


class MealLogListCreate(generics.ListCreateAPIView[MealLog]):
    serializer_class = MealLogSerializer

    def get_queryset(self) -> QuerySet[MealLog]:
        assert isinstance(self.request.user, User)
        queryset = MealLog.objects.filter(user=self.request.user)
        date = self.request.query_params.get("date")
        if date:
            queryset = queryset.filter(logged_at__date=date)
        return queryset

    def perform_create(self, serializer: BaseSerializer[MealLog]) -> None:
        serializer.save(user=self.request.user)


class DailySummaryView(APIView):
    def get(self, request: Request) -> Response:
        assert isinstance(request.user, User)
        date_param = request.query_params.get("date")
        day = parse_date(date_param) if date_param else timezone.now().date()
        logs = MealLog.objects.filter(user=request.user, logged_at__date=day)
        total: int = logs.aggregate(total=Sum("kcal"))["total"] or 0
        goal = request.user.daily_calorie_goal
        summary: dict[str, Any] = {
            "date": str(day),
            "total_kcal": total,
            "goal": goal,
            "remaining": goal - total,
            "count": logs.count(),
        }
        return Response(summary)
