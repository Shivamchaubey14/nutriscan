from rest_framework import generics, permissions

from accounts.models import User
from accounts.serializers import RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView[User]):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveUpdateAPIView[User]):
    """GET the current user; PATCH the daily calorie goal / data-contribution consent."""

    serializer_class = UserSerializer

    def get_object(self) -> User:
        assert isinstance(self.request.user, User)  # guaranteed by IsAuthenticated
        return self.request.user
