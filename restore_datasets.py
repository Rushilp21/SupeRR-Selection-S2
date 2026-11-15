"""Restore byte-identical CSVs from the committed gzip archives using only Python's standard library."""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parent

def sha(stream):
    digest=hashlib.sha256()
    for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only',action='store_true',help='Validate archives without extracting CSVs.')
    args=parser.parse_args()
    entries=json.loads((ROOT/'data_manifest.json').read_text(encoding='utf-8'))
    for entry in entries:
        archive=ROOT/entry['archive'];dest=ROOT/entry['path']
        assert dest.resolve().is_relative_to(ROOT) and archive.resolve().is_relative_to(ROOT)
        with gzip.open(archive,'rb') as source:
            if sha(source)!=entry['sha256']:raise ValueError(f'Archive checksum mismatch: {archive.name}')
        if args.verify_only:
            print(f"Verified {entry['path']}")
            continue
        if dest.exists():
            with dest.open('rb') as source:current=sha(source)
            if current!=entry['sha256']:raise FileExistsError(f'{dest} exists with different contents; preserve it before restoring.')
            print(f"Already restored {entry['path']}")
            continue
        with gzip.open(archive,'rb') as source,dest.open('wb') as target:shutil.copyfileobj(source,target,1024*1024)
        if dest.stat().st_size!=entry['bytes']:raise ValueError(f'Unexpected restored size: {dest.name}')
        print(f"Restored {entry['path']}")
    print(f'{len(entries)} datasets verified.')

if __name__=='__main__':main()
