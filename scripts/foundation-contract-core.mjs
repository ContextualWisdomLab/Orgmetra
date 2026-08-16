/**
 * Dependency-free validation for Orgmetra's durable foundation artifacts.
 *
 * This module is production-quality repository tooling: it validates the
 * documentation and naming contract without installing application packages.
 */

import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';

/** Canonical artifacts required before implementation claims are reviewable. */
export const REQUIRED_FILES = Object.freeze([
  'README.md',
  'AGENTS.md',
  'CLAUDE.md',
  'ARCHITECTURE.md',
  'CHANGELOG.md',
  '.gitignore',
  'LICENSE',
  'NOTICE',
  'manifest.json',
  'package.json',
  '.github/workflows/foundation-ci.yml',
  'docs/PRD.md',
  'docs/TRD.md',
  'docs/USER_STORIES.md',
  'docs/STORYBOARD.md',
  'docs/WIREFRAMES.md',
  'docs/STORYBOOK.md',
  'docs/UML.md',
  'docs/ERD.md',
  'docs/DATA_MODEL.md',
  'docs/API_CONTRACT.md',
  'docs/SECURITY.md',
  'docs/THREAT_MODEL.md',
  'docs/TEST_STRATEGY.md',
  'docs/OPERABILITY.md',
  'docs/TRACEABILITY.md',
  'docs/adr/README.md',
  'docs/adr/0001-orgmetra-authoritative-hris-record.md',
  'docs/adr/0002-federated-cwl-integration-boundaries.md',
  'docs/adr/0003-bitemporal-hris-data-contract.md',
  'docs/doctoring/REFERENCES.md',
  'docs/superpowers/specs/2026-08-15-orgmetra-foundation-design.md',
  'docs/superpowers/plans/2026-08-15-orgmetra-foundation-implementation-plan.md',
  'database/migrations/0001_foundation_schema.sql',
  'database/migrations/0002_sealed_evidence_digest.sql',
  'schemas/openapi.yaml',
  'scripts/foundation-contract-core.mjs',
  'scripts/foundation-contract.mjs',
  'tests/foundation-contract.test.mjs',
  'tests/openapi-contract.test.mjs',
  'tests/test_bitemporal_postgres.sh',
  'tests/test_tenant_isolation_postgres.sh',
  'tests/test_evidence_sealing_postgres.sh',
  'tests/validate_repository.py'
]);

/** Exact maturity vocabulary accepted by traceability tables. */
export const MATURITY_VALUES = Object.freeze(new Set([
  'implemented_on_protected_main',
  'implemented_on_active_pr',
  'accepted_architecture',
  'planned',
  'research_only',
  'superseded',
  'out_of_scope'
]));

/** Logical database objects governed by the initial naming contract. */
export const DATABASE_OBJECT_NAMES = Object.freeze([
  'tenant_record', 'person_record', 'person_name_record', 'person_contact_record',
  'external_identity_link', 'employment_record', 'employment_contract',
  'employment_status_history', 'employment_transition', 'legal_entity',
  'organization_unit', 'organization_relation', 'business_location',
  'cost_center_record', 'job_family', 'job_profile', 'job_profile_version',
  'position_record', 'position_relation', 'assignment_record',
  'job_analysis_case', 'source_record', 'source_version', 'task_statement',
  'task_rating', 'fja_function', 'task_fja_link', 'ksao_requirement',
  'task_ksao_link', 'qualification_rule', 'candidate_profile',
  'requisition_record', 'application_record', 'application_stage_history',
  'candidate_evidence_link', 'assessment_assignment', 'interview_session',
  'interview_rating', 'selection_decision', 'decision_evidence_link',
  'candidate_worker_link', 'criterion_blueprint', 'criterion_dimension',
  'criterion_indicator', 'work_opportunity', 'criterion_observation',
  'performance_cycle', 'performance_decision', 'compensation_record',
  'compensation_decision', 'validation_study', 'study_population_snapshot',
  'study_predictor_link', 'study_criterion_link', 'analysis_manifest',
  'analysis_artifact', 'policy_recommendation', 'policy_review_decision',
  'document_record', 'document_version', 'document_segment', 'image_artifact',
  'evidence_record', 'evidence_source_segment', 'authorization_policy',
  'authorization_decision', 'audit_event', 'data_rights_request',
  'outbox_event', 'inbox_event', 'integration_delivery'
]);

const UNFINISHED_MARKER_PATTERN = /(?:^|\n)\s*(?:#{1,6}\s+|[-*+]\s+)?(?:\[(?:TODO|TBD|FIXME)\]|\{\{(?:TODO|TBD|FIXME)\}\}|<(?:TODO|TBD|FIXME)>|(?:TODO|TBD|FIXME)(?:\s*:|\s*$))/im;
const ADR_STATUS_PATTERN = /^\|\s*\[\d{4}\]\(([^)]+)\)\s*\|.*\|\s*(Proposed|Accepted|Superseded|Rejected)\s*\|$/;
const LOCAL_LINK_PATTERN = /\[[^\]]+\]\((?!https?:\/\/|mailto:|#)([^)]+)\)/g;

/** Recursively collect Markdown files in stable lexical order. */
export function collectMarkdownFiles(directoryPath) {
  if (!existsSync(directoryPath)) return [];
  const files = [];
  for (const entryName of readdirSync(directoryPath).sort()) {
    const entryPath = join(directoryPath, entryName);
    if (statSync(entryPath).isDirectory()) {
      files.push(...collectMarkdownFiles(entryPath));
    } else if (entryName.endsWith('.md')) {
      files.push(entryPath);
    }
  }
  return files;
}

/** Count Markdown code-fence markers that begin a line. */
export function countCodeFences(markdownText) {
  return markdownText.split(/\r?\n/).filter((line) => /^\s*```/.test(line)).length;
}

/** Return whether Markdown contains an explicit unfinished-work marker. */
export function hasUnfinishedMarker(markdownText) {
  return UNFINISHED_MARKER_PATTERN.test(markdownText);
}

/** Return whether a database object is descriptive multiword snake_case. */
export function isValidDatabaseObjectName(objectName) {
  return /^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$/.test(objectName);
}

/** Validate a collection of database object names. */
export function validateDatabaseObjectNames(objectNames = DATABASE_OBJECT_NAMES) {
  return objectNames
    .filter((objectName) => !isValidDatabaseObjectName(objectName))
    .map((objectName) => `Invalid database object name: ${objectName}`);
}

/** Extract a level-two Markdown section. */
export function extractSection(markdownText, headingText) {
  const heading = `## ${headingText}`;
  const startIndex = markdownText.indexOf(heading);
  if (startIndex < 0) return '';
  const remainder = markdownText.slice(startIndex + heading.length);
  const nextHeading = remainder.search(/\n## /);
  return nextHeading < 0 ? remainder : remainder.slice(0, nextHeading);
}

/** Parse final table cells that look like maturity values. */
export function extractMaturityCells(sectionText) {
  const values = [];
  for (const line of sectionText.split(/\r?\n/)) {
    if (!line.startsWith('|') || /^\|[-\s|]+\|$/.test(line)) continue;
    const cells = line.split('|').slice(1, -1).map((cell) => cell.trim());
    const lastCell = cells.at(-1);
    if (lastCell && /^[a-z_]+$/.test(lastCell) && lastCell !== 'maturity') {
      values.push(lastCell);
    }
  }
  return values;
}

/** Validate local Markdown links from one source file. */
export function validateLocalLinks(filePath, markdownText) {
  const errors = [];
  LOCAL_LINK_PATTERN.lastIndex = 0;
  for (const match of markdownText.matchAll(LOCAL_LINK_PATTERN)) {
    const rawTarget = match[1].split('#', 1)[0];
    const targetPath = resolve(dirname(filePath), decodeURIComponent(rawTarget));
    if (!existsSync(targetPath)) {
      errors.push(`${filePath}: local link target does not exist: ${match[1]}`);
    }
  }
  return errors;
}

/** Validate the ADR index, referenced files, and indexed statuses. */
export function validateAdrIndex(rootPath) {
  const indexPath = join(rootPath, 'docs/adr/README.md');
  if (!existsSync(indexPath)) return [];
  const errors = [];
  const indexText = readFileSync(indexPath, 'utf8');
  for (const line of indexText.split(/\r?\n/)) {
    const match = line.match(ADR_STATUS_PATTERN);
    if (!match) continue;
    const adrPath = resolve(dirname(indexPath), match[1]);
    if (!existsSync(adrPath)) {
      errors.push(`${relative(rootPath, indexPath)}: indexed ADR is missing: ${match[1]}`);
      continue;
    }
    if (!readFileSync(adrPath, 'utf8').includes(`Status: ${match[2]}`)) {
      errors.push(`${relative(rootPath, adrPath)}: status does not match ADR index (${match[2]})`);
    }
  }
  return errors;
}

function indentationWidth(line) {
  return line.length - line.trimStart().length;
}

function extractYamlBlock(yamlText, exactMarker) {
  const lines = yamlText.split(/\r?\n/);
  const startIndex = lines.findIndex((line) => line === exactMarker);
  if (startIndex < 0) return '';
  const markerIndent = indentationWidth(exactMarker);
  const blockLines = [];
  for (let index = startIndex + 1; index < lines.length; index += 1) {
    const line = lines[index];
    if (line.trim() && indentationWidth(line) <= markerIndent) break;
    blockLines.push(line);
  }
  return blockLines.join('\n');
}

function requireWithin(errors, label, blockText, fragment, description) {
  if (!blockText.includes(fragment)) {
    errors.push(`${label}: missing ${description}`);
  }
}

/**
 * Validate OpenAPI authorization and command contracts at their actual YAML boundaries.
 *
 * This intentionally parses only the indentation-stable subset used by the checked-in
 * contract. It is deterministic, dependency-free, and rejects a requirement moved to
 * an unrelated operation or schema instead of treating global substring presence as proof.
 */
export function validateOpenApiContract(openapiText) {
  const errors = [];
  if (!openapiText.startsWith('openapi: 3.2.0\n')) {
    errors.push('OpenAPI document: expected version 3.2.0');
  }

  const operationContracts = [
    {
      pathMarker: '  /person-records:',
      operationId: 'createPersonRecord',
      scope: 'orgmetra.people.write',
      requestSchema: 'CreatePersonRecordCommand',
      extraResponses: []
    },
    {
      pathMarker: '  /job-profiles:',
      operationId: 'createJobProfile',
      scope: 'orgmetra.job_architecture.write',
      requestSchema: 'CreateJobProfileCommand',
      extraResponses: []
    },
    {
      pathMarker: '  /selection-decisions:',
      operationId: 'recordSelectionDecision',
      scope: 'orgmetra.talent_acquisition.write',
      requestSchema: 'RecordSelectionDecisionCommand',
      extraResponses: ["        '422':"]
    }
  ];

  for (const contract of operationContracts) {
    const pathBlock = extractYamlBlock(openapiText, contract.pathMarker);
    if (!pathBlock) {
      errors.push(`${contract.operationId}: path block is missing`);
      continue;
    }
    requireWithin(errors, contract.operationId, pathBlock, `operationId: ${contract.operationId}`, 'operationId');
    requireWithin(errors, contract.operationId, pathBlock, `            - ${contract.scope}`, `least-privilege scope ${contract.scope}`);
    for (const parameterName of ['IdempotencyKey', 'TenantReference', 'ActorReference', 'PurposeCode']) {
      requireWithin(
        errors,
        contract.operationId,
        pathBlock,
        `$ref: '#/components/parameters/${parameterName}'`,
        `required parameter ${parameterName}`
      );
    }
    requireWithin(
      errors,
      contract.operationId,
      pathBlock,
      `$ref: '#/components/schemas/${contract.requestSchema}'`,
      `request body binding ${contract.requestSchema}`
    );
    for (const responseCode of ["        '201':", "        '400':", "        '401':", "        '403':", "        '409':", ...contract.extraResponses]) {
      requireWithin(errors, contract.operationId, pathBlock, responseCode, `response ${responseCode.trim()}`);
    }
    requireWithin(errors, contract.operationId, pathBlock, '            Location:', '201 Location header');
  }

  const jobCommand = extractYamlBlock(openapiText, '    CreateJobProfileCommand:');
  if (!jobCommand) {
    errors.push('CreateJobProfileCommand: schema block is missing');
  } else {
    requireWithin(
      errors,
      'CreateJobProfileCommand',
      jobCommand,
      '        - evidence_references',
      'required evidence_references'
    );
    requireWithin(errors, 'CreateJobProfileCommand', jobCommand, '          maxItems: 100', 'evidence_references maxItems 100');
    requireWithin(errors, 'CreateJobProfileCommand', jobCommand, '          uniqueItems: true', 'unique evidence_references');
  }

  const decisionCommand = extractYamlBlock(openapiText, '    RecordSelectionDecisionCommand:');
  if (!decisionCommand) {
    errors.push('RecordSelectionDecisionCommand: schema block is missing');
  } else {
    requireWithin(
      errors,
      'RecordSelectionDecisionCommand',
      decisionCommand,
      '        - evidence_references',
      'required evidence_references'
    );
    requireWithin(errors, 'RecordSelectionDecisionCommand', decisionCommand, '        - confirmation_reference', 'human confirmation reference');
    requireWithin(errors, 'RecordSelectionDecisionCommand', decisionCommand, '          maxItems: 100', 'evidence_references maxItems 100');
    requireWithin(errors, 'RecordSelectionDecisionCommand', decisionCommand, '          uniqueItems: true', 'unique evidence_references');
  }

  const errorSchema = extractYamlBlock(openapiText, '    ErrorResponse:');
  if (!errorSchema) {
    errors.push('ErrorResponse: schema block is missing');
  } else {
    for (const fieldName of ['error_code', 'message', 'next_action', 'support_reference']) {
      requireWithin(errors, 'ErrorResponse', errorSchema, `        - ${fieldName}`, `required field ${fieldName}`);
    }
    requireWithin(
      errors,
      'ErrorResponse',
      errorSchema,
      'Opaque random client-safe support identifier.',
      'opaque support-reference semantics'
    );
  }

  if (/^\s*(?:-\s+)?trace_id\s*:/m.test(openapiText)) {
    errors.push('OpenAPI document: internal trace identifiers must not be client-visible');
  }
  if (openapiText.includes('keyverse_oidc: []')) {
    errors.push('OpenAPI document: empty-scope OIDC requirements are forbidden');
  }
  return errors;
}

/**
 * Validate the complete foundation repository contract rooted at `rootPath`.
 *
 * The returned array is empty only when required artifacts, Markdown structure,
 * explicit unfinished-work markers, local links, database naming, traceability
 * maturities, OpenAPI structural contracts, and ADR index/status relationships
 * all satisfy their deterministic checks. The function is read-only and returns
 * operator-readable errors instead of throwing for ordinary validation failures.
 */
export function validateFoundation(rootPath) {
  const resolvedRoot = resolve(rootPath);
  if (!existsSync(resolvedRoot)) return [`Repository root does not exist: ${resolvedRoot}`];

  const errors = [];
  for (const requiredPath of REQUIRED_FILES) {
    if (!existsSync(join(resolvedRoot, requiredPath))) {
      errors.push(`Missing required foundation artifact: ${requiredPath}`);
    }
  }

  const rootMarkdown = ['README.md', 'AGENTS.md', 'CLAUDE.md', 'ARCHITECTURE.md', 'CHANGELOG.md']
    .map((fileName) => join(resolvedRoot, fileName))
    .filter((filePath) => existsSync(filePath));
  const markdownFiles = [...rootMarkdown, ...collectMarkdownFiles(join(resolvedRoot, 'docs'))];

  for (const filePath of markdownFiles) {
    const text = readFileSync(filePath, 'utf8');
    const displayPath = relative(resolvedRoot, filePath);
    if (hasUnfinishedMarker(text)) errors.push(`${displayPath}: unresolved work marker`);
    if (countCodeFences(text) % 2 !== 0) errors.push(`${displayPath}: unbalanced Markdown code fence`);
    errors.push(...validateLocalLinks(filePath, text)
      .map((message) => message.replace(`${filePath}:`, `${displayPath}:`)));
  }

  errors.push(...validateDatabaseObjectNames());

  const traceabilityPath = join(resolvedRoot, 'docs/TRACEABILITY.md');
  if (existsSync(traceabilityPath)) {
    const traceabilityText = readFileSync(traceabilityPath, 'utf8');
    for (const sectionName of ['2. Product traceability matrix', '4. CWL integration traceability']) {
      const sectionText = extractSection(traceabilityText, sectionName);
      if (!sectionText) {
        errors.push(`docs/TRACEABILITY.md: missing section ${sectionName}`);
        continue;
      }
      for (const maturityValue of extractMaturityCells(sectionText)) {
        if (!MATURITY_VALUES.has(maturityValue)) {
          errors.push(`docs/TRACEABILITY.md: invalid maturity value: ${maturityValue}`);
        }
      }
    }
  }

  const openapiPath = join(resolvedRoot, 'schemas/openapi.yaml');
  if (existsSync(openapiPath)) {
    errors.push(...validateOpenApiContract(readFileSync(openapiPath, 'utf8')));
  }

  errors.push(...validateAdrIndex(resolvedRoot));
  return errors;
}

/** Run validation as a CLI and return a process-compatible exit code. */
export function runCli(rootPath, outputStream = process.stdout, errorStream = process.stderr) {
  const errors = validateFoundation(rootPath);
  if (errors.length === 0) {
    outputStream.write(`${JSON.stringify({ status: 'passed', error_count: 0 })}\n`);
    return 0;
  }
  errorStream.write(`${JSON.stringify({ status: 'failed', error_count: errors.length, errors }, null, 2)}\n`);
  return 1;
}
