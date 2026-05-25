# Sources Researched

## SAP Fuel And Procurement

Real-world format: SAP IDoc/flat-file style export projected to CSV for this prototype.

What I learned: SAP IDocs carry control records, data records, and status records. Data records contain segment names and payload data, while control records identify sender, receiver, message type, and IDoc type. SAP Help also describes data-record fields like `SEGNAM` and `SDATA`, which is why the sample file keeps document, plant, material, posting date, quantity, unit, vendor, and PO-style fields rather than a toy `fuel_liters` column.

Sources:

- [SAP Help: IDoc Structure, Technical Implementation](https://help.sap.com/docs/SAP_NETWEAVER_740/8f3819b0c24149b5959ab31070b64058/4b38633ead7f74fee10000000a421937.html)
- [SAP Help: Structure of the Data Records](https://help.sap.com/saphelp_gbt10/helpdata/en/d7/5451c8a0b24aa1a71cea3cfacac6b1/content.htm)
- [SAP Help: EDI_DC IDoc Control Record](https://help.sap.com/docs/SAP_ERP/8a10bc7f4f3c4d64a22c819907ca1e57/0095c95360267214e10000000a174cb4.html)

Sample data: `sample_data/sap_fuel_procurement.csv` includes SAP-like document numbers, plant codes, posting dates in multiple formats, German material text, mixed units, vendors, and purchase orders.

What would break: nested IDoc segments, custom Z fields, split invoices, material master changes, and plant codes missing from the client lookup.

## Utility Electricity

Real-world format: facilities team CSV export from a utility portal.

What I learned: Utility data often centers on account, meter, tariff, billing periods, kWh, and demand. UtilityAPI documents that interval availability varies and that meter, bill, and interval objects can differ across utilities, which supports designing a tolerant CSV ingest rather than assuming one universal schema.

Sources:

- [UtilityAPI Docs: Intervals](https://utilityapi.com/docs/api/intervals)
- [UtilityAPI Docs: Billing summaries](https://utilityapi.com/docs/api/accounting/billing-summaries)

Sample data: `sample_data/utility_electricity.csv` includes account number, meter number, service address, site code, non-calendar billing periods, tariff, demand kW, kWh, and charge.

What would break: PDF-only bills, demand ratchets, time-of-use intervals, estimated reads, net metering, renewable tariffs, and market-based Scope 2 accounting.

## Corporate Travel

Real-world format: Concur-like expense/report export.

What I learned: Concur data exposes expense report entries with transaction dates, vendor, expense type, amounts, and configurable fields. SAP Concur travel and expense APIs/documentation show that travel categories differ by flight, hotel, car, and ground transport; distance is not always directly present, so missing-distance flags matter.

Sources:

- [SAP Help: Report Entry Data](https://help.sap.com/docs/CONCUR_EXPENSE/bb83754b1c5541808d50c09901e11475/d4975d91f9e04d7c96defd095e441847.html)
- [SAP Help: Data Dictionary - Expense Report](https://help.sap.com/docs/SAP_CONCUR/27041ab78c844e679db485fff6f4033f/19c4b9fff2df443dbe42ba518f8cdb72.html)
- [SAP Concur Developer Center: Ground Transportation Direct Connect](https://developer.concur.com/api-reference/direct-connects/ground-transportation/post-reservation-sell.html)

Sample data: `sample_data/concur_travel.csv` includes report id, employee id, expense type, transaction date, vendor, origin/destination, distance, nights, amount, currency, and cost center.

What would break: airport-code-only rows without a distance service, multi-leg itineraries, rail, employee-owned vehicles, hotel itemization, refunds, personal portions, and duplicate expense lines.
