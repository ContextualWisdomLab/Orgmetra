# Candidate application primary references

Verified against primary publisher pages on **2026-08-21**. These references inform terminology, process separation, governance and interoperability. They do not by themselves establish legal compliance, certification, or a required physical database schema.

## APA 7 references

HR Open Standards Consortium, Inc. (2019, November 19). *HR Open Standards Consortium announces approved 4.2 standards.* https://www.hropenstandards.org/news/hr-open-standards-consortium-announces-approved-42-standards

HR Open Standards Consortium, Inc. (n.d.). *Recruiting standards project.* Retrieved August 21, 2026, from https://www.hropenstandards.org/recruiting-standards-project

International Organization for Standardization. (2023). *Human resource management—Guidelines on recruitment (ISO Standard No. 30405:2023).* https://www.iso.org/standard/79488.html

International Organization for Standardization. (2026). *Human resources management systems—Requirements (ISO Standard No. 30201:2026).* https://www.iso.org/standard/90923.html

## Decision relevance

- **ISO 30201:2026:** the publisher lists this as a published International Standard (Edition 1, June 2026) for an HR management system and includes attraction, development and deployment of workers in its scope. Orgmetra uses it as current management-system context; this active PR does not claim conformity or certification.
- **ISO 30405:2023:** the publisher lists Edition 2 as the current published recruitment guidance and describes recruitment as distinct phases and stakeholder-managed processes from attraction through employment. Orgmetra uses that process separation to avoid collapsing all recruiting state onto candidate identity.
- **HR Open Recruiting 4.2:** the Consortium's approved 4.2 announcement describes Recruiting as building on distinct Candidate Record and Position Opening concepts. Orgmetra treats this as interoperability evidence for separately addressable candidate and opening context, not as permission to copy a foreign schema verbatim.
- **Current HR Open Recruiting workgroup:** the current project page states that Recruiting covers exchanges among recruiters, ATS, HRIS/front-office systems, job boards, staffing suppliers and candidates, and that current schema work includes an application form and talent-pipeline use cases. Orgmetra therefore preserves an application identity that can be mapped across boundaries without direct cross-service application-table SQL.

## Implementation inference

The concrete `candidate_application_record` / `candidate_application_stage_record` 3NF and bitemporal shape is an Orgmetra architecture decision derived from its existing tenant, Job, Position, selection-decision and historical-record contracts. None of the cited sources is represented as prescribing these table names, PostgreSQL constraints, UUID policy, RLS design, or exact stage vocabulary.
