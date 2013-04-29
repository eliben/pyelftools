#!/usr/bin/env python
#-------------------------------------------------------------------------------
# test/run_elfdump_tests.py
#
# Automatic test runner for elftools & elfdump
#
# Eli Bendersky (eliben@gmail.com)
# Yann Rouillard (yann@pleiades.fr.eu.org)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os, sys
import re
from difflib import SequenceMatcher
from optparse import OptionParser
import logging
import platform
from utils import setup_syspath; setup_syspath()
from utils import run_exe, is_in_rootdir, dump_output_to_temp_files


# Create a global logger object
#
testlog = logging.getLogger('run_tests')
testlog.setLevel(logging.DEBUG)
testlog.addHandler(logging.StreamHandler(sys.stdout))

ELFDUMP_PATH = '/usr/ccs/bin/elfdump'

def discover_testfiles(rootdir):
    """ Discover test files in the given directory. Yield them one by one.
    """
    for filename in os.listdir(rootdir):
        name, ext = os.path.splitext(filename)
        if ext == '.elf' and 'solaris' in name:
            yield os.path.join(rootdir, filename)


def run_test_on_file(filename, verbose=False):
    """ Runs a test on the given input filename. Return True if all test
        runs succeeded.
    """
    success = True
    testlog.info("Test file '%s'" % filename)
    for option in [
            '-y']:
        if verbose: testlog.info("..option='%s'" % option)
        # stdouts will be a 2-element list: output of elfdump and output
        # of scripts/elfdump.py
        stdouts = []
        for exe_path in [ELFDUMP_PATH, 'scripts/elfdump.py']:
            args = [option, filename]
            if verbose: testlog.info("....executing: '%s %s'" % (
                exe_path, ' '.join(args)))
            rc, stdout = run_exe(exe_path, args)
            if rc != 0:
                testlog.error("@@ aborting - '%s' returned '%s'" % (exe_path, rc))
                return False
            stdouts.append(stdout)
        if verbose: testlog.info('....comparing output...')
        rc, errmsg = compare_output(*stdouts)
        if rc:
            if verbose: testlog.info('.......................SUCCESS')
        else:
            success = False
            testlog.info('.......................FAIL')
            testlog.info('....for option "%s"' % option)
            testlog.info('....Output #1 is elfdump, Output #2 is pyelftools')
            testlog.info('@@ ' + errmsg)
            dump_output_to_temp_files(testlog, *stdouts)
    return success


def compare_output(s1, s2):
    """ Compare stdout strings s1 and s2.
        s1 is from elfdump, s2 from elftools elfdump.py
        Return pair success, errmsg. If comparison succeeds, success is True
        and errmsg is empty. Otherwise success is False and errmsg holds a
        description of the mismatch.

        Note: this function contains some rather horrible hacks to ignore
        differences which are not important for the verification of pyelftools.
        This is due to some intricacies of binutils's elfdump which pyelftools
        doesn't currently implement, or silly inconsistencies in the output of
        elfdump, which I was reluctant to replicate.
        Read the documentation for more details.
    """
    def prepare_lines(s):
        return [line for line in s.lower().splitlines() if line.strip() != '']
    def filter_elfdump_lines(lines):
        filter_out = False
        for line in lines:
            if not filter_out:
                yield line

    lines1 = prepare_lines(s1)
    lines2 = prepare_lines(s2)

    lines1 = list(filter_elfdump_lines(lines1))

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
            if not ok:
                errmsg = 'Mismatch on line #%s:\n>>%s<<\n>>%s<<\n' % (
                    i, lines1[i], lines2[i])
                return False, errmsg
    return True, ''


def main():
    if not is_in_rootdir():
        testlog.error('Error: Please run me from the root dir of pyelftools!')
        return 1

    optparser = OptionParser(
        usage='usage: %prog [options] [file] [file] ...',
        prog='run_elfdump_tests.py')
    optparser.add_option('-V', '--verbose',
        action='store_true', dest='verbose',
        help='Verbose output')
    options, args = optparser.parse_args()

    if options.verbose:
        testlog.info('Running in verbose mode')
        testlog.info('Python executable = %s' % sys.executable)
        testlog.info('elfdump path = %s' % READELF_PATH)
        testlog.info('Given list of files: %s' % args)

    # If file names are given as command-line arguments, only these files
    # are taken as inputs. Otherwise, autodiscovery is performed.
    #
    if len(args) > 0:
        filenames = args
    else:
        filenames = list(discover_testfiles('test/testfiles'))

    success = True
    for filename in filenames:
        if success:
            success = success and run_test_on_file(
                                    filename,
                                    verbose=options.verbose)

    if success:
        testlog.info('\nConclusion: SUCCESS')
        return 0
    else:
        testlog.info('\nConclusion: FAIL')
        return 1


if __name__ == '__main__':
    sys.exit(main())

