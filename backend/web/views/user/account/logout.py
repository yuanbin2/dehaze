from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken


class LogoutViews(APIView):
    permission_classes = (IsAuthenticated,)
    def post(self, request, *args, **kwargs):
        response = Response({
            'result': 'success',
        })
        response.delete_cookie('refresh_token')
        return response