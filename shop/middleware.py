from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.deprecation import MiddlewareMixin


class JWTAuthenticationMiddleware(MiddlewareMixin):
    """
    Simple middleware that authenticates users based on a JWT stored in a cookie.
    It runs after Django's AuthenticationMiddleware and can override request.user.
    """

    def process_request(self, request):
        token = request.COOKIES.get('access_token')
        if not token:
            return

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        except jwt.PyJWTError:
            # Invalid or expired token; treat as anonymous
            return

        user_id = payload.get('user_id')
        if not user_id:
            return

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return

        request.user = user


def create_jwt_for_user(user):
    """
    Helper to create a JWT for the given user with 1 day expiry.
    """
    exp = datetime.now(timezone.utc) + timedelta(days=1)
    payload = {
        'user_id': user.id,
        'exp': exp,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    # pyjwt>=2 returns str when using algorithm
    return token

