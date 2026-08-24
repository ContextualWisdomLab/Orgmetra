# Employment absence truth references

Checked against primary/official sources on 2026-08-25.

## APA 7 references

European Parliament & Council of the European Union. (2016). *Regulation (EU) 2016/679 ... (General Data Protection Regulation), Article 5*. EUR-Lex. https://eur-lex.europa.eu/eli/reg/2016/679/

National Institute of Standards and Technology. (2020). *NIST Privacy Framework: A tool for improving privacy through enterprise risk management, version 1.0*. U.S. Department of Commerce. https://www.nist.gov/privacy-framework/privacy-framework

National Institute of Standards and Technology. (2025). *NIST Privacy Framework 1.1 initial public draft (CSWP 40)*. U.S. Department of Commerce. https://csrc.nist.gov/pubs/cswp/40/nist-privacy-framework-11/ipd

U.S. Department of Labor, Wage and Hour Division. (2025). *Fact Sheet #28A: Employee protections under the Family and Medical Leave Act*. https://www.dol.gov/agencies/whd/fact-sheets/28a-fmla-employee-protections

## Design use

- GDPR Article 5(c) is used only as a primary-source example of the data-minimization principle: core operational absence evidence should be limited to what its operational purpose needs. Orgmetra does **not** infer that every tenant or absence is governed by the GDPR.
- NIST Privacy Framework 1.0 is the current final framework published on NIST's primary framework page at the time of review. NIST Privacy Framework 1.1 remains an Initial Public Draft / forthcoming update, so this implementation does not present 1.1 as a final standard.
- The U.S. Department of Labor fact sheet demonstrates that leave can carry legally significant family/medical reasons and employment protections. It is used to justify separating operational absence truth from jurisdiction-specific case/entitlement details, not to implement FMLA eligibility or legal conclusions.

## Architecture conclusion

The HRIS kernel therefore stores only the reason-free operational absence coordinate needed to reconstruct Employment availability. Jurisdiction-specific eligibility, certification, entitlement, medical/family details, benefit calculations, discipline, and return-to-work decisions remain purpose-bound downstream workflows with human authority and immutable evidence.
