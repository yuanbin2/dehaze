from rest_framework.authentication import TokenAuthentication
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication


class LogoutView(APIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = [IsAuthenticated]  # 强制必须登录才能访问
    def post(self, request):
        response = Response({
            'result': 'success'
        })
        response.delete_cookie('refresh_token')
        return response
