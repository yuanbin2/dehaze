import traceback

from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from web.models.user import UserProfile


class LoginViews(APIView):
    def post(self, request, *args, **kwargs):
        try:
            username = request.data['username'].strip()
            password = request.data['password'].strip()
            if not username or not password:
                return Response({
                    'result': '用户名或密码不能为空',
                })
            user = authenticate(username=username, password=password)
            if user:
                user_profile = UserProfile.objects.get(user=user)
                # print('user_profile', user_profile)
                refresh = RefreshToken.for_user(user)
                response = Response({
                    'result': 'success',
                    'access': str(refresh.access_token),
                    'user_id': user.id,
                    'username': user.get_username(),
                    'photo': user_profile.photo.url,
                    'profile': user_profile.profile,
                })
                response.set_cookie(
                    key='refresh_token',
                    value=str(refresh),
                    httponly=True,
                    samesite='Lax',
                    secure=True,
                    max_age=86400 * 7,
                )
                return response
            return Response({
                'result': '用户名或密码错误',
            })
        except:
            traceback.print_exc()
            return Response({
                'result':'系统异常请稍后重试',
            })