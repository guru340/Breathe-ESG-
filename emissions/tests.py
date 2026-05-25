from pathlib import Path

from django.core.files import File
from django.test import TestCase

from .ingestion import ingest_csv
from .models import EmissionActivity, Facility, SourceSystem, Tenant


class IngestionTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='ACME Industrial', slug='acme-industrial')
        Facility.objects.create(tenant=self.tenant, code='DE01', name='Berlin Components Plant', country='DE')
        Facility.objects.create(tenant=self.tenant, code='US01', name='Ohio Assembly Plant', country='US')
        Facility.objects.create(tenant=self.tenant, code='IN01', name='Pune Shared Services', country='IN')

    def make_source(self, source_type):
        return SourceSystem.objects.create(tenant=self.tenant, source_type=source_type, name=source_type)

    def ingest_sample(self, source_type, filename):
        path = Path(__file__).resolve().parents[1] / 'sample_data' / filename
        with path.open('rb') as handle:
            return ingest_csv(self.tenant, self.make_source(source_type), File(handle, name=filename))

    def test_sap_sample_keeps_bad_rows_for_review(self):
        batch = self.ingest_sample(SourceSystem.SAP, 'sap_fuel_procurement.csv')
        self.assertEqual(batch.row_count, 5)
        self.assertEqual(EmissionActivity.objects.filter(scope=EmissionActivity.SCOPE_1).count(), 2)
        flagged = EmissionActivity.objects.get(source_reference='5100001333')
        self.assertIn('unknown_facility', flagged.flags)
        self.assertIn('missing_factor', flagged.flags)

    def test_utility_sample_flags_unusual_period(self):
        self.ingest_sample(SourceSystem.UTILITY, 'utility_electricity.csv')
        row = EmissionActivity.objects.get(source_reference='UTIL-2026-004')
        self.assertEqual(row.scope, EmissionActivity.SCOPE_2)
        self.assertIn('unusual_billing_period', row.flags)

    def test_travel_sample_flags_missing_flight_distance(self):
        self.ingest_sample(SourceSystem.TRAVEL, 'concur_travel.csv')
        row = EmissionActivity.objects.get(source_reference='TR-9003')
        self.assertEqual(row.scope, EmissionActivity.SCOPE_3)
        self.assertIn('missing_distance', row.flags)

# Create your tests here.
