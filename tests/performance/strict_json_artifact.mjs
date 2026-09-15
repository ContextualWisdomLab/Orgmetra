const MAX_JSON_NESTING_DEPTH = 64;

function invalidJson(label, cause) {
  if (cause === undefined) return new Error(`${label} must be valid JSON`);
  return new Error(`${label} must be valid JSON`, { cause });
}

function skipWhitespace(text, start) {
  let index = start;
  while (index < text.length && /[\u0009\u000a\u000d\u0020]/u.test(text[index])) index += 1;
  return index;
}

function scanString(text, start, label) {
  if (text[start] !== '"') throw invalidJson(label);
  let index = start + 1;
  while (index < text.length) {
    const character = text[index];
    if (character === '"') {
      const raw = text.slice(start, index + 1);
      try {
        return { end: index + 1, value: JSON.parse(raw) };
      } catch (error) {
        throw invalidJson(label, error);
      }
    }
    if (character === "\\") {
      index += 1;
      if (index >= text.length) throw invalidJson(label);
      if (text[index] === "u") {
        const escape = text.slice(index + 1, index + 5);
        if (!/^[0-9a-fA-F]{4}$/u.test(escape)) throw invalidJson(label);
        index += 5;
        continue;
      }
      if (!['"', "\\", "/", "b", "f", "n", "r", "t"].includes(text[index])) {
        throw invalidJson(label);
      }
      index += 1;
      continue;
    }
    if (character.charCodeAt(0) < 0x20) throw invalidJson(label);
    index += 1;
  }
  throw invalidJson(label);
}

function scanPrimitive(text, start, label) {
  let index = start;
  while (index < text.length && !/[\u0009\u000a\u000d\u0020,\]}]/u.test(text[index])) index += 1;
  if (index === start) throw invalidJson(label);
  return index;
}

function scanArray(text, start, label, depth) {
  let index = skipWhitespace(text, start + 1);
  if (text[index] === "]") return index + 1;
  while (index < text.length) {
    index = scanValue(text, index, label, depth);
    index = skipWhitespace(text, index);
    if (text[index] === "]") return index + 1;
    if (text[index] !== ",") throw invalidJson(label);
    index = skipWhitespace(text, index + 1);
  }
  throw invalidJson(label);
}

function scanObject(text, start, label, depth) {
  const names = new Set();
  let index = skipWhitespace(text, start + 1);
  if (text[index] === "}") return index + 1;
  while (index < text.length) {
    const member = scanString(text, index, label);
    if (names.has(member.value)) {
      throw new Error(`${label} must not contain duplicate JSON object member name ${JSON.stringify(member.value)}`);
    }
    names.add(member.value);
    index = skipWhitespace(text, member.end);
    if (text[index] !== ":") throw invalidJson(label);
    index = scanValue(text, skipWhitespace(text, index + 1), label, depth);
    index = skipWhitespace(text, index);
    if (text[index] === "}") return index + 1;
    if (text[index] !== ",") throw invalidJson(label);
    index = skipWhitespace(text, index + 1);
  }
  throw invalidJson(label);
}

function scanValue(text, start, label, depth) {
  const index = skipWhitespace(text, start);
  if (index >= text.length) throw invalidJson(label);
  if (text[index] === "{" || text[index] === "[") {
    if (depth >= MAX_JSON_NESTING_DEPTH) {
      throw new Error(`${label} exceeds maximum JSON nesting depth ${MAX_JSON_NESTING_DEPTH}`);
    }
    if (text[index] === "{") return scanObject(text, index, label, depth + 1);
    return scanArray(text, index, label, depth + 1);
  }
  if (text[index] === '"') return scanString(text, index, label).end;
  return scanPrimitive(text, index, label);
}

export function parseStrictJsonText(text, label) {
  if (typeof text !== "string") throw new TypeError(`${label} must be JSON text`);
  const end = skipWhitespace(text, scanValue(text, 0, label, 0));
  if (end !== text.length) throw invalidJson(label);
  try {
    return JSON.parse(text);
  } catch (error) {
    throw invalidJson(label, error);
  }
}
