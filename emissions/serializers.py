from rest_framework import serializers

from .models import AuditEvent, EmissionActivity, Facility, IngestionBatch, SourceSystem, Tenant


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'slug']


class FacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = ['id', 'tenant', 'code', 'name', 'country']


class SourceSystemSerializer(serializers.ModelSerializer):
    source_type_label = serializers.CharField(source='get_source_type_display', read_only=True)

    class Meta:
        model = SourceSystem
        fields = ['id', 'tenant', 'name', 'source_type', 'source_type_label', 'description']


class IngestionBatchSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name', read_only=True)
    source_type = serializers.CharField(source='source.source_type', read_only=True)

    class Meta:
        model = IngestionBatch
        fields = ['id', 'tenant', 'source', 'source_name', 'source_type', 'file_name', 'status', 'received_at', 'processed_at', 'row_count', 'failed_count', 'notes']


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = ['id', 'action', 'actor', 'before', 'after', 'note', 'created_at']


class EmissionActivitySerializer(serializers.ModelSerializer):
    facility_code = serializers.CharField(source='facility.code', read_only=True)
    facility_name = serializers.CharField(source='facility.name', read_only=True)
    source_name = serializers.CharField(source='source.name', read_only=True)
    source_type = serializers.CharField(source='source.source_type', read_only=True)
    raw_payload = serializers.JSONField(source='raw_record.payload', read_only=True)
    raw_error = serializers.CharField(source='raw_record.error', read_only=True)
    audit_events = AuditEventSerializer(many=True, read_only=True)

    class Meta:
        model = EmissionActivity
        fields = [
            'id', 'tenant', 'facility', 'facility_code', 'facility_name', 'source', 'source_name', 'source_type',
            'batch', 'raw_record', 'activity_date', 'period_start', 'period_end', 'scope', 'category',
            'description', 'quantity', 'unit', 'normalized_quantity', 'normalized_unit', 'emission_factor',
            'co2e_kg', 'status', 'flags', 'metadata', 'analyst_notes', 'source_reference', 'was_edited',
            'approved_at', 'locked_at', 'updated_at', 'raw_payload', 'raw_error', 'audit_events',
        ]
        read_only_fields = ['tenant', 'source', 'batch', 'raw_record', 'co2e_kg', 'approved_at', 'locked_at', 'was_edited']
