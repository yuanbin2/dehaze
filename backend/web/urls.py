
from django.urls import path, re_path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from web.views.homepage.restore_image import RestoreImageView
from web.views.homepage.restore_video import RestoreVideoView, VideoProgressView
from web.views.index import index
from web.views.user.account.get_user_info import GetUserInfoView
from web.views.user.account.login import LoginViews
from web.views.user.account.logout import LogoutView
from web.views.user.account.refresh_token import RefreshTokenView
from web.views.user.account.register import RegisterView

urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/user/account/login/', LoginViews.as_view()),
    path('api/user/account/logout/', LogoutView.as_view()),
    path('api/user/account/register/', RegisterView.as_view()),
    path('api/user/account/refresh_token/', RefreshTokenView.as_view()),
    path('api/user/account/get_user_info/', GetUserInfoView.as_view()),
    path('api/restore_image/', RestoreImageView.as_view()),
    path('api/restore_video/', RestoreVideoView.as_view()),
    path('api/video_progress/', VideoProgressView.as_view()),
    re_path(r'^(?!media/|static/|assets/).*$', index),
    path('', index),
]
