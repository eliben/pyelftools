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
# installing pyelftools; useful for CI testing, etc.
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
elif platform.system() == "Windows":
    # Point the environment variable READELF at Cygwin's readelf.exe, or some other Windows build
    READELF_PATH = os.environ.get('READELF', "readelf.exe")
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


def run_test_on_file(filename, verbose=False, opt=None):
    """ Runs a test on the given input filename. Return True if all test
        runs succeeded.
        If opt is specified, rather that going over the whole
        set of supported readelf options, the test will only
        run for one option.
    """
    success = True
    testlog.info("Test file '%s'" % filename)
    if opt is None:
        options = [
            '-e', '-d', '-s', '-n', '-r', '-x.text', '-p.shstrtab', '-V',
            '--debug-dump=info', '--debug-dump=decodedline',
            '--debug-dump=frames', '--debug-dump=frames-interp',
            '--debug-dump=aranges', '--debug-dump=pubtypes',
            '--debug-dump=pubnames', '--debug-dump=loc',
            '--debug-dump=Ranges'
            ]
    else:
        options = [opt]

    for option in options:
        if verbose: testlog.info("..option='%s'" % option)

        # TODO(zlobober): this is a dirty hack to make tests work for ELF core
        # dump notes. Making it work properly requires a pretty deep
        # investigation of how original readelf formats the output.
        if "core" in filename and option == "-n":
            if verbose:
                testlog.warning("....will fail because corresponding part of readelf.py is not implemented yet")
                testlog.info('.......................SKIPPED')
            continue

        # sevaa says: there is another shorted out test; in dwarf_lineprogramv5.elf, the two bytes at 0x2072 were
        # patched from 0x07 0x10 to 00 00.
        # Those represented the second instruction in the first FDE in .eh_frame. This changed the instruction
        # from "DW_CFA_undefined 16" to two NOPs.
        # GNU readelf 2.38 had a bug here, had to work around:
        # https://sourceware.org/bugzilla/show_bug.cgi?id=29250
        # It's been fixed in the binutils' master since, but the latest master will break a lot.
        # Same patch in  dwarf_test_versions_mix.elf at 0x2061: 07 10 -> 00 00

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
            testlog.info('....Output #1 is readelf, Output #2 is pyelftools')
            testlog.info('@@ ' + errmsg)
            dump_output_to_temp_files(testlog, filename, option, *stdouts)
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

    flag_in_debug_line_section = False

    if len(lines1) != len(lines2):
        return False, 'Number of lines different: %s vs %s' % (
                len(lines1), len(lines2))

    # Position of the View column in the output file, if parsing readelf..decodedline
    # output, and the GNU readelf output contains the View column. Otherwise stays -1.
    view_col_position = -1
    for i in range(len(lines1)):
        if lines1[i].endswith('debug_line section:'):
            # .debug_line or .zdebug_line
            flag_in_debug_line_section = True

        # readelf spelling error for GNU property notes
        lines1[i] = lines1[i].replace('procesor-specific type', 'processor-specific type')

        # The view column position may change from CU to CU:
        if view_col_position >= 0 and lines1[i].startswith('cu:'):
            view_col_position = -1

        # Check if readelf..decodedline output line contains the view column
        if flag_in_debug_line_section and lines1[i].startswith('file name') and view_col_position < 0:
            view_col_position = lines1[i].find("view")
            stmt_col_position = lines1[i].find("stmt")

        # Excise the View column from the table, if any.
        # View_col_position is only set to a nonzero number if one of the previous
        # lines was a table header line with a "view" in it.
        # We assume careful formatting on GNU readelf's part - View column values
        # are not out of line with the View header.
        if view_col_position >= 0 and not lines1[i].endswith(':'):
            lines1[i] = lines1[i][:view_col_position] + lines1[i][stmt_col_position:]

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
            if '[...]' in lines1[i]:
                # Special case truncations with ellipsis like these:
                #     .note.gnu.bu[...]        redelf
                #     .note.gnu.build-i        pyelftools
                # Or more complex for symbols with versions, like these:
                #     _unw[...]@gcc_3.0        readelf
                #     _unwind_resume@gcc_3.0   pyelftools
                for p1, p2 in zip(lines1_parts, lines2_parts):
                    dots_start = p1.find('[...]')
                    if dots_start != -1:
                        break
                ok = p1.endswith('[...]') and p1[:dots_start] == p2[:dots_start]
                if not ok:
                    dots_end = dots_start + 5
                    if len(p1) > dots_end and p1[dots_end] == '@':
                        ok = (    p1[:dots_start] == p2[:dots_start]
                              and p1[p1.rfind('@'):] == p2[p2.rfind('@'):])
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
            elif len(lines1_parts) == 3 and lines1_parts[2] == 'nt_gnu_property_type_0':
                # readelf does not seem to print a readable description for this
                ok = lines1_parts == lines2_parts[:3]
            else:
                for s in ('t (tls)', 'l (large)', 'd (mbind)'):
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
    argparser.add_argument('--opt',
        action='store', dest='opt', metavar='<readelf-option>',
        help= 'Limit the test one one readelf option.')
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
