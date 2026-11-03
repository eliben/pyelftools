#!/usr/bin/env python3
"""Rebuild the executable fixtures and their independent readelf expectations.

This code is in the public domain. Run from any directory on Linux x86-64
with GCC and GNU binutils. No pyelftools import is used to create expectations.
"""
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(*args, cwd=HERE):
    result = subprocess.run(args, cwd=cwd, check=True, capture_output=True,
                            text=True, env={**os.environ, 'LC_ALL': 'C'})
    if result.stderr:
        raise RuntimeError(result.stderr)
    return result.stdout


def readelf_lists(text, locations):
    """Read the complete absolute intervals printed by GNU readelf."""
    lists = {}
    entries = []
    first_offset = None
    for line in text.splitlines():
        end = re.match(r'\s+([0-9a-f]+) <End of list>', line)
        if end:
            if first_offset is None:
                first_offset = int(end[1], 16)
            lists[first_offset] = entries
            entries = []
            first_offset = None
            continue
        row = re.match(r'\s+([0-9a-f]+) ([0-9a-f]+)(?: ([0-9a-f]+))?\s*(.*)', line)
        if row is None:
            continue
        if first_offset is None:
            first_offset = int(row[1], 16)
        if '(base address)' in row[4]:
            continue
        if row[3] is None:
            raise ValueError(line)
        entry = [int(row[2], 16), int(row[3], 16)]
        if locations:
            entry.append(row[4])
        entries.append(entry)
    if entries:
        raise ValueError('Unterminated readelf list')
    return lists


def readelf_expectations(path):
    locations = readelf_lists(run('readelf', '-wo', str(path)), True)
    ranges = readelf_lists(run('readelf', '-wR', str(path)), False)
    cus = []
    for line in run('readelf', '-wi', str(path)).splitlines():
        if 'Compilation Unit @ offset' in line:
            cu = {'locations': [], 'ranges': []}
            cus.append(cu)
        elif match := re.search(r'Version:\s+(\d+)', line):
            cu['version'] = int(match[1])
        elif match := re.search(r'Pointer Size:\s+(\d+)', line):
            cu['address_size'] = int(match[1])
        elif match := re.search(r'DW_AT_location\s+: (0x[0-9a-f]+|0) \(location list\)', line):
            offset = int(match[1], 0)
            cu['locations'].append({'offset': offset, 'entries': locations[offset]})
        elif match := re.search(r'DW_AT_ranges\s+: (0x[0-9a-f]+|0)', line):
            offset = int(match[1], 0)
            cu['ranges'].append({'offset': offset, 'entries': ranges[offset]})
    if len(cus) != 2 or any(len(cu['locations']) != 3 or len(cu['ranges']) != 1
                            for cu in cus):
        raise ValueError('Unexpected compiler-generated list references')
    return cus


def main():
    expectations = {}
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        run('as', '--64', str(HERE / 'entry.S'), '-o', str(work / 'entry.o'))
        for version in (4, 5):
            for bits in (32, 64):
                assembly = work / f'compute{bits}.s'
                args = ['gcc', f'-m{bits}', '-O2', f'-gdwarf-{version}',
                        '-gno-as-loc-support', '-gno-variable-location-views',
                        '-fno-pie', '-fno-asynchronous-unwind-tables',
                        '-fno-stack-protector', '-ffunction-sections',
                        '-ffile-prefix-map=' + str(HERE) + '=.',
                        f'-DCOMPUTE=compute{bits}', f'-DHELPER=helper{bits}',
                        '-S', 'compute.c', '-o', str(assembly)]
                run(*args)
                if bits == 32:
                    # Assemble GCC's unchanged i386 instructions and DWARF
                    # using ELF64 RELA relocations, retaining implicit addends.
                    assembly.write_text('.code32\n' + assembly.read_text())
                run('as', '--64', str(assembly), '-o', str(work / f'compute{bits}.o'))
            for order in ((32, 64), (64, 32)):
                name = f'dwarf{version}-{order[0]}-first.elf'
                path = HERE / name
                run('ld', '-o', str(path), str(work / 'entry.o'),
                    *(str(work / f'compute{bits}.o') for bits in order))
                run(str(path))
                expectations[name] = readelf_expectations(path)
                print(f'{name}: native execution exited 0; 8 readelf list references')
    (HERE / 'expected.json').write_text(json.dumps(expectations, indent=2) + '\n')


if __name__ == '__main__':
    main()
