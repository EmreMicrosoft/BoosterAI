# SPDX-License-Identifier: MIT
# MIT License
#
# Copyright (c) 2026 EmreMicrosoft
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Validate JSON with a standalone subset of JSON Schema on Python 3.12+.

Run this file with --schema and --instance to read two caller-selected UTF-8
JSON files. The schema should use the vocabulary documented by validate_schema.
Use this example as a read-only reference for code owned by the consuming project.

The validation kernel derives from scripts/archive_profile.py at
https://github.com/EmreMicrosoft/BoosterAI/blob/fa8f2c55b4040a5d12b1f3e89dd4c248a838dcc2/scripts/archive_profile.py
"""

import argparse
import json
import math
from pathlib import Path
import re
import sys


class UnsupportedSchemaError(ValueError):
    """Identify unsupported profile constructs even inside schema alternatives."""


def reject_non_finite_number(_literal):
    """Reject non-finite number literals in JSON input."""
    raise ValueError('non-finite JSON number')


def _json_equality_key(value):
    """Return a hashable JSON equality key for constants, options and uniqueness.

    Booleans are distinct from numbers, while equal integer/float values share a
    key. Object order is ignored and array order is retained recursively. Reject
    non-JSON values and non-finite numbers rather than letting Python equality
    silently broaden the supported JSON Schema contract.
    """
    if value is None:
        return ('null',)
    if isinstance(value, bool):
        return ('boolean', value)
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError('non-finite JSON number')
        return ('number', value)
    if isinstance(value, str):
        return ('string', value)
    if isinstance(value, list):
        return ('array', tuple(_json_equality_key(item) for item in value))
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        return ('object', frozenset((key, _json_equality_key(item))
                                    for key, item in value.items()))
    raise ValueError('unsupported JSON value')


def validate_schema(value, schema, document=None, location='$'):
    """Validate a parsed JSON value against the supported schema subset.

    Pass the current schema and, when validating a subschema, the root document
    containing its local definitions. The location labels errors in the API.
    The subset supports single types, local #/$defs references, oneOf, const,
    enum, object and array constraints, string patterns and scalar bounds.
    Integer values use Python int and exclude bool. Success returns None. A
    mismatch raises ValueError, and unsupported constructs encountered during
    validation raise UnsupportedSchemaError. No files are read by this function.
    """
    document = schema if document is None else document
    if not isinstance(schema, dict):
        raise UnsupportedSchemaError('unsupported schema at ' + location)
    supported = {'$schema', '$id', '$defs', '$ref', 'title', 'description', 'type', 'const',
                 'enum', 'required', 'properties', 'additionalProperties', 'items', 'minItems',
                 'maxItems', 'uniqueItems', 'minLength', 'maxLength', 'pattern', 'minimum', 'maximum',
                 'oneOf'}
    if set(schema) - supported:
        raise UnsupportedSchemaError('unsupported schema keyword at ' + location)
    if '$ref' in schema:
        ref = schema['$ref']
        if not isinstance(ref, str) or not ref.startswith('#/$defs/') or '/' in ref[8:]:
            raise UnsupportedSchemaError('unsupported schema reference')
        target = document.get('$defs', {}).get(ref[8:])
        if not isinstance(target, dict):
            raise UnsupportedSchemaError('unresolved schema reference')
        validate_schema(value, target, document, location)
    if 'oneOf' in schema:
        alternatives = schema['oneOf']
        if not isinstance(alternatives, list) or not alternatives:
            raise UnsupportedSchemaError('unsupported schema alternatives')
        matched = 0
        for alternative in alternatives:
            try:
                validate_schema(value, alternative, document, location)
            except UnsupportedSchemaError:
                raise
            except ValueError:
                continue
            matched += 1
        if matched != 1:
            raise ValueError('schema alternatives mismatch at ' + location)
    kind = schema.get('type')
    types = {'object': lambda v: isinstance(v, dict), 'array': lambda v: isinstance(v, list),
             'string': lambda v: isinstance(v, str), 'integer': lambda v: isinstance(v, int) and not isinstance(v, bool),
             'number': lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
                                 and (isinstance(v, int) or math.isfinite(v)),
             'boolean': lambda v: isinstance(v, bool)}
    if kind is not None and (kind not in types or not types[kind](value)):
        raise ValueError('invalid type at ' + location)
    if 'const' in schema and _json_equality_key(value) != _json_equality_key(schema['const']):
        raise ValueError('invalid constant at ' + location)
    if 'enum' in schema and _json_equality_key(value) not in {
            _json_equality_key(option) for option in schema['enum']}:
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
        if schema.get('uniqueItems') and len({_json_equality_key(v) for v in value}) != len(value):
            raise ValueError('duplicate array item at ' + location)
        if 'items' in schema:
            for index, item in enumerate(value):
                validate_schema(item, schema['items'], document, location + '[' + str(index) + ']')
    if isinstance(value, str):
        if len(value) < schema.get('minLength', 0) or len(value) > schema.get('maxLength', float('inf')):
            raise ValueError('invalid string length at ' + location)
        if 'pattern' in schema and re.search(schema['pattern'], value) is None:
            raise ValueError('invalid string pattern at ' + location)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError('non-finite number at ' + location)
        if value < schema.get('minimum', value) or value > schema.get('maximum', value):
            raise ValueError('number outside bounds at ' + location)


def _unique_object(pairs):
    """Build a JSON object from decoded pairs, rejecting any repeated key."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON field')
        result[key] = value
    return result


def _finite_float(literal):
    """Convert a JSON fractional or exponent token to a finite Python float."""
    value = float(literal)
    if not math.isfinite(value):
        raise ValueError('non-finite JSON number')
    return value


def _decode_json(text):
    """Decode JSON text into Python values with unique keys and finite numbers."""
    return json.loads(
        text,
        object_pairs_hook=_unique_object,
        parse_constant=reject_non_finite_number,
        parse_float=_finite_float,
    )


class _ArgumentParser(argparse.ArgumentParser):
    """Keep argument diagnostics independent of user-supplied values."""

    def error(self, message):
        """Exit with status 2 and a fixed message, without echoing arguments."""
        self.exit(2, 'invalid arguments\n')


def main(argv=None):
    """Read the requested files and report the result without printing input data.

    Use argv for explicit arguments or None to read the command line. A valid
    instance prints 'valid' and returns 0. A read, parse or validation failure
    prints a fixed diagnostic to stderr and returns 1.
    """
    parser = _ArgumentParser(
        description='Validate UTF-8 JSON against a supported schema subset.',
        allow_abbrev=False,
    )
    parser.add_argument('--schema', type=Path, required=True, help='JSON schema file')
    parser.add_argument('--instance', type=Path, required=True, help='JSON instance file')
    args = parser.parse_args(argv)
    try:
        schema = _decode_json(args.schema.read_text(encoding='utf-8'))
        instance = _decode_json(args.instance.read_text(encoding='utf-8'))
        validate_schema(instance, schema)
    except (OSError, ValueError, TypeError, AttributeError, OverflowError, RecursionError, re.error):
        print('validation failed', file=sys.stderr)
        return 1
    print('valid')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
