import hashlib
import json
from decimal import Decimal

from django.db import models
from django.utils import timezone


class Tenant(models.Model):
    name = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Facility(models.Model):
    tenant = models.ForeignKey(Tenant, related_name='facilities', on_delete=models.CASCADE)
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=160)
    country = models.CharField(max_length=2, default='US')

    class Meta:
        ordering = ['code']
        unique_together = ('tenant', 'code')

    def __str__(self):
        return f'{self.code} - {self.name}'


class SourceSystem(models.Model):
    SAP = 'sap'
    UTILITY = 'utility'
    TRAVEL = 'travel'
    SOURCE_TYPES = [
        (SAP, 'SAP fuel/procurement flat file'),
        (UTILITY, 'Utility electricity CSV'),
        (TRAVEL, 'Corporate travel export'),
    ]

    tenant = models.ForeignKey(Tenant, related_name='sources', on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    source_type = models.CharField(max_length=24, choices=SOURCE_TYPES)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['source_type']
        unique_together = ('tenant', 'source_type')

    def __str__(self):
        return self.name


class IngestionBatch(models.Model):
    PENDING = 'pending'
    PROCESSED = 'processed'
    FAILED = 'failed'
    STATUSES = [(PENDING, 'Pending'), (PROCESSED, 'Processed'), (FAILED, 'Failed')]

    tenant = models.ForeignKey(Tenant, related_name='batches', on_delete=models.CASCADE)
    source = models.ForeignKey(SourceSystem, related_name='batches', on_delete=models.PROTECT)
    file_name = models.CharField(max_length=240)
    status = models.CharField(max_length=16, choices=STATUSES, default=PENDING)
    received_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(null=True, blank=True)
    row_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-received_at']

    def __str__(self):
        return f'{self.source.name} - {self.file_name}'


class RawRecord(models.Model):
    batch = models.ForeignKey(IngestionBatch, related_name='raw_records', on_delete=models.CASCADE)
    row_number = models.PositiveIntegerField()
    payload = models.JSONField()
    row_hash = models.CharField(max_length=64, db_index=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('batch', 'row_number')

    @staticmethod
    def calculate_hash(payload):
        canonical = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


class EmissionActivity(models.Model):
    SCOPE_1 = 'scope_1'
    SCOPE_2 = 'scope_2'
    SCOPE_3 = 'scope_3'
    SCOPES = [(SCOPE_1, 'Scope 1'), (SCOPE_2, 'Scope 2'), (SCOPE_3, 'Scope 3')]

    NEEDS_REVIEW = 'needs_review'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    LOCKED = 'locked'
    STATUSES = [
        (NEEDS_REVIEW, 'Needs review'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
        (LOCKED, 'Locked for audit'),
    ]

    tenant = models.ForeignKey(Tenant, related_name='activities', on_delete=models.CASCADE)
    facility = models.ForeignKey(Facility, null=True, blank=True, related_name='activities', on_delete=models.SET_NULL)
    source = models.ForeignKey(SourceSystem, related_name='activities', on_delete=models.PROTECT)
    batch = models.ForeignKey(IngestionBatch, related_name='activities', on_delete=models.CASCADE)
    raw_record = models.OneToOneField(RawRecord, related_name='activity', on_delete=models.CASCADE)
    activity_date = models.DateField()
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    scope = models.CharField(max_length=16, choices=SCOPES)
    category = models.CharField(max_length=80)
    description = models.CharField(max_length=240)
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit = models.CharField(max_length=24)
    normalized_quantity = models.DecimalField(max_digits=14, decimal_places=3)
    normalized_unit = models.CharField(max_length=24)
    emission_factor = models.DecimalField(max_digits=12, decimal_places=6)
    co2e_kg = models.DecimalField(max_digits=14, decimal_places=3)
    status = models.CharField(max_length=16, choices=STATUSES, default=NEEDS_REVIEW)
    flags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    analyst_notes = models.TextField(blank=True)
    source_reference = models.CharField(max_length=160, blank=True)
    was_edited = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-activity_date', '-id']

    def recalculate(self):
        self.co2e_kg = (self.normalized_quantity * self.emission_factor).quantize(Decimal('0.001'))


class AuditEvent(models.Model):
    activity = models.ForeignKey(EmissionActivity, related_name='audit_events', on_delete=models.CASCADE)
    action = models.CharField(max_length=40)
    actor = models.CharField(max_length=120, default='analyst@example.com')
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

# Create your models here.
