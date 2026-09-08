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
  'docs/adr/0004-employment-position-version-and-assignment-binding.md',
  'docs/adr/0005-exclusive-employment-and-staffable-seats.md',
  'docs/adr/0006-governed-audit-outbox-envelope.md',
  'docs/adr/0007-governed-job-analysis-evidence.md',
  'docs/adr/0008-purpose-bound-pii-authorization.md',
  'docs/adr/0009-performance-criterion-observation-scope.md',
  'docs/adr/0010-naruon-calendar-intent-boundary.md',
  'docs/adr/0011-bitemporal-workforce-composition.md',
  'docs/adr/0012-governed-migration-handoff.md',
  'docs/adr/0013-governed-requisition-review-packet.md',
  'docs/adr/0014-job-analysis-snapshot-persistence.md',
  'docs/doctoring/REFERENCES.md',
  'docs/superpowers/specs/2026-08-15-orgmetra-foundation-design.md',
  'docs/superpowers/plans/2026-08-15-orgmetra-foundation-implementation-plan.md',
  'database/migrations/0001_foundation_schema.sql',
  'database/migrations/0002_sealed_evidence_digest.sql',
  'database/migrations/0003_audit_outbox_persistence.sql',
  'database/migrations/0004_outbox_delivery_claim.sql',
  'database/migrations/0005_outbox_delivery_finalization.sql',
  'database/migrations/0006_outbox_delivery_dead_letter.sql',
  'database/migrations/0007_outbox_retry_exhaustion.sql',
  'database/migrations/0008_audit_outbox_review_hardening.sql',
  'database/migrations/0009_candidate_worker_conversion_governance.sql',
  'database/migrations/0010_validity_study_case_integrity.sql',
  'database/migrations/0011_criterion_observation_scope.sql',
  'database/migrations/0012_people_mutation_idempotency.sql',
  'database/migrations/0013_job_analysis_snapshot.sql',
  'packages/hris-kernel/src/orgmetra_hris_kernel/audit.py',
  'packages/hris-kernel/tests/test_audit_outbox.py',
  'schemas/openapi.yaml',
  'scripts/foundation-contract-core.mjs',
  'scripts/foundation-contract.mjs',
  'tests/dispatcher-inventory.test.mjs',
  'tests/foundation-contract.test.mjs',
  'tests/openapi-contract.test.mjs',
  'tests/test_bitemporal_postgres.sh',
  'tests/test_tenant_isolation_postgres.sh',
  'tests/test_evidence_sealing_postgres.sh',
  'tests/test_operational_uuid_postgres.sh',
  'tests/test_audit_outbox_postgres.sh',
  'tests/test_outbox_claim_postgres.sh',
  'tests/test_outbox_dead_letter_postgres.sh',
  'tests/test_audit_outbox_hardening_postgres.sh',
  'tests/test_candidate_worker_conversion_postgres.sh',
  'tests/test_validity_study_case_postgres.sh',
  'tests/test_criterion_observation_scope_postgres.sh',
  'tests/test_people_mutation_idempotency_postgres.sh',
  'tests/test_job_analysis_snapshot_postgres.sh',
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
  'external_identity_link', 'employment_record', 'employment_record_version',
  'employment_contract', 'employment_status_history', 'employment_transition',
  'legal_entity',
  'organization_unit', 'organization_relation', 'business_location',
  'cost_center_record', 'job_family', 'job_profile', 'job_profile_version',
  'position_record', 'position_record_version', 'position_relation',
  'assignment_record',
  'job_analysis_snapshot', 'job_analysis_task_item', 'job_analysis_ksao_item',
  'job_analysis_task_ksao_link', 'job_analysis_write_command',
  'qualification_rule', 'candidate_profile',
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
  'authorization_decision', 'audit_event', 'audit_event_record', 'data_rights_request',
  'outbox_event', 'outbox_delivery_record', 'outbox_delivery_escalation_record',
  'people_mutation_idempotency_record', 'inbox_event', 'integration_delivery'
]);

/** Migration-backed logical objects whose persisted table identity must not drift. */
export const MIGRATION_BACKED_DATABASE_OBJECT_NAMES = Object.freeze([
  'people_mutation_idempotency_record',
  'job_analysis_snapshot',
  'job_analysis_task_item',
  'job_analysis_ksao_item',
  'job_analysis_task_ksao_link',
  'job_analysis_write_command'
]);

const UNFINISHED_MARKER_LINE_PATTERN = /^\s*(?:#{1,6}\s+|[-*+]\s+)?(?:\[(?:TODO|TBD|FIXME)\]|\{\{(?:TODO|TBD|FIXME)\}\}|<(?:TODO|TBD|FIXME)>|(?:TODO|TBD|FIXME)(?:\s*:\s*.*)?\s*)$/i;
const ADR_STATUS_PATTERN = /^\|\s*\[\d{4}\]\(([^)]+)\)\s*\|.*\|\s*(Proposed|Accepted|Superseded|Rejected)\s*\|$/;
const LOCAL_LINK_PATTERN = /\[[^\]]+\]\((?!https?:\/\/|mailto:|#)([^)]+)\)/g;
const CREATE_TABLE_PATTERN = /\bCREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+(?:[a-z_][a-z0-9_]*\.)?([a-z_][a-z0-9_]*)/gi;
const DOLLAR_QUOTE_START_PATTERN = /^\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$/;

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

/** Return the first explicit unfinished-work marker and its one-based line. */
export function findUnfinishedMarker(markdownText) {
  const lines = markdownText.split(/\r?\n/);
  for (let index = 0; index < lines.length; index += 1) {
    if (!UNFINISHED_MARKER_LINE_PATTERN.test(lines[index])) continue;
    return Object.freeze({
      line: index + 1,
      marker: lines[index].trim()
    });
  }
  return null;
}

/** Return whether Markdown contains an explicit unfinished-work marker. */
export function hasUnfinishedMarker(markdownText) {
  return findUnfinishedMarker(markdownText) !== null;
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

function maskedSqlCharacter(character) {
  return character === '\n' || character === '\r' ? character : ' ';
}

/**
 * Mask PostgreSQL comments and literal bodies while preserving code positions.
 *
 * Migration inventory is intentionally lexical and dependency-free, but it must
 * never treat DDL-shaped prose as executable SQL. PostgreSQL permits nested block
 * comments, ordinary/escape strings, quoted identifiers, and dollar-quoted
 * bodies; masking those regions prevents false CREATE TABLE evidence while
 * preserving actual unquoted lower-snake-case DDL for the naming contract.
 */
export function maskPostgresNonCode(sqlText) {
  if (typeof sqlText !== 'string') throw new TypeError('sqlText must be a string');
  let output = '';
  let index = 0;

  const maskThrough = (endIndex) => {
    while (index < endIndex) {
      output += maskedSqlCharacter(sqlText[index]);
      index += 1;
    }
  };

  while (index < sqlText.length) {
    if (sqlText.startsWith('--', index)) {
      while (index < sqlText.length && sqlText[index] !== '\n' && sqlText[index] !== '\r') {
        output += ' ';
        index += 1;
      }
      continue;
    }

    if (sqlText.startsWith('/*', index)) {
      let depth = 0;
      while (index < sqlText.length) {
        if (sqlText.startsWith('/*', index)) {
          depth += 1;
          maskThrough(index + 2);
          continue;
        }
        if (sqlText.startsWith('*/', index)) {
          depth -= 1;
          maskThrough(index + 2);
          if (depth === 0) break;
          continue;
        }
        output += maskedSqlCharacter(sqlText[index]);
        index += 1;
      }
      continue;
    }

    if (sqlText[index] === "'" || sqlText[index] === '"') {
      const delimiter = sqlText[index];
      output += ' ';
      index += 1;
      while (index < sqlText.length) {
        if (sqlText[index] === '\\') {
          maskThrough(Math.min(index + 2, sqlText.length));
          continue;
        }
        if (sqlText[index] === delimiter) {
          if (sqlText[index + 1] === delimiter) {
            maskThrough(index + 2);
            continue;
          }
          output += ' ';
          index += 1;
          break;
        }
        output += maskedSqlCharacter(sqlText[index]);
        index += 1;
      }
      continue;
    }

    if (sqlText[index] === '$') {
      const delimiterMatch = sqlText.slice(index).match(DOLLAR_QUOTE_START_PATTERN);
      if (delimiterMatch) {
        const delimiter = delimiterMatch[0];
        maskThrough(index + delimiter.length);
        const closingIndex = sqlText.indexOf(delimiter, index);
        if (closingIndex < 0) {
          maskThrough(sqlText.length);
          continue;
        }
        maskThrough(closingIndex + delimiter.length);
        continue;
      }
    }

    output += sqlText[index];
    index += 1;
  }
  return output;
}

/** Extract created table names from executable regions of one SQL document. */
export function extractCreatedTableNames(sqlText) {
  CREATE_TABLE_PATTERN.lastIndex = 0;
  const executableSql = maskPostgresNonCode(sqlText);
  return new Set([...executableSql.matchAll(CREATE_TABLE_PATTERN)].map((match) => match[1].toLowerCase()));
}

/**
 * Prove that migration-backed logical table identities remain present in both
 * the canonical object inventory and the checked-in migration history.
 */
export function validateMigrationBackedDatabaseObjectNames(
  rootPath,
  objectNames = MIGRATION_BACKED_DATABASE_OBJECT_NAMES
) {
  const migrationDirectory = join(rootPath, 'database/migrations');
  const inventoryNames = new Set(DATABASE_OBJECT_NAMES);
  const createdTableNames = new Set();
  const migrationPrefixes = new Map();
  const errors = [];
  if (existsSync(migrationDirectory)) {
    for (const entryName of readdirSync(migrationDirectory).sort()) {
      if (!/^\d{4}_[a-z0-9_]+\.sql$/.test(entryName)) continue;
      const prefix = entryName.slice(0, 4);
      const prior = migrationPrefixes.get(prefix);
      if (prior) {
        errors.push(`Duplicate migration number prefix ${prefix}: ${prior}, ${entryName}`);
      } else {
        migrationPrefixes.set(prefix, entryName);
      }
      const migrationText = readFileSync(join(migrationDirectory, entryName), 'utf8');
      for (const tableName of extractCreatedTableNames(migrationText)) createdTableNames.add(tableName);
    }
  }

  for (const objectName of objectNames) {
    if (!inventoryNames.has(objectName)) {
      errors.push(`Database object inventory omitted migration-backed object: ${objectName}`);
    }
    if (!createdTableNames.has(objectName)) {
      errors.push(`Migration-backed database object is missing from migrations: ${objectName}`);
    }
  }
  return errors;
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
    },
    {
      pathMarker: '  /employment-records:',
      operationId: 'createEmploymentRecord',
      scope: 'orgmetra.people.write',
      requestSchema: 'CreateEmploymentRecordCommand',
      extraResponses: []
    },
    {
      pathMarker: '  /position-records:',
      operationId: 'createPositionRecord',
      scope: 'orgmetra.job_architecture.write',
      requestSchema: 'CreatePositionRecordCommand',
      extraResponses: []
    },
    {
      pathMarker: '  /assignment-records:',
      operationId: 'createAssignmentRecord',
      scope: 'orgmetra.people.write',
      requestSchema: 'CreateAssignmentRecordCommand',
      extraResponses: []
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

  const jobAnalysisWrite = extractYamlBlock(openapiText, '  /tenants/{tenant_record_id}/job-analysis-snapshots:');
  if (!jobAnalysisWrite) {
    errors.push('persistJobAnalysisSnapshot: path block is missing');
  } else {
    requireWithin(errors, 'persistJobAnalysisSnapshot', jobAnalysisWrite, 'operationId: persistJobAnalysisSnapshot', 'operationId');
    requireWithin(errors, 'persistJobAnalysisSnapshot', jobAnalysisWrite, '            - orgmetra.job_architecture.write', 'least-privilege write scope');
    requireWithin(errors, 'persistJobAnalysisSnapshot', jobAnalysisWrite, `$ref: '#/components/parameters/IdempotencyKey'`, 'Idempotency-Key');
    requireWithin(errors, 'persistJobAnalysisSnapshot', jobAnalysisWrite, `$ref: '#/components/parameters/PurposeCode'`, 'purpose parameter');
    requireWithin(errors, 'persistJobAnalysisSnapshot', jobAnalysisWrite, `$ref: '#/components/schemas/PersistJobAnalysisSnapshotCommand'`, 'request body binding');
    requireWithin(errors, 'persistJobAnalysisSnapshot', jobAnalysisWrite, "        '201':", '201 response');
    requireWithin(errors, 'persistJobAnalysisSnapshot', jobAnalysisWrite, '            Location:', '201 Location header');
    requireWithin(errors, 'persistJobAnalysisSnapshot', jobAnalysisWrite, "        '415':", 'unsupported-media response');
  }

  const jobAnalysisRead = extractYamlBlock(
    openapiText,
    '  /tenants/{tenant_record_id}/job-analysis-snapshots/{analysis_record_id}:'
  );
  if (!jobAnalysisRead) {
    errors.push('readJobAnalysisSnapshot: path block is missing');
  } else {
    requireWithin(errors, 'readJobAnalysisSnapshot', jobAnalysisRead, 'operationId: readJobAnalysisSnapshot', 'operationId');
    requireWithin(errors, 'readJobAnalysisSnapshot', jobAnalysisRead, '            - orgmetra.job_architecture.read', 'least-privilege read scope');
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

  for (const schemaName of [
    'CreateEmploymentRecordCommand',
    'CreatePositionRecordCommand',
    'CreateAssignmentRecordCommand'
  ]) {
    const commandBlock = extractYamlBlock(openapiText, `    ${schemaName}:`);
    if (!commandBlock) {
      errors.push(`${schemaName}: schema block is missing`);
      continue;
    }
    requireWithin(errors, schemaName, commandBlock, '        - evidence_references', 'required evidence_references');
    requireWithin(errors, schemaName, commandBlock, '        - confirmation_reference', 'human confirmation reference');
    requireWithin(errors, schemaName, commandBlock, '          maxItems: 100', 'evidence_references maxItems 100');
    requireWithin(errors, schemaName, commandBlock, '          uniqueItems: true', 'unique evidence_references');
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
    const unfinishedMarker = findUnfinishedMarker(text);
    if (unfinishedMarker) {
      errors.push(`${displayPath}:${unfinishedMarker.line}: unresolved work marker ${unfinishedMarker.marker}`);
    }
    if (countCodeFences(text) % 2 !== 0) errors.push(`${displayPath}: unbalanced Markdown code fence`);
    errors.push(...validateLocalLinks(filePath, text)
      .map((message) => message.replace(`${filePath}:`, `${displayPath}:`)));
  }

  errors.push(...validateDatabaseObjectNames());
  errors.push(...validateMigrationBackedDatabaseObjectNames(resolvedRoot));

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
