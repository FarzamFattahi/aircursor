"""Update Farzam's original Python 3.12 portable app without replacing its UI.

Run with Python 3.12: python packaging/update_portable.py original.exe improved.exe
The input is never modified. The output must not already exist.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import marshal
import struct
import sys
import zlib
from pathlib import Path

ORIGINAL_SHA256 = "094e72773ca49b82ff3645516fcb4f000bc7799e9de36529040d929bc64b10a4"
COOKIE = struct.Struct("!8sIIII64s")
ENTRY = struct.Struct("!IIIIBc")
MAGIC = b"MEI\014\013\012\013\016"
ROOT = Path(__file__).resolve().parents[1]


def updated_pyz(data: bytes) -> bytes:
    if data[:8] != b"PYZ\0" + importlib.util.MAGIC_NUMBER:
        raise ValueError("PYZ must use this interpreter's Python 3.12 bytecode")
    toc_offset = struct.unpack("!i", data[8:12])[0]
    toc = dict(marshal.loads(data[toc_offset:]))
    replacements = {}
    replacements["aircursor.packaged_qa"] = (0, ROOT / "packaging/qa_probe.py")
    for name in ("__init__", "config", "models", "gestures", "pointer", "input", "interaction"):
        path = ROOT / "src/aircursor" / f"{name}.py"
        module = "aircursor" if name == "__init__" else f"aircursor.{name}"
        replacements[module] = (1 if name == "__init__" else 0, path)
    for name, source in {
        "app.gestures.gesture_manager": "gesture_manager.py",
        "app.pointer.tap_stabilizer": "tap_stabilizer.py",
        "app.platform.windows_input": "windows_input.py",
    }.items():
        replacements[name] = (0, ROOT / "packaging/compat" / source)
    output = bytearray(data[:toc_offset])
    for name, source in (("app.ui.main_window", "main_window.py"),
                         ("app.ui.settings_dialog", "settings_dialog.py")):
        kind, position, size = toc[name]
        original_code = zlib.decompress(data[position:position + size])
        wrapper = f"import marshal\nexec(marshal.loads({original_code!r}), globals())\n"
        wrapper += (ROOT / "packaging/compat" / source).read_text(encoding="utf-8")
        blob = zlib.compress(marshal.dumps(compile(wrapper, name + ".py", "exec")), 6)
        toc[name] = (kind, len(output), len(blob))
        output.extend(blob)
    for name, (kind, path) in replacements.items():
        code = compile(path.read_text(encoding="utf-8"), name.replace(".", "/") + ".py", "exec")
        blob = zlib.compress(marshal.dumps(code), 6)
        toc[name] = (kind, len(output), len(blob))
        output.extend(blob)
    offset = len(output)
    output.extend(marshal.dumps(list(toc.items())))
    output[8:12] = struct.pack("!i", offset)
    return bytes(output)


def update(source: Path, destination: Path) -> None:
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("Use Python 3.12 to match the packaged runtime")
    if destination.exists() or destination.resolve() == source.resolve():
        raise ValueError("output must be a new file, separate from the input")
    original = source.read_bytes()
    if hashlib.sha256(original).hexdigest() != ORIGINAL_SHA256:
        raise ValueError("Input is not the supported original AirCursor build; no files changed")
    cookie_at = original.rfind(MAGIC)
    magic, length, offset, toc_length, version, library = COOKIE.unpack_from(original, cookie_at)
    if version != 312 or cookie_at + COOKIE.size != len(original):
        raise ValueError("unexpected archive version or trailing signature")
    start = cookie_at + COOKIE.size - length
    cursor, stop = start + offset, start + offset + toc_length
    entries = []
    archive = bytearray()
    while cursor < stop:
        size, position, compressed, raw_size, flag, kind = ENTRY.unpack_from(original, cursor)
        name_bytes = original[cursor + ENTRY.size:cursor + size]
        name = name_bytes.rstrip(b"\0").decode("utf-8")
        blob = original[start + position:start + position + compressed]
        if name == "PYZ-00.pyz":
            raw = zlib.decompress(blob) if flag else blob
            raw = updated_pyz(raw)
            raw_size = len(raw)
            blob = zlib.compress(raw, 9) if flag else raw
        elif name == "main":
            raw = zlib.decompress(blob) if flag else blob
            wrapper = (
                "import sys, marshal, traceback\n"
                "from pathlib import Path\n"
                "if '--aircursor-native-test' in sys.argv:\n"
                "    from aircursor.packaged_qa import native_probe\n"
                "    path = sys.argv[sys.argv.index('--aircursor-native-test') + 1]\n"
                "    try:\n"
                "        native_probe(path)\n"
                "    except Exception:\n"
                "        Path(path + '.error.txt').write_text(traceback.format_exc(), encoding='utf-8')\n"
                "        raise SystemExit(1)\n"
                "    raise SystemExit(0)\n"
                "if '--aircursor-self-test' in sys.argv:\n"
                "    from aircursor.packaged_qa import run\n"
                "    run(sys.argv[sys.argv.index('--aircursor-self-test') + 1])\n"
                "    raise SystemExit(0)\n"
                f"exec(marshal.loads({raw!r}), globals())\n"
            )
            raw = marshal.dumps(compile(wrapper, "main.py", "exec"))
            raw_size = len(raw)
            blob = zlib.compress(raw, 9) if flag else raw
        entries.append(ENTRY.pack(size, len(archive), len(blob), raw_size, flag, kind) + name_bytes)
        archive.extend(blob)
        cursor += size
    new_offset = len(archive)
    table = b"".join(entries)
    archive.extend(table)
    archive.extend(COOKIE.pack(magic, len(archive) + COOKIE.size, new_offset,
                               len(table), version, library))
    with destination.open("xb") as output:
        output.write(original[:start])
        output.write(archive)
    print(f"Created {destination}; original unchanged. SHA256: {hashlib.sha256(destination.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    update(args.source, args.destination)
