from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from app_saude.views.account_management_views import *
from app_saude.views.auth_views import *
from app_saude.views.diary_views import *
from app_saude.views.help_views import *
from app_saude.views.linking_views import *
from app_saude.views.onboarding_views import *
from app_saude.views.simple_dto_views import *
from app_saude.views.visit_views import *
from app_saude.views.vocabulary_views import *

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
router.register(r"full-person", FullPersonViewSet, basename="full-person")
router.register(r"full-provider", FullProviderViewSet, basename="full-provider")
router.register(r"interest-area", InterestAreaViewSet, basename="interest-area")

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
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("admin/", admin.site.urls),
    path("account/", include("allauth.urls")),
    path("account/theme", SwitchDarkModeView.as_view(), name="switch-theme"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # API
    path("api/", include(router.urls)),
    path("accounts/", AccountView.as_view(), name="account"),
    path("api/user-entity/", UserRoleView.as_view(), name="user-entity"),
    path("provider/link-code/", GenerateProviderLinkCodeView.as_view(), name="generate-link-code"),
    path("person/link-code/", PersonLinkProviderView.as_view(), name="person-link-code"),
    path(
        "person/<int:person_id>/provider/<int:provider_id>/unlink/",
        PersonProviderUnlinkView.as_view(),
        name="person-provider-unlink",
    ),
    path("person/providers/", PersonProvidersView.as_view(), name="person-providers"),
    path("provider/persons/", ProviderPersonsView.as_view(), name="provider-persons"),
    path("provider/by-link-code/", ProviderByLinkCodeView.as_view(), name="provider-by-link-code"),
    path("help/send/", SendHelpView.as_view(), name="send-help"),
    path("provider/help/", ReceivedHelpsView.as_view(), name="get-help"),
    path("provider/help/<int:help_id>/resolve/", MarkHelpAsResolvedView.as_view(), name="resolve-help"),
    path("provider/help-count/", HelpCountView.as_view(), name="provider-help-count"),
    path("provider/next-visit/", NextScheduledVisitView.as_view(), name="next-scheduled-visit"),
    path("diaries/", DiaryView.as_view(), name="diary"),
    path("diaries/<str:diary_id>/", DiaryDetailView.as_view(), name="diary-detail"),
    path("provider/patients/<int:person_id>/diaries/", ProviderPersonDiariesView.as_view(), name="acs-diaries"),
    path("person/diaries/", PersonDiariesView.as_view(), name="person-diaries"),
    path(
        "provider/patients/<int:person_id>/diaries/<str:diary_id>/",
        ProviderPersonDiaryDetailView.as_view(),
        name="acs-diary-detail",
    ),
    path("person/interest-areas/mark-attention-point/", MarkAttentionPointView.as_view()),
    # Docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    urlpatterns += [
        path("dev-login-as-provider/", dev_login_as_provider),
        path("dev-login-as-person/", dev_login_as_person),
    ]
