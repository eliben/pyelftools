#!/usr/bin/env python
#-------------------------------------------------------------------------------
# test/run_dwarfdump_tests.py
#
# Automatic test runner for elftools & llvm-dwarfdump-11
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import argparse
from difflib import SequenceMatcher
import logging
from multiprocessing import Pool
import os
import platform
import re
import sys
import time

from utils import run_exe, is_in_rootdir, dump_output_to_temp_files

# Make it possible to run this file from the root dir of pyelftools without
# installing pyelftools; useful for CI testing, etc.
sys.path[0:0] = ['.']

# Create a global logger object
testlog = logging.getLogger('run_tests')
testlog.setLevel(logging.DEBUG)
testlog.addHandler(logging.StreamHandler(sys.stdout))

# Following the readelf example, we ship our own.
if platform.system() == "Darwin": # MacOS
    raise NotImplementedError("Not supported on MacOS")
elif platform.system() == "Windows":
    raise NotImplementedError("Not supported on Windows")
else:
    DWARFDUMP_PATH = 'test/external_tools/llvm-dwarfdump'

def discover_testfiles(rootdir):
    """ Discover test files in the given directory. Yield them one by one.
    """
    for filename in os.listdir(rootdir):
        _, ext = os.path.splitext(filename)
        if ext == '.elf':
            yield os.path.join(rootdir, filename)


def run_test_on_file(filename, verbose=False, opt=None):
    """ Runs a test on the given input filename. Return True if all test
        runs succeeded.
        If opt is specified, rather that going over the whole
        set of supported options, the test will only
        run for one option.
    """
    success = True
    testlog.info("Test file '%s'" % filename)
    if opt is None:
        options = [
            '--debug-info'
            ]
    else:
        options = [opt]

    for option in options:
        if verbose: testlog.info("..option='%s'" % option)

        # stdouts will be a 2-element list: output of llvm-dwarfdump and output
        # of scripts/dwarfdump.py
        stdouts = []
        for exe_path in [DWARFDUMP_PATH, 'scripts/dwarfdump.py']:
            args = [option, '--verbose', filename]
            if verbose: testlog.info("....executing: '%s %s'" % (
                exe_path, ' '.join(args)))
            t1 = time.time()
            rc, stdout = run_exe(exe_path, args)
            if verbose: testlog.info("....elapsed: %s" % (time.time() - t1,))
            if rc != 0:
                testlog.error("@@ aborting - '%s %s' returned '%s'" % (exe_path, option, rc))
                return False
            stdouts.append(stdout)
        if verbose: testlog.info('....comparing output...')
        t1 = time.time()
        rc, errmsg = compare_output(*stdouts)
        if verbose: testlog.info("....elapsed: %s" % (time.time() - t1,))
        if rc:
            if verbose: testlog.info('.......................SUCCESS')
        else:
            success = False
            testlog.info('.......................FAIL')
            testlog.info('....for file %s' % filename)
            testlog.info('....for option "%s"' % option)
            testlog.info('....Output #1 is llvm-dwarfdump, Output #2 is pyelftools')
            testlog.info('@@ ' + errmsg)
            dump_output_to_temp_files(testlog, filename, option, *stdouts)
    return success


def compare_output(s1, s2):
    """ Compare stdout strings s1 and s2.
        s1 is from llvm-dwarfdump, s2 from elftools dwarfdump.py
        Return pair success, errmsg. If comparison succeeds, success is True
        and errmsg is empty. Otherwise success is False and errmsg holds a
        description of the mismatch.
    """
    def prepare_lines(s):
        return [line for line in s.lower().splitlines() if line.strip() != '']

    lines1 = prepare_lines(s1)
    lines2 = prepare_lines(s2)

    if len(lines1) != len(lines2):
        return False, 'Number of lines different: %s vs %s' % (
                len(lines1), len(lines2))

    for (i, (line1, line2)) in enumerate(zip(lines1, lines2)):
        # Compare ignoring whitespace
        lines1_parts = line1.split()
        lines2_parts = line2.split()

        if ''.join(lines1_parts) != ''.join(lines2_parts):
            sm = SequenceMatcher()
            sm.set_seqs(lines1[i], lines2[i])
            changes = sm.get_opcodes()

            errmsg = 'Mismatch on line #%s:\n>>%s<<\n>>%s<<\n (%r)' % (
                i, line1, line2, changes)
            return False, errmsg
    return True, ''

def main():
    if not is_in_rootdir():
        testlog.error('Error: Please run me from the root dir of pyelftools!')
        return 1

    argparser = argparse.ArgumentParser(
        usage='usage: %(prog)s [options] [file] [file] ...',
        prog='run_dwarfdump_tests.py')
    argparser.add_argument('files', nargs='*', help='files to run tests on')
    argparser.add_argument(
        '--parallel', action='store_true',
        help='run tests in parallel; always runs all tests w/o verbose')
    argparser.add_argument('-V', '--verbose',
                           action='store_true', dest='verbose',
                           help='verbose output')
    argparser.add_argument(
        '-k', '--keep-going',
        action='store_true', dest='keep_going',
        help="Run all tests, don't stop at the first failure")
    argparser.add_argument('--opt',
        action='store', dest='opt', metavar='<dwarfdump-option>',
        help= 'Limit the test one one dwarfdump option.')
    args = argparser.parse_args()

    if args.parallel:
        if args.verbose or args.keep_going == False:
            print('WARNING: parallel mode disables verbosity and always keeps going')

    if args.verbose:
        testlog.info('Running in verbose mode')
        testlog.info('Python executable = %s' % sys.executable)
        testlog.info('dwarfdump path = %s' % DWARFDUMP_PATH)
        testlog.info('Given list of files: %s' % args.files)

    # If file names are given as command-line arguments, only these files
    # are taken as inputs. Otherwise, autodiscovery is performed.
    if len(args.files) > 0:
        filenames = args.files
    else:
        filenames = sorted(discover_testfiles('test/testfiles_for_dwarfdump'))

    if len(filenames) > 1 and args.parallel:
        pool = Pool()
        results = pool.map(run_test_on_file, filenames)
        failures = results.count(False)
    else:
        failures = 0
        for filename in filenames:
            if not run_test_on_file(filename, args.verbose, args.opt):
                failures += 1
                if not args.keep_going:
                    break

    if failures == 0:
        testlog.info('\nConclusion: SUCCESS')
        return 0
    elif args.keep_going:
        testlog.info('\nConclusion: FAIL ({}/{})'.format(
            failures, len(filenames)))
        return 1
    else:
        testlog.info('\nConclusion: FAIL')
        return 1


if __name__ == '__main__':
    sys.exit(main())
