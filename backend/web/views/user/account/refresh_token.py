import traceback

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from backend.settings import SIMPLE_JWT


class RefreshTokenView(APIView):
    def post(self, request):
        try:
            refresh_token = request.COOKIES.get('refresh_token')
            if not refresh_token:
                return Response({
                    'result': '不存在refresh_token',
                }, status=401)
            refresh = RefreshToken(refresh_token)

            if settings.SIMPLE_JWT['ROTATE_REFRESH_TOKENS']:
                refresh.set_jti()
                response = Response({
                    'result': 'success',
                    'access': str(refresh.access_token),
                })
                response.set_cookie(
                    key = 'refresh_token',
                    value= str(refresh),
                    httponly=True,
                    samesite='Lax',
                    secure = True,
                    max_age=86400 * 7,
                )

            return Response({
                'result': 'success',
                'access': str(refresh.access_token),
            })
        except:
            traceback.print_exc()
            return Response({
                'result': 'refresh_token过期了',
            },status=401)