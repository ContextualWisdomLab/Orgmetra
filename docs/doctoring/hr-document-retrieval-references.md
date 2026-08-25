# Doctoring — HR document retrieval references

This note records primary public standards and primary packaging-release evidence used as design evidence for the active HR document retrieval PR. It does not claim certification, regulatory compliance, or legal entitlement to disclose any particular employee document.

## Design implications

- **NIST Privacy Framework 1.0** is the current final NIST Privacy Framework baseline used by this design. It motivates explicit data-processing purpose, data minimization, privacy-risk management, and controlled data processing. NIST is separately developing Privacy Framework 1.1; current NIST material identifies that work as an Initial Public Draft, so this ADR does not treat 1.1 as a final standard.
- **NIST SP 800-53 Rev. 5 / Release 5.2.0** supplies current security/privacy control vocabulary relevant to access control, Audit and Accountability, PII Processing and Transparency, and System and Information Integrity. The package uses those families as design evidence for deny-by-default exact-scope authorization, immutable audit-before-release, minimized receipts, and content-integrity verification.
- **PyPI setuptools 84.0.0** is the reviewed build backend for the package's no-build-isolation installation smoke test. PyPI publishes the `setuptools-84.0.0-py3-none-any.whl` SHA-256 as `51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670`; the workflow installs that exact wheel through a hash-locked requirement before invoking `setuptools.build_meta`. The package wheel is then built from the exact Git checkout, its SHA-256 is computed locally, and isolated installation requires that same digest. The public support declaration is intentionally bounded to Python `>=3.14,<3.15` because the exact quality lane executes CPython 3.14.7 rather than claiming untested older or future minor compatibility.
- These sources are risk/control and build-evidence references rather than proof that an Orgmetra deployment conforms to NIST, SOC 2, CSAP, or any legal regime. Deployment-specific policy, identity assurance, retention/legal-hold rules, storage protections, audit durability, and release signing remain separately testable responsibilities.

## APA 7 references

National Institute of Standards and Technology. (2020). *NIST Privacy Framework: A tool for improving privacy through enterprise risk management, version 1.0* (NIST CSWP 10). U.S. Department of Commerce. https://doi.org/10.6028/NIST.CSWP.01162020

Joint Task Force. (2020). *Security and privacy controls for information systems and organizations* (NIST Special Publication 800-53, Revision 5; current control catalog Release 5.2.0). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-53r5

Python Packaging Authority. (2026, August 8). *setuptools 84.0.0*. Python Package Index. https://pypi.org/project/setuptools/84.0.0/

## Verification notes

Primary NIST pages were rechecked on 2026-08-25. NIST's Privacy Framework page identifies Version 1.0 and separately advertises the Privacy Framework 1.1 Initial Public Draft. The NIST SP 800-53 page identifies Rev. 5 as final and links the current Release 5.2.0 supplemental/control-catalog update. PyPI was rechecked on 2026-08-25 and reports setuptools 84.0.0 as released 2026-08-08, compatible with Python >=3.10, with the reviewed universal wheel SHA-256 recorded above.
