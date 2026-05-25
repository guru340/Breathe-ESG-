import csv
import io
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from dateutil import parser
from django.db import transaction
from django.utils import timezone

from .models import EmissionActivity, Facility, IngestionBatch, RawRecord, SourceSystem


@dataclass
class NormalizedRow:
    activity_date: date
    period_start: date | None
    period_end: date | None
    scope: str
    category: str
    description: str
    quantity: Decimal
    unit: str
    normalized_quantity: Decimal
    normalized_unit: str
    emission_factor: Decimal
    facility_code: str | None = None
    source_reference: str = ''
    flags: list[str] | None = None
    metadata: dict | None = None


UNIT_ALIASES = {
    'L': ('litre', Decimal('1')),
    'LTR': ('litre', Decimal('1')),
    'LITER': ('litre', Decimal('1')),
    'LITRE': ('litre', Decimal('1')),
    'GAL': ('litre', Decimal('3.78541')),
    'GALLON': ('litre', Decimal('3.78541')),
    'KWH': ('kwh', Decimal('1')),
    'MWH': ('kwh', Decimal('1000')),
    'KG': ('kg', Decimal('1')),
    'TON': ('kg', Decimal('1000')),
    'TONNE': ('kg', Decimal('1000')),
    'KM': ('km', Decimal('1')),
    'MI': ('km', Decimal('1.60934')),
    'NIGHT': ('night', Decimal('1')),
}

EMISSION_FACTORS = {
    ('diesel', 'litre'): Decimal('2.680000'),
    ('gasoline', 'litre'): Decimal('2.310000'),
    ('natural_gas', 'kwh'): Decimal('0.184000'),
    ('steel', 'kg'): Decimal('1.900000'),
    ('paper', 'kg'): Decimal('1.100000'),
    ('electricity_us_grid', 'kwh'): Decimal('0.386000'),
    ('flight', 'km'): Decimal('0.158000'),
    ('hotel', 'night'): Decimal('20.000000'),
    ('ground_transport', 'km'): Decimal('0.180000'),
}


def parse_decimal(value):
    if value is None or str(value).strip() == '':
        raise ValueError('missing numeric value')
    cleaned = str(value).replace(',', '').strip()
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f'invalid decimal: {value}') from exc


def parse_date(value):
    if not value:
        raise ValueError('missing date')
    return parser.parse(str(value), dayfirst=False).date()


def normalize_unit(unit, quantity):
    raw = str(unit or '').strip().upper()
    if raw not in UNIT_ALIASES:
        return str(unit or '').strip().lower(), quantity, ['unknown_unit']
    normalized_unit, multiplier = UNIT_ALIASES[raw]
    return normalized_unit, (quantity * multiplier).quantize(Decimal('0.001')), []


def pick(row, *names):
    lowered = {key.lower().strip(): value for key, value in row.items()}
    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return ''


def detect_material(description):
    text = description.lower()
    if 'diesel' in text:
        return 'diesel', EmissionActivity.SCOPE_1, 'Stationary/mobile fuel'
    if 'gasoline' in text or 'petrol' in text:
        return 'gasoline', EmissionActivity.SCOPE_1, 'Mobile fuel'
    if 'natural gas' in text or 'erdgas' in text:
        return 'natural_gas', EmissionActivity.SCOPE_1, 'Stationary fuel'
    if 'steel' in text or 'stahl' in text:
        return 'steel', EmissionActivity.SCOPE_3, 'Purchased goods'
    if 'paper' in text or 'papier' in text:
        return 'paper', EmissionActivity.SCOPE_3, 'Purchased goods'
    return 'unknown', EmissionActivity.SCOPE_3, 'Purchased goods'


def normalize_sap(row):
    description = pick(row, 'MAKTX', 'material_description', 'Kurztext')
    material, scope, category = detect_material(description)
    quantity = parse_decimal(pick(row, 'MENGE', 'quantity', 'Menge'))
    unit, normalized_quantity, flags = normalize_unit(pick(row, 'MEINS', 'unit', 'Einheit'), quantity)
    factor = EMISSION_FACTORS.get((material, unit), Decimal('0'))
    if factor == 0:
        flags.append('missing_factor')
    posting_date = parse_date(pick(row, 'BUDAT', 'posting_date', 'Buchungsdatum'))
    if not pick(row, 'WERKS', 'plant', 'Werk'):
        flags.append('missing_facility')
    return NormalizedRow(
        activity_date=posting_date,
        period_start=None,
        period_end=None,
        scope=scope,
        category=category,
        description=description or material,
        quantity=quantity,
        unit=str(pick(row, 'MEINS', 'unit', 'Einheit')).strip(),
        normalized_quantity=normalized_quantity,
        normalized_unit=unit,
        emission_factor=factor,
        facility_code=str(pick(row, 'WERKS', 'plant', 'Werk')).strip() or None,
        source_reference=str(pick(row, 'DOCNUM', 'document_number', 'BELNR')),
        flags=flags,
        metadata={'material': pick(row, 'MATNR', 'material'), 'vendor': pick(row, 'LIFNR', 'vendor'), 'purchase_order': pick(row, 'EBELN', 'po')},
    )


def normalize_utility(row):
    quantity = parse_decimal(pick(row, 'usage_kwh', 'kwh', 'Usage (kWh)'))
    unit, normalized_quantity, flags = normalize_unit('kWh', quantity)
    period_start = parse_date(pick(row, 'period_start', 'start_date', 'service_from'))
    period_end = parse_date(pick(row, 'period_end', 'end_date', 'service_to'))
    days = (period_end - period_start).days + 1
    if days < 20 or days > 45:
        flags.append('unusual_billing_period')
    return NormalizedRow(
        activity_date=period_end,
        period_start=period_start,
        period_end=period_end,
        scope=EmissionActivity.SCOPE_2,
        category='Purchased electricity',
        description=f"Electricity meter {pick(row, 'meter_number', 'meter')}",
        quantity=quantity,
        unit='kWh',
        normalized_quantity=normalized_quantity,
        normalized_unit=unit,
        emission_factor=EMISSION_FACTORS[('electricity_us_grid', 'kwh')],
        facility_code=str(pick(row, 'facility_code', 'site_code')).strip() or None,
        source_reference=str(pick(row, 'bill_id', 'account_number')),
        flags=flags,
        metadata={'meter_number': pick(row, 'meter_number', 'meter'), 'tariff': pick(row, 'tariff', 'rate_code'), 'demand_kw': pick(row, 'demand_kw')},
    )


def normalize_travel(row):
    expense_type = str(pick(row, 'expense_type', 'category')).lower()
    flags = []
    if 'flight' in expense_type or 'air' in expense_type:
        category = 'Business travel - air'
        factor_key = ('flight', 'km')
        distance = pick(row, 'distance_km', 'distance', 'miles')
        quantity = parse_decimal(distance) if distance else Decimal('0')
        unit = 'km' if pick(row, 'distance_km', 'distance') else 'mi'
        normalized_unit, normalized_quantity, unit_flags = normalize_unit(unit, quantity)
        flags += unit_flags
        if normalized_quantity == 0:
            flags.append('missing_distance')
        description = f"Flight {pick(row, 'origin')} to {pick(row, 'destination')}"
    elif 'hotel' in expense_type or 'lodging' in expense_type:
        category = 'Business travel - hotel'
        factor_key = ('hotel', 'night')
        quantity = parse_decimal(pick(row, 'nights', 'quantity') or '1')
        normalized_unit, normalized_quantity, unit_flags = normalize_unit('night', quantity)
        flags += unit_flags
        description = f"Hotel stay at {pick(row, 'vendor')}"
    else:
        category = 'Business travel - ground'
        factor_key = ('ground_transport', 'km')
        quantity = parse_decimal(pick(row, 'distance_km', 'distance') or '0')
        normalized_unit, normalized_quantity, unit_flags = normalize_unit('km', quantity)
        flags += unit_flags
        if normalized_quantity == 0:
            flags.append('missing_distance')
        description = f"Ground transport with {pick(row, 'vendor')}"
    return NormalizedRow(
        activity_date=parse_date(pick(row, 'transaction_date', 'date')),
        period_start=None,
        period_end=None,
        scope=EmissionActivity.SCOPE_3,
        category=category,
        description=description,
        quantity=quantity,
        unit=normalized_unit,
        normalized_quantity=normalized_quantity,
        normalized_unit=normalized_unit,
        emission_factor=EMISSION_FACTORS[factor_key],
        facility_code=str(pick(row, 'facility_code', 'cost_center')).strip() or None,
        source_reference=str(pick(row, 'report_id', 'expense_id')),
        flags=flags,
        metadata={'employee_id': pick(row, 'employee_id'), 'vendor': pick(row, 'vendor'), 'amount': pick(row, 'amount'), 'currency': pick(row, 'currency')},
    )


NORMALIZERS = {
    SourceSystem.SAP: normalize_sap,
    SourceSystem.UTILITY: normalize_utility,
    SourceSystem.TRAVEL: normalize_travel,
}


@transaction.atomic
def ingest_csv(tenant, source, uploaded_file):
    text = uploaded_file.read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text))
    batch = IngestionBatch.objects.create(tenant=tenant, source=source, file_name=uploaded_file.name)
    normalizer = NORMALIZERS[source.source_type]
    for index, row in enumerate(reader, start=2):
        raw = RawRecord.objects.create(
            batch=batch,
            row_number=index,
            payload=row,
            row_hash=RawRecord.calculate_hash(row),
        )
        try:
            normalized = normalizer(row)
            facility = None
            flags = normalized.flags or []
            if normalized.facility_code:
                facility = Facility.objects.filter(tenant=tenant, code=normalized.facility_code).first()
                if facility is None:
                    flags.append('unknown_facility')
            co2e = (normalized.normalized_quantity * normalized.emission_factor).quantize(Decimal('0.001'))
            if co2e > Decimal('5000'):
                flags.append('high_emissions')
            EmissionActivity.objects.create(
                tenant=tenant,
                facility=facility,
                source=source,
                batch=batch,
                raw_record=raw,
                activity_date=normalized.activity_date,
                period_start=normalized.period_start,
                period_end=normalized.period_end,
                scope=normalized.scope,
                category=normalized.category,
                description=normalized.description,
                quantity=normalized.quantity,
                unit=normalized.unit,
                normalized_quantity=normalized.normalized_quantity,
                normalized_unit=normalized.normalized_unit,
                emission_factor=normalized.emission_factor,
                co2e_kg=co2e,
                flags=flags,
                metadata=normalized.metadata or {},
                source_reference=normalized.source_reference,
            )
        except Exception as exc:
            raw.error = str(exc)
            raw.save(update_fields=['error'])
            batch.failed_count += 1
    batch.row_count = max(reader.line_num - 1, 0)
    batch.status = IngestionBatch.PROCESSED if batch.failed_count == 0 else IngestionBatch.FAILED
    batch.processed_at = timezone.now()
    batch.save(update_fields=['row_count', 'failed_count', 'status', 'processed_at'])
    return batch
