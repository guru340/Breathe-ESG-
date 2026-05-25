from decimal import Decimal

from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .bootstrap import ensure_demo_database
from .ingestion import ingest_csv
from .models import AuditEvent, EmissionActivity, Facility, IngestionBatch, SourceSystem, Tenant
from .serializers import (
    EmissionActivitySerializer,
    FacilitySerializer,
    IngestionBatchSerializer,
    SourceSystemSerializer,
    TenantSerializer,
)


def snapshot(activity):
    return {
        'status': activity.status,
        'description': activity.description,
        'normalized_quantity': str(activity.normalized_quantity),
        'normalized_unit': activity.normalized_unit,
        'emission_factor': str(activity.emission_factor),
        'co2e_kg': str(activity.co2e_kg),
        'analyst_notes': activity.analyst_notes,
        'flags': activity.flags,
    }


class TenantViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer

    def get_queryset(self):
        ensure_demo_database()
        return super().get_queryset()


class FacilityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Facility.objects.select_related('tenant')
    serializer_class = FacilitySerializer

    def get_queryset(self):
        ensure_demo_database()
        return super().get_queryset()


class SourceSystemViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SourceSystem.objects.select_related('tenant')
    serializer_class = SourceSystemSerializer

    def get_queryset(self):
        ensure_demo_database()
        return super().get_queryset()


class IngestionBatchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = IngestionBatch.objects.select_related('tenant', 'source')
    serializer_class = IngestionBatchSerializer

    def get_queryset(self):
        ensure_demo_database()
        return super().get_queryset()


class EmissionActivityViewSet(viewsets.ModelViewSet):
    serializer_class = EmissionActivitySerializer

    def get_queryset(self):
        ensure_demo_database()
        queryset = EmissionActivity.objects.select_related('tenant', 'facility', 'source', 'batch', 'raw_record').prefetch_related('audit_events')
        tenant = self.request.query_params.get('tenant')
        status_filter = self.request.query_params.get('status')
        source_type = self.request.query_params.get('source_type')
        flagged = self.request.query_params.get('flagged')
        if tenant:
            queryset = queryset.filter(tenant__slug=tenant)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if source_type:
            queryset = queryset.filter(source__source_type=source_type)
        if flagged == 'true':
            queryset = queryset.exclude(flags=[])
        return queryset

    def partial_update(self, request, *args, **kwargs):
        activity = self.get_object()
        if activity.status == EmissionActivity.LOCKED:
            return Response({'detail': 'Locked records cannot be edited.'}, status=status.HTTP_409_CONFLICT)
        before = snapshot(activity)
        allowed = {'description', 'normalized_quantity', 'emission_factor', 'analyst_notes', 'flags'}
        for field, value in request.data.items():
            if field in allowed:
                setattr(activity, field, value)
        activity.normalized_quantity = Decimal(str(activity.normalized_quantity))
        activity.emission_factor = Decimal(str(activity.emission_factor))
        activity.recalculate()
        activity.was_edited = True
        activity.save()
        AuditEvent.objects.create(activity=activity, action='edited', before=before, after=snapshot(activity), note=request.data.get('analyst_notes', ''))
        return Response(self.get_serializer(activity).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        activity = self.get_object()
        if activity.status == EmissionActivity.LOCKED:
            return Response({'detail': 'Already locked for audit.'}, status=status.HTTP_409_CONFLICT)
        before = snapshot(activity)
        activity.status = EmissionActivity.APPROVED
        activity.approved_at = timezone.now()
        activity.analyst_notes = request.data.get('note', activity.analyst_notes)
        activity.save(update_fields=['status', 'approved_at', 'analyst_notes', 'updated_at'])
        AuditEvent.objects.create(activity=activity, action='approved', before=before, after=snapshot(activity), note=request.data.get('note', ''))
        return Response(self.get_serializer(activity).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        activity = self.get_object()
        if activity.status == EmissionActivity.LOCKED:
            return Response({'detail': 'Locked records cannot be rejected.'}, status=status.HTTP_409_CONFLICT)
        before = snapshot(activity)
        activity.status = EmissionActivity.REJECTED
        activity.analyst_notes = request.data.get('note', activity.analyst_notes)
        activity.save(update_fields=['status', 'analyst_notes', 'updated_at'])
        AuditEvent.objects.create(activity=activity, action='rejected', before=before, after=snapshot(activity), note=request.data.get('note', ''))
        return Response(self.get_serializer(activity).data)

    @action(detail=True, methods=['post'])
    def lock(self, request, pk=None):
        activity = self.get_object()
        if activity.status != EmissionActivity.APPROVED:
            return Response({'detail': 'Only approved rows can be locked for audit.'}, status=status.HTTP_409_CONFLICT)
        before = snapshot(activity)
        activity.status = EmissionActivity.LOCKED
        activity.locked_at = timezone.now()
        activity.save(update_fields=['status', 'locked_at', 'updated_at'])
        AuditEvent.objects.create(activity=activity, action='locked', before=before, after=snapshot(activity), note='Locked for audit package')
        return Response(self.get_serializer(activity).data)


@api_view(['POST'])
def upload_ingestion(request):
    ensure_demo_database()
    tenant = get_object_or_404(Tenant, slug=request.data.get('tenant', 'acme-industrial'))
    source = get_object_or_404(SourceSystem, tenant=tenant, source_type=request.data.get('source_type'))
    uploaded = request.FILES.get('file')
    if not uploaded:
        return Response({'detail': 'file is required'}, status=status.HTTP_400_BAD_REQUEST)
    batch = ingest_csv(tenant, source, uploaded)
    return Response(IngestionBatchSerializer(batch).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def dashboard_summary(request):
    ensure_demo_database()
    tenant_slug = request.query_params.get('tenant', 'acme-industrial')
    activities = EmissionActivity.objects.filter(tenant__slug=tenant_slug)
    total = activities.aggregate(total=Sum('co2e_kg'))['total'] or Decimal('0')
    by_scope = activities.values('scope').annotate(total=Sum('co2e_kg'), rows=Count('id')).order_by('scope')
    by_status = activities.values('status').annotate(rows=Count('id')).order_by('status')
    by_source = activities.values('source__source_type', 'source__name').annotate(total=Sum('co2e_kg'), rows=Count('id')).order_by('source__source_type')
    return Response({
        'total_co2e_kg': total,
        'rows': activities.count(),
        'flagged_rows': activities.exclude(flags=[]).count(),
        'pending_rows': activities.filter(status=EmissionActivity.NEEDS_REVIEW).count(),
        'by_scope': list(by_scope),
        'by_status': list(by_status),
        'by_source': list(by_source),
    })

# Create your views here.
