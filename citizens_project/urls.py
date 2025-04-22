from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from app_saude.views import GoogleLoginView, MeView, PersonViewSet, ProviderViewSet

router = DefaultRouter()
router.register(r'person', PersonViewSet)
router.register(r'provider', ProviderViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("auth/login/google/", GoogleLoginView.as_view(), name="google_login"),
    path("", lambda request: HttpResponse("🎉 Login bem-sucedido!")),
    path("auth/me/", MeView.as_view(), name="me"),
    path('api/', include(router.urls)),
]
