from django.contrib import admin
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import include, path

from core.views import me


def start_google_login(request):
    return redirect("/accounts/google/login/")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("auth/login/google/", start_google_login),
    path("", lambda request: HttpResponse("🎉 Login bem-sucedido!")),
    path("auth/me/", me),
]
