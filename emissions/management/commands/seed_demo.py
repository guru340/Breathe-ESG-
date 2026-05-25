from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand

from emissions.ingestion import ingest_csv
from emissions.models import Facility, IngestionBatch, SourceSystem, Tenant


class Command(BaseCommand):
    help = 'Seed a demo tenant and ingest the realistic sample source files.'

    def handle(self, *args, **options):
        tenant, _ = Tenant.objects.get_or_create(slug='acme-industrial', defaults={'name': 'ACME Industrial'})
        facilities = [
            ('DE01', 'Berlin Components Plant', 'DE'),
            ('US01', 'Ohio Assembly Plant', 'US'),
            ('IN01', 'Pune Shared Services', 'IN'),
        ]
        for code, name, country in facilities:
            Facility.objects.get_or_create(tenant=tenant, code=code, defaults={'name': name, 'country': country})
        sources = [
            (SourceSystem.SAP, 'SAP ECC outbound flat file', 'Fuel and procurement records exported as a CSV projection of IDoc-like fields.'),
            (SourceSystem.UTILITY, 'Utility portal CSV', 'Monthly electricity bill exports pulled by facilities.'),
            (SourceSystem.TRAVEL, 'Concur expense export', 'Corporate travel and expense line export.'),
        ]
        source_objects = {}
        for source_type, name, description in sources:
            source, _ = SourceSystem.objects.get_or_create(
                tenant=tenant,
                source_type=source_type,
                defaults={'name': name, 'description': description},
            )
            source_objects[source_type] = source
        if IngestionBatch.objects.filter(tenant=tenant).exists():
            self.stdout.write(self.style.WARNING('Demo tenant already has batches; skipping re-ingestion.'))
            return
        sample_dir = Path(__file__).resolve().parents[3] / 'sample_data'
        for source_type, filename in [
            (SourceSystem.SAP, 'sap_fuel_procurement.csv'),
            (SourceSystem.UTILITY, 'utility_electricity.csv'),
            (SourceSystem.TRAVEL, 'concur_travel.csv'),
        ]:
            with (sample_dir / filename).open('rb') as handle:
                batch = ingest_csv(tenant, source_objects[source_type], File(handle, name=filename))
                self.stdout.write(self.style.SUCCESS(f'Ingested {filename}: {batch.row_count} rows, {batch.failed_count} failed'))
