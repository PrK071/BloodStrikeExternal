# Static Python model link probe

`05_python_model_links.js` reads only `../python-format/selected-models-static.json`, which had already been statically parsed by the parent analysis. It does not parse or execute marshal bytecode. It writes `model-link-static.json`, retaining decoded module hashes, code-object provenance, code bytes, names/constants, and instruction windows around `ActorComponent`, `Parent`, and model-attachment operations. Module code references are decoded from CPython 3.14 instruction records using the selected parser's name-index convention (`arg >> 1` for the relevant attribute/global opcodes).

Input SHA-256: `0493a5c510cc06a998d4888777696e14195ed947ef7f7be144414017cd58aa9a`.

Selected module indexes and decoded hashes:

- 17226: `61179f1c0859d8c40097410337147629397b65987581791e8df35ad07c417de1` (MHelper)
- 25281: `e30ac8f6d7bd03898dc171bcc6f6c36a7cf97530f358c64579844690a7f5458a` (weapon_model.py)
- 68957: `6e6adda8eba6dfe1153301a517282472be152fe16ed16cdfc9c61bd79499f92c` (simple_model.py)
- 143510: `0a4a57f34d1c8e14e38c08f510f1787f46659e4b2928663cf526797eac8b0ed3` (avatar_model.py)

The source JSON came from `integration-evidence/python-format/`; no payload extraction, decompression, runtime evaluation, process access, or game execution is performed by this probe.
