# Employment employing-organization evidence note

## Question

Why does Orgmetra model an Employment's employing legal organization separately from Position and Assignment?

## Current authoritative standard evidence

ISO 30414:2025 is the published second edition of *Human resource management — Requirements and recommendations for human capital reporting and disclosure*. ISO lists workforce composition among the standard's core human-capital reporting areas and states that the standard is intended to support comprehensive internal and external human-capital reporting across organizations of different sizes and sectors.

Orgmetra uses that published standard only as reporting-context evidence that workforce composition needs defensible organizational scope. ISO 30414 does not define this database schema and does not by itself determine the legal employer for any jurisdiction.

## Product implication

A Position is an organizational seat. An Employment is the durable worker-employment relationship. Treating `position_record.organization_unit_id` as the legal employer would therefore make a seat transfer silently change employment-contract scope and would make a legal-employer transfer indistinguishable from a seat move.

The active PR instead records a tenant-scoped, bitemporal `employment_employing_organization_record` relationship. The referenced Organization must be `legal_entity` over the full effective interval at the row's recorded-time coordinate, while the same interval must be covered by active/leave Employment truth. No payroll, withholding, tax, statutory-accounting, benefits, compensation, candidate, performance, or model-output fields are added.

This is an HRIS source-of-truth relationship, not a claim of payroll or statutory-system ownership.

## Reference (APA 7)

International Organization for Standardization. (2025). *ISO 30414:2025 Human resource management — Requirements and recommendations for human capital reporting and disclosure* (2nd ed.). ISO. https://www.iso.org/standard/30414
