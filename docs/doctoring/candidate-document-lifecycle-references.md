# Candidate document lifecycle references

These sources inform the proposed candidate-document lifecycle boundary (ADR 0303). They do not establish certification, jurisdiction-specific legal compliance, or permission to collect, retain, return, or destroy any particular document.

## Korean authority

### 채용절차의 공정화에 관한 법률 (채용절차법)

- 제3조·제11조 (적용 범위, 채용서류 반환): https://www.law.go.kr/LSW/lsInfoP.do?ancYnChk=0&lsId=011990
- 시행령 제2조 (반환 기한 14일): https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&joBrNo=00&joNo=0002&lsiSeq=209867&urlMode=lsScJoRltInfoR
- 시행령 제3·4조 (보관 및 반환 청구기간 14~180일) 구조 확인: https://www.lawmaking.go.kr/lmSts/govLm/2000000106350/detailRP

채용절차법은 원칙적으로 상시 30명 이상 사업/사업장의 채용절차에 적용되고(제3조), 채용 확정 후 미채용자가 반환을 청구하면 본인확인 후 채용서류를 반환하도록 한다(제11조). 홈페이지/전자우편 제출 또는 구인자 요구 없이 자발적으로 제출한 경우에는 반환의무 예외가 있다. 시행령은 반환 청구를 받은 날부터 14일 이내 반환(제2조), 미청구 서류는 구인자가 정한 반환 청구기간까지 보관(제3조), 반환 청구기간은 채용 여부 확정일 이후 14일부터 180일까지 범위에서 정하고 확정 전에 고지(제4조)하도록 한다.

### 개인정보 보호법 (PIPA)

- 2026-09-11 시행 법률 제21445호 기준: https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=283839&viewCls=lsRvsDocInfoR
- 제15조 (수집·이용의 법정 근거): https://law.go.kr/lsLinkCommonInfo.do?ancYnChk=&chrClsCd=010202&lsJoLnkSeq=1020398481
- 제18조 (목적 외 이용 제한): https://law.go.kr/lsLinkCommonInfo.do?chrClsCd=010202&lsJoLnkSeq=1020398985
- 제21조 (파기, 분리 보관): https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&joBrNo=00&joNo=0021&lsiSeq=270351&urlMode=lsScJoRltInfoR

제15조는 동의, 법령상 의무, 계약 체결 과정, 정당한 이익 등 법정 근거 안에서 수집·이용하도록 하고, 제18조는 목적 범위를 넘는 이용을 원칙적으로 제한한다. 제21조는 보유기간 경과·목적 달성 등 개인정보가 불필요해지면 지체 없이 파기하고, 다른 법령 때문에 보존해야 하는 경우에는 다른 개인정보와 분리 저장·관리하도록 한다.

### 근로기준법 및 시행령

- 근로기준법 제42조 (근로자 명부·계약서류 3년 보존): https://www.law.go.kr/법령/근로기준법
- 근로기준법 시행령 제22조 (보존 대상·기산점 구분): https://www.law.go.kr/법령/근로기준법시행령

근로기준법 제42조는 근로자 명부와 대통령령상 중요한 근로계약 관련 서류를 3년간 보존하도록 한다. 시행령 제22조는 근로계약서, 임금대장, 임금 결정·지급 및 계산 기초 서류, 고용·해고·퇴직, 승급·감급, 휴가 등 대상과 기산점을 구분한다.

## Applied boundary

Orgmetra therefore keeps four obligations separate rather than merging them into one clock:

- **Return vs. destruction:** a return-workflow exception (for example, email submission) is not read as a retention exemption. Return eligibility and PIPA retention/destruction are computed as separate states.
- **Talent pool as its own purpose:** enrollment is never auto-created from an application. It carries its own purpose, lawful basis/consent version, `granted_at`, `expires_at`, and `revoked_at`, and withdrawal/expiry removes the person from search/recommendation eligibility into the deletion workflow.
- **Minimum materialization on hire:** only the minimum approved fields/document references needed as statutory worker/employment records transfer to `people_core`; the rest stays under the candidate retention policy.
- **Statutory retention with distinct anchors:** each record category computes its three-year retention from its own authoritative starting event, fails closed against early deletion, and also fails closed against continued retention past the period without a separate basis.

Applicability is modeled as an effective-dated, versioned policy keyed on tenant, employer size, and jurisdiction, not as a global constant. Return/deletion obligations, legal hold, and jurisdiction-specific legal review remain separate determinations; this boundary does not replace legal advice.

Implementation PRs must pin any additional acceptance source (for example, an exact 고용노동부 노무관리 guidebook publication artifact and date) in `docs/TRACEABILITY` rather than relying on a moving web resource.
