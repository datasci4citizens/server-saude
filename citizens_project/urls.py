from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework.routers import DefaultRouter

from app_saude.views import *

router = DefaultRouter()
router.register(r"person", PersonViewSet)
router.register(r"provider", ProviderViewSet)

router.register(r"vocabulary", VocabularyViewSet)
router.register(r"concept-class", ConceptClassViewSet)
router.register(r"concept", ConceptViewSet)
router.register(r"concept-synonym", ConceptSynonymViewSet)
router.register(r"domain", DomainViewSet)

router.register(r"location", LocationViewSet)
router.register(r"care-site", CareSiteViewSet)
router.register(r"drug-exposure", DrugExposureViewSet)

router.register(r"observation", ObservationViewSet)
router.register(r"visit-occurrence", VisitOccurrenceViewSet)
router.register(r"measurement", MeasurementViewSet)
router.register(r"fact-relationship", FactRelationshipViewSet)

# router.register(r"full-registration", FullPersonRegistrationView, basename="full-registration")


# path("link/", LinkPersonToProviderView.as_view(), name="link-person-to-provider"),
#    path("api/domains/", DomainsWithConceptsView.as_view(), name="domains-with-concepts"),

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
    # Auth
    path("auth/login/google/", GoogleLoginView.as_view(), name="google_login"),
    path("auth/login/admin/", AdminLoginView.as_view(), name="admin_login"),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("auth/me/", MeView.as_view(), name="me"),
    # Complete Api
    path("api/", include(router.urls)),
    # Docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
