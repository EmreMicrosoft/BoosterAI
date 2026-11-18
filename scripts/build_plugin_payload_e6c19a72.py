"""Assemble a reproducible BoosterAI runtime payload for release preparation.

Read UTF-8 JSON with a reviewed "manifest" and a "files" object mapping each
manifest path to its exact UTF-8 text. Write a ZIP containing runtime/ to
stdout. The caller supplies the independently reviewed canonical recipe hash.
Installer metadata, installation, and package integrity acceptance have
separate release steps.
"""

import argparse
import hashlib
import io
import json
import re
import sys
import zipfile


FORMAT = "boosterai-plugin-runtime-v1"
INPUT_LIMIT = 16 * 1024 * 1024
HASH = re.compile(r"[0-9a-f]{64}")
PATH_COMPONENT = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*")
WINDOWS_NAMES = {"AUX", "CON", "NUL", "PRN"} | {
    f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(10)
}
ERROR = "invalid runtime build input\n"


class BuildArgumentParser(argparse.ArgumentParser):
    """Use the fixed failure diagnostic for malformed CLI arguments."""

    def error(self, message):
        """Exit without exposing the supplied arguments in the diagnostic."""
        self.exit(2, ERROR)


def unique_object(pairs):
    """Read a JSON object while rejecting ambiguous repeated member names."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate member")
        result[key] = value
    return result


def build_payload(raw, recipe_hash):
    """Return immutable ZIP bytes from bounded UTF-8 input and reviewed hash.

    Require the exact recipe membership and matching input bytes. Complete
    construction in memory before returning any output to the caller.
    """
    if len(raw) > INPUT_LIMIT or not HASH.fullmatch(recipe_hash):
        raise ValueError("invalid input boundary")
    request = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
    if not isinstance(request, dict) or set(request) != {"manifest", "files"}:
        raise ValueError("invalid input fields")
    manifest, sources = request["manifest"], request["files"]
    if not isinstance(manifest, dict) or set(manifest) != {
        "format", "source_commit", "files"
    }:
        raise ValueError("invalid recipe fields")
    commit, expected = manifest["source_commit"], manifest["files"]
    if (manifest["format"] != FORMAT or not isinstance(commit, str)
            or not re.fullmatch(r"[0-9a-f]{40}", commit)
            or not isinstance(expected, dict) or not expected
            or not isinstance(sources, dict) or set(sources) != set(expected)):
        raise ValueError("invalid recipe membership")

    recipe = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if hashlib.sha256(recipe).hexdigest() != recipe_hash:
        raise ValueError("recipe pin mismatch")

    files = {"manifest.json": recipe}
    seen = {"manifest.json"}
    directories = {}
    for path, digest in expected.items():
        parts = path.split("/")
        if (len(path) > 65535 - len("runtime/")
                or any(len(part) > 255 or not PATH_COMPONENT.fullmatch(part)
                       or part.endswith(".")
                       or part.split(".")[0].upper() in WINDOWS_NAMES for part in parts)):
            raise ValueError("invalid payload path")
        identity = path.lower()
        if identity in seen:
            raise ValueError("duplicate payload path")
        seen.add(identity)
        for index in range(1, len(parts)):
            directory = "/".join(parts[:index])
            if directories.setdefault(directory.lower(), directory) != directory:
                raise ValueError("ambiguous directory spelling")
        if (not isinstance(digest, str) or not HASH.fullmatch(digest)
                or not isinstance(sources[path], str)):
            raise ValueError("invalid payload material")
        content = sources[path].encode("utf-8")
        if hashlib.sha256(content).hexdigest() != digest:
            raise ValueError("payload source differs")
        files[path] = content
    if seen.intersection(directories):
        raise ValueError("file and directory conflict")

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for path, content in sorted(files.items()):
            entry = zipfile.ZipInfo("runtime/" + path)
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, content)
    return output.getvalue()


def main(argv=None):
    """Read the release material from stdin and stream a payload or a fixed error."""
    parser = BuildArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--recipe-sha256", required=True, action="append")
    args = parser.parse_args(argv)
    if len(args.recipe_sha256) != 1:
        parser.error("exactly one reviewed pin is required")
    try:
        payload = build_payload(sys.stdin.buffer.read(INPUT_LIMIT + 1), args.recipe_sha256[0])
    except (ValueError, RecursionError):
        sys.stderr.write(ERROR)
        return 2
    sys.stdout.buffer.write(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
