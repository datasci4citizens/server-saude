from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework.routers import DefaultRouter

from app_saude.views import *

router = DefaultRouter()
router.register(r"person", PersonViewSet)
router.register(r"provider", ProviderViewSet)

schema_view = get_schema_view(
    openapi.Info(
        title="SAÚDE! API",
        default_version="v1",
        description="Documentação da API do projeto SAÚDE!",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="mistery@email.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("auth/login/google/", GoogleLoginView.as_view(), name="google_login"),
    path("", lambda request: HttpResponse("🎉 Login bem-sucedido!")),
    path("auth/me/", MeView.as_view(), name="me"),
    path("api/", include(router.urls)),
    path("link/", LinkPersonToProviderView.as_view(), name="link-person-to-provider"),
    path("api/domains/", DomainsWithConceptsView.as_view(), name="domains-with-concepts"),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    path("swagger.json", schema_view.without_ui(cache_timeout=0), name="schema-json"),
]
