from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    EmissionActivityViewSet,
    FacilityViewSet,
    IngestionBatchViewSet,
    SourceSystemViewSet,
    TenantViewSet,
    dashboard_summary,
    upload_ingestion,
)

router = DefaultRouter()
router.register('tenants', TenantViewSet)
router.register('facilities', FacilityViewSet)
router.register('sources', SourceSystemViewSet)
router.register('batches', IngestionBatchViewSet)
router.register('activities', EmissionActivityViewSet, basename='activity')

urlpatterns = [
    path('', include(router.urls)),
    path('upload/', upload_ingestion, name='upload-ingestion'),
    path('summary/', dashboard_summary, name='dashboard-summary'),
]
