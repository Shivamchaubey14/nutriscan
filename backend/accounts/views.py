from rest_framework import generics, permissions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.serializers import RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView[User]):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(APIView):
    def get(self, request: Request) -> Response:
        user = request.user
        assert isinstance(user, User)  # guaranteed by IsAuthenticated
        return Response(UserSerializer(user).data)
