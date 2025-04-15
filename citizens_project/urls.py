from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path

from app_saude.views import GoogleLogin, me

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("auth/login/google/", GoogleLogin.as_view(), name="google_login"),
    path("", lambda request: HttpResponse("🎉 Login bem-sucedido!")),
    path("auth/me/", me),
]
