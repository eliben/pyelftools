#!/usr/bin/env python
#-------------------------------------------------------------------------------
# test/run_readelf_tests.py
#
# Automatic test runner for elftools & readelf
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
# installing pyelftools; useful for Travis testing, etc.
sys.path[0:0] = ['.']

# Create a global logger object
testlog = logging.getLogger('run_tests')
testlog.setLevel(logging.DEBUG)
testlog.addHandler(logging.StreamHandler(sys.stdout))

# Set the path for calling readelf. We carry our own version of readelf around,
# because binutils tend to change its output even between daily builds of the
# same minor release and keeping track is a headache.
if platform.system() == "Darwin": # MacOS
    READELF_PATH = 'greadelf'
else:
    READELF_PATH = 'test/external_tools/readelf'
    if not os.path.exists(READELF_PATH):
        READELF_PATH = 'readelf'


def discover_testfiles(rootdir):
    """ Discover test files in the given directory. Yield them one by one.
    """
    for filename in os.listdir(rootdir):
        _, ext = os.path.splitext(filename)
        if ext == '.elf':
            yield os.path.join(rootdir, filename)


def run_test_on_file(filename, verbose=False):
    """ Runs a test on the given input filename. Return True if all test
        runs succeeded.
    """
    success = True
    testlog.info("Test file '%s'" % filename)
    for option in [
            '-e', '-d', '-s', '-n', '-r', '-x.text', '-p.shstrtab', '-V',
            '--debug-dump=info', '--debug-dump=decodedline',
            '--debug-dump=frames', '--debug-dump=frames-interp',
            '--debug-dump=aranges', '--debug-dump=pubtypes',
            '--debug-dump=pubnames'
            ]:
        if verbose: testlog.info("..option='%s'" % option)

        # TODO(zlobober): this is a dirty hack to make tests work for ELF core
        # dump notes. Making it work properly requires a pretty deep
        # investigation of how original readelf formats the output.
        if "core" in filename and option == "-n":
            if verbose:
                testlog.warning("....will fail because corresponding part of readelf.py is not implemented yet")
                testlog.info('.......................SKIPPED')
            continue

        # stdouts will be a 2-element list: output of readelf and output
        # of scripts/readelf.py
        stdouts = []
        for exe_path in [READELF_PATH, 'scripts/readelf.py']:
            args = [option, filename]
            if verbose: testlog.info("....executing: '%s %s'" % (
                exe_path, ' '.join(args)))
            t1 = time.time()
            rc, stdout = run_exe(exe_path, args)
            if verbose: testlog.info("....elapsed: %s" % (time.time() - t1,))
            if rc != 0:
                testlog.error("@@ aborting - '%s' returned '%s'" % (exe_path, rc))
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
            testlog.info('....for option "%s"' % option)
            testlog.info('....Output #1 is readelf, Output #2 is pyelftools')
            testlog.info('@@ ' + errmsg)
            dump_output_to_temp_files(testlog, *stdouts)
    return success


def compare_output(s1, s2):
    """ Compare stdout strings s1 and s2.
        s1 is from readelf, s2 from elftools readelf.py
        Return pair success, errmsg. If comparison succeeds, success is True
        and errmsg is empty. Otherwise success is False and errmsg holds a
        description of the mismatch.

        Note: this function contains some rather horrible hacks to ignore
        differences which are not important for the verification of pyelftools.
        This is due to some intricacies of binutils's readelf which pyelftools
        doesn't currently implement, features that binutils doesn't support,
        or silly inconsistencies in the output of readelf, which I was reluctant
        to replicate. Read the documentation for more details.
    """
    def prepare_lines(s):
        return [line for line in s.lower().splitlines() if line.strip() != '']

    lines1 = prepare_lines(s1)
    lines2 = prepare_lines(s2)

    flag_after_symtable = False

    if len(lines1) != len(lines2):
        return False, 'Number of lines different: %s vs %s' % (
                len(lines1), len(lines2))

    for i in range(len(lines1)):
        if 'symbol table' in lines1[i]:
            flag_after_symtable = True

        # Compare ignoring whitespace
        lines1_parts = lines1[i].split()
        lines2_parts = lines2[i].split()

        if ''.join(lines1_parts) != ''.join(lines2_parts):
            ok = False

            try:
                # Ignore difference in precision of hex representation in the
                # last part (i.e. 008f3b vs 8f3b)
                if (''.join(lines1_parts[:-1]) == ''.join(lines2_parts[:-1]) and
                    int(lines1_parts[-1], 16) == int(lines2_parts[-1], 16)):
                    ok = True
            except ValueError:
                pass

            sm = SequenceMatcher()
            sm.set_seqs(lines1[i], lines2[i])
            changes = sm.get_opcodes()
            if flag_after_symtable:
                # Detect readelf's adding @ with lib and version after
                # symbol name.
                if (    len(changes) == 2 and changes[1][0] == 'delete' and
                        lines1[i][changes[1][1]] == '@'):
                    ok = True
            elif 'at_const_value' in lines1[i]:
                # On 32-bit machines, readelf doesn't correctly represent
                # some boundary LEB128 numbers
                val = lines2_parts[-1]
                num2 = int(val, 16 if val.startswith('0x') else 10)
                if num2 <= -2**31 and '32' in platform.architecture()[0]:
                    ok = True
            elif 'os/abi' in lines1[i]:
                if 'unix - gnu' in lines1[i] and 'unix - linux' in lines2[i]:
                    ok = True
            elif (  'unknown at value' in lines1[i] and
                    'dw_at_apple' in lines2[i]):
                ok = True
            else:
                for s in ('t (tls)', 'l (large)'):
                    if s in lines1[i] or s in lines2[i]:
                        ok = True
                        break
            if not ok:
                errmsg = 'Mismatch on line #%s:\n>>%s<<\n>>%s<<\n (%r)' % (
                    i, lines1[i], lines2[i], changes)
                return False, errmsg
    return True, ''


def main():
    if not is_in_rootdir():
        testlog.error('Error: Please run me from the root dir of pyelftools!')
        return 1

    argparser = argparse.ArgumentParser(
        usage='usage: %(prog)s [options] [file] [file] ...',
        prog='run_readelf_tests.py')
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
    args = argparser.parse_args()

    if args.parallel:
        if args.verbose or args.keep_going == False:
            print('WARNING: parallel mode disables verbosity and always keeps going')

    if args.verbose:
        testlog.info('Running in verbose mode')
        testlog.info('Python executable = %s' % sys.executable)
        testlog.info('readelf path = %s' % READELF_PATH)
        testlog.info('Given list of files: %s' % args.files)

    # If file names are given as command-line arguments, only these files
    # are taken as inputs. Otherwise, autodiscovery is performed.
    if len(args.files) > 0:
        filenames = args.files
    else:
        filenames = sorted(discover_testfiles('test/testfiles_for_readelf'))

    if len(filenames) > 1 and args.parallel:
        pool = Pool()
        results = pool.map(
            run_test_on_file,
            filenames)
        failures = results.count(False)
    else:
        failures = 0
        for filename in filenames:
            if not run_test_on_file(filename, verbose=args.verbose):
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
