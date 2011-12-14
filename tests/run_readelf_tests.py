#!/usr/bin/env python
#-------------------------------------------------------------------------------
# tests/run_readelf_tests.py
#
# Automatic test runner for elftools & readelf
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os, sys
import re
from difflib import SequenceMatcher
import logging
import subprocess
import tempfile


# Create a global logger object
#
testlog = logging.getLogger('run_tests')
testlog.setLevel(logging.DEBUG)
testlog.addHandler(logging.StreamHandler(sys.stdout))


def discover_testfiles(rootdir):
    """ Discover test files in the given directory. Yield them one by one.
    """
    for filename in os.listdir(rootdir):
        _, ext = os.path.splitext(filename)
        if ext == '.elf':
            yield os.path.join(rootdir, filename)


def run_exe(exe_path, args):
    """ Runs the given executable as a subprocess, given the
        list of arguments. Captures its return code (rc) and stdout and
        returns a pair: rc, stdout_str
    """
    popen_cmd = [exe_path] + args
    if os.path.splitext(exe_path)[1] == '.py':
        popen_cmd.insert(0, 'python')
    proc = subprocess.Popen(popen_cmd, stdout=subprocess.PIPE)
    proc_stdout = proc.communicate()[0]
    return proc.returncode, proc_stdout
    

def run_test_on_file(filename):
    """ Runs a test on the given input filename. Return True if all test
        runs succeeded.
    """
    success = True
    testlog.info("Running test on file '%s'" % filename)
    for option in [
            '-e', '-s', '-r', '-x.text', '-p.shstrtab',
            '--debug-dump=info', '--debug-dump=decodedline',
            '--debug-dump=frames']:
        testlog.info("..option='%s'" % option)
        # stdouts will be a 2-element list: output of readelf and output 
        # of scripts/readelf.py
        stdouts = []
        for exe_path in ['readelf', 'scripts/readelf.py']:
            args = [option, filename]
            testlog.info("....executing: '%s %s'" % (
                exe_path, ' '.join(args)))
            rc, stdout = run_exe(exe_path, args)
            if rc != 0:
                testlog.error("@@ aborting - '%s' returned '%s'" % (exe_path, rc))
                return False
            stdouts.append(stdout)
        testlog.info('....comparing output...')
        rc, errmsg = compare_output(*stdouts)
        if rc:
            testlog.info('.......................SUCCESS')
        else:
            success = False
            testlog.info('.......................FAIL')
            testlog.info('@@ ' + errmsg)
            dump_output_to_temp_files(*stdouts)
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
        doesn't currently implement, or silly inconsistencies in the output of
        readelf, which I was reluctant to replicate.
        Read the documentation for more details.
    """
    def prepare_lines(s):
        return [line for line in s.lower().splitlines() if line.strip() != '']
    def filter_readelf_lines(lines):
        filter_out = False
        for line in lines:
            if 'of the .eh_frame section' in line:
                filter_out = True
            elif 'of the .debug_frame section' in line:
                filter_out = False
            if not filter_out:
                yield line
        
    lines1 = prepare_lines(s1)
    lines2 = prepare_lines(s2)

    lines1 = list(filter_readelf_lines(lines1))

    flag_after_symtable = False

    if len(lines1) != len(lines2):
        return False, 'Number of lines different: %s vs %s' % (
                len(lines1), len(lines2))

    for i in range(len(lines1)):
        if 'symbol table' in lines1[i]:
            flag_after_symtable = True

        # Compare ignoring whitespace
        if lines1[i].split() != lines2[i].split():
            ok = False
            sm = SequenceMatcher()
            sm.set_seqs(lines1[i], lines2[i])
            changes = sm.get_opcodes()
            if flag_after_symtable:
                # Detect readelf's adding @ with lib and version after 
                # symbol name.
                if (    len(changes) == 2 and changes[1][0] == 'delete' and
                        lines1[i][changes[1][1]] == '@'):
                    ok = True
            else: 
                for s in ('t (tls)', 'l (large)'):
                    if s in lines1[i] or s in lines2[i]:
                        ok = True
                        break
            if not ok:
                errmsg = 'Mismatch on line #%s:\n>>%s<<\n>>%s<<\n' % (
                    i, lines1[i], lines2[i])
                return False, errmsg
    return True, ''
    

def dump_output_to_temp_files(*args):
    """ Dumps the output strings given in 'args' to temp files: one for each
        arg.
    """
    for i, s in enumerate(args):
        fd, path = tempfile.mkstemp(
                prefix='out' + str(i + 1) + '_',
                suffix='.stdout')
        file = os.fdopen(fd, 'w')
        file.write(s)
        file.close()
        testlog.info('@@ Output #%s dumped to file: %s' % (i + 1, path))
    

def die(msg):
    testlog.error('Error: %s' % msg)
    sys.exit(1)


def is_in_rootdir():
    """ Check whether the current dir is the root dir of pyelftools
    """
    dirstuff = os.listdir('.')
    return 'tests' in dirstuff and 'elftools' in dirstuff
    

def main():
    if not is_in_rootdir():
        die('Please run me from the root dir of pyelftools!')

    # If file names are given as command-line arguments, only these files
    # are taken as inputs. Otherwise, autodiscovery is performed.
    #
    if len(sys.argv) > 1:
        filenames = sys.argv[1:]
    else:
        filenames = list(discover_testfiles('tests/testfiles'))

    success = True
    for filename in filenames:
        success = success and run_test_on_file(filename)

    if success:
        testlog.info('\nConclusion: SUCCESS')
    else:
        testlog.info('\nConclusion: FAIL')


if __name__ == '__main__':
    #import os
    #os.chdir('..')
    main()
    #testlog.info(list(discover_testfiles('tests/testfiles'))) 
    #print run_exe('scripts/readelf.py', ['-h', 'tests/testfiles/z32.o.elf'])




