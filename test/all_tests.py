#!/usr/bin/env python
#-------------------------------------------------------------------------------
# test/all_tests.py
#
# Run all pyelftools tests.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import subprocess
import sys
from utils import is_in_rootdir

def run_test_script(path, *args):
    cmd = [sys.executable, path, *args]
    print("Running '%s'" % ' '.join(cmd))
    subprocess.check_call(cmd)

def main():
    if not is_in_rootdir():
        sys.exit('Error: Please run me from the root dir of pyelftools!')
    run_test_script('test/run_all_unittests.py')
    run_test_script('test/run_examples_test.py')
    run_test_script('test/run_readelf_tests.py', '--parallel')
    run_test_script('test/run_dwarfdump_tests.py', '--parallel')

if __name__ == '__main__':
    sys.exit(main())
