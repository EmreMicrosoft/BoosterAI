"""Validate the deliberately limited JSON Schema vocabulary used by the archive."""

import json
import re
import hashlib
from pathlib import Path


def validate_schema(value, schema, document=None, location='$'):
    """Check a value against the bundled profile subset; reject unsupported schema keywords.

    The local profile uses only types, local references, object and array constraints,
    string patterns and scalar bounds. This is not a general JSON Schema implementation.
    Validation is offline, returns no value on success and raises ValueError on failure.
    """
    document = schema if document is None else document
    if not isinstance(schema, dict):
        raise ValueError('unsupported schema at ' + location)
    supported = {'$schema', '$id', '$defs', '$ref', 'title', 'description', 'type', 'const',
                 'enum', 'required', 'properties', 'additionalProperties', 'items', 'minItems',
                 'maxItems', 'uniqueItems', 'minLength', 'maxLength', 'pattern', 'minimum', 'maximum'}
    if set(schema) - supported:
        raise ValueError('unsupported schema keyword at ' + location)
    if '$ref' in schema:
        ref = schema['$ref']
        if not isinstance(ref, str) or not ref.startswith('#/$defs/') or '/' in ref[8:]:
            raise ValueError('unsupported schema reference')
        target = document.get('$defs', {}).get(ref[8:])
        if not isinstance(target, dict):
            raise ValueError('unresolved schema reference')
        validate_schema(value, target, document, location)
    kind = schema.get('type')
    types = {'object': lambda v: isinstance(v, dict), 'array': lambda v: isinstance(v, list),
             'string': lambda v: isinstance(v, str), 'integer': lambda v: isinstance(v, int) and not isinstance(v, bool),
             'boolean': lambda v: isinstance(v, bool)}
    if kind is not None and (kind not in types or not types[kind](value)):
        raise ValueError('invalid type at ' + location)
    if 'const' in schema and value != schema['const']:
        raise ValueError('invalid constant at ' + location)
    if 'enum' in schema and value not in schema['enum']:
        raise ValueError('invalid option at ' + location)
    if isinstance(value, dict):
        for key in schema.get('required', []):
            if key not in value:
                raise ValueError('missing field at ' + location + '.' + key)
        properties = schema.get('properties', {})
        for key, item in value.items():
            if key in properties:
                validate_schema(item, properties[key], document, location + '.' + key)
            elif schema.get('additionalProperties') is False:
                raise ValueError('unexpected field at ' + location + '.' + key)
    if isinstance(value, list):
        if len(value) < schema.get('minItems', 0) or len(value) > schema.get('maxItems', float('inf')):
            raise ValueError('invalid array length at ' + location)
        if schema.get('uniqueItems') and len({json.dumps(v, sort_keys=True) for v in value}) != len(value):
            raise ValueError('duplicate array item at ' + location)
        if 'items' in schema:
            for index, item in enumerate(value):
                validate_schema(item, schema['items'], document, location + '[' + str(index) + ']')
    if isinstance(value, str):
        if len(value) < schema.get('minLength', 0) or len(value) > schema.get('maxLength', float('inf')):
            raise ValueError('invalid string length at ' + location)
        if 'pattern' in schema and re.search(schema['pattern'], value) is None:
            raise ValueError('invalid string pattern at ' + location)
    if isinstance(value, int) and not isinstance(value, bool):
        if value < schema.get('minimum', value) or value > schema.get('maximum', value):
            raise ValueError('integer outside bounds at ' + location)


SCHEMA_PATH = Path(__file__).resolve().parents[1] / 'solutions/archive.schema.json'
LANGUAGES = {'.py': 'Python', '.cs': 'C#', '.js': 'JavaScript', '.ts': 'TypeScript',
             '.ps1': 'PowerShell', '.sh': 'Shell', '.go': 'Go', '.rs': 'Rust',
             '.java': 'Java', '.cpp': 'C++', '.c': 'C'}


def code_filename(name, revision, digest, suffix):
    """Generate a concise, stable filename whose suffix identifies this exact revision.

    The identifier combines the public record name, revision number and source hash.
    It is deterministic, so rebuilding the index never renames an unchanged record.
    """
    if suffix not in LANGUAGES:
        raise ValueError('unsupported code extension')
    parts = [part for part in name.split('-') if part]
    short = (parts[0] + '-' + parts[-1] if len(parts) > 2 else name)[:16].rstrip('-')
    unique = hashlib.sha256((name + ':' + str(revision) + ':' + digest).encode('utf-8')).hexdigest()[:8]
    return short + '-' + unique + suffix


def validate_entry(entry, schema=None):
    """Validate one archive record and its path without opening or executing source code.

    In addition to the JSON Schema profile, check the category hierarchy, language,
    deterministic code filename, sorted tags, CodeMeta keywords and any declared
    sanitized-summary digest. A matching digest does not authenticate the observation.
    """
    schema = schema or json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))
    validate_schema(entry, schema['$defs']['entry'], schema)
    for value in [entry['name'], *entry['categories'], *entry['categoryAliases'], *entry['tags']]:
        if re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', value) is None:
            raise ValueError('invalid archive slug')
    if entry['tags'] != sorted(entry['tags']) or entry['keywords'] != entry['tags']:
        raise ValueError('tags and keywords must be identical and sorted')
    if entry['categoryAliases'] != sorted(entry['categoryAliases']):
        raise ValueError('category aliases must be sorted')
    if entry.get('evidence_basis') == 'sanitized-summary-sha256':
        observed = hashlib.sha256(entry['test_summary'].encode('utf-8')).hexdigest()
        if entry['evidence_sha256'] != observed:
            raise ValueError('sanitized evidence summary hash mismatch')
    code = Path(entry['code'])
    suffix = code.suffix
    if LANGUAGES.get(suffix) != entry['programmingLanguage']:
        raise ValueError('programming language does not match code extension')
    filename = code_filename(entry['name'], entry['revision'], entry['code_sha256'], suffix)
    expected = ['solutions', *entry['categories'], entry['name'], 'revisions',
                str(entry['revision']).zfill(4), filename]
    if list(code.parts) != expected:
        raise ValueError('code path does not match category and revision')
    return True


def build_index(entries):
    """Create the canonical archive index from current records, in stable order.

    Categories remain ordered paths. Tags and category paths are deduplicated and sorted;
    the result is checked before it can be written or sent to an archive consumer.
    """
    entries = sorted(entries, key=lambda item: item['name'])
    categories = [list(parts) for parts in sorted({tuple(item['categories']) for item in entries})]
    tags = sorted({tag for item in entries for tag in item['tags']})
    result = {'format': 'boosterai-index-v2', 'entries': entries, 'categories': categories, 'tags': tags}
    validate_index(result)
    return result


def validate_index(index):
    """Apply the bundled JSON Schema subset and archive-specific consistency checks.

    This does not download context files, authenticate evidence or execute examples.
    It raises ValueError when metadata, names, paths or deterministic ordering disagree.
    """
    schema = json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))
    validate_schema(index, schema)
    names, paths = set(), set()
    for entry in index['entries']:
        validate_entry(entry, schema)
        if entry['name'] in names or entry['code'] in paths:
            raise ValueError('duplicate archive name or path')
        names.add(entry['name']); paths.add(entry['code'])
    if [e['name'] for e in index['entries']] != sorted(names):
        raise ValueError('archive entries are not sorted')
    if index['categories'] != [list(p) for p in sorted({tuple(e['categories']) for e in index['entries']})]:
        raise ValueError('archive category paths are not canonical')
    if index['tags'] != sorted({tag for e in index['entries'] for tag in e['tags']}):
        raise ValueError('archive tags are not canonical')
    return index
