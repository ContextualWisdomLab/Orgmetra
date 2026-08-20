# Organization hierarchy snapshot references

Retrieved and rechecked August 21, 2026 against official ISO primary sources.

## Why these sources are material

The active Orgmetra hierarchy-snapshot slice reconstructs organization structure at an explicit effective date and system-recorded knowledge cutoff and emits deterministic evidence for authorized HR use. The implementation remains an Orgmetra technical control; these standards inform terminology, management-system context, and reporting discipline rather than serving as executable product requirements. No conformity or certification claim is made.

ISO 30201:2026 is the current published requirements standard for human resources management systems and explicitly addresses operational planning/control, workforce planning, documented information, roles/responsibilities, and continual improvement. Orgmetra uses that context to keep historical organization evidence reproducible and attributable rather than treating a mutable current hierarchy as sufficient audit truth.

ISO 30400:2022 is the current published HR-management vocabulary standard. Orgmetra keeps Organization, Job, Position, Assignment, Person, and Employment as distinct domain concepts and does not infer worker or managerial authority merely from one parent-link snapshot.

ISO 30414:2025 is the current second edition for human-capital reporting and disclosure. It includes workforce composition among its reporting areas. The hierarchy snapshot is structural evidence only; it does not itself calculate workforce-composition, diversity, turnover, or protected-attribute metrics.

## APA 7 references

International Organization for Standardization. (2022). *ISO 30400:2022 Human resource management—Vocabulary* (2nd ed.). https://www.iso.org/standard/78044.html

International Organization for Standardization. (2025). *ISO 30414:2025 Human resource management—Requirements and recommendations for human capital reporting and disclosure* (2nd ed.). https://www.iso.org/standard/86106.html

International Organization for Standardization. (2026). *ISO 30201:2026 Human resources management systems—Requirements* (1st ed.). https://www.iso.org/standard/90923.html

## Internal technical references

- `docs/adr/0001-orgmetra-authoritative-hris-record.md`
- `docs/adr/0003-bitemporal-hris-data-contract.md`
- `packages/hris-kernel/src/orgmetra_hris_kernel/organization.py`
- `docs/traceability/organization-hierarchy-snapshot.md`
