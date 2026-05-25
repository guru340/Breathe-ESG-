from django.contrib import admin

from .models import AuditEvent, EmissionActivity, Facility, IngestionBatch, RawRecord, SourceSystem, Tenant


admin.site.register(Tenant)
admin.site.register(Facility)
admin.site.register(SourceSystem)
admin.site.register(IngestionBatch)
admin.site.register(RawRecord)
admin.site.register(EmissionActivity)
admin.site.register(AuditEvent)

# Register your models here.
