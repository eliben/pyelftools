# Hacking guide

## Contributing

Contributing to **pyelftools** is really easy, since it\'s a completely
open-source project, with the code being in the public domain and easily
available on Github. The git repository can be cloned at any time with
the latest code which hasn\'t made it into a release version yet. My
methodology is to keep trunk `main` branch) stable, so it\'s quite
usable (sometimes even more so than the released version, since it may
contain bug fixes).

Please open Github pull requests for contributions. Make sure to add
tests, unless the code you\'re affecting is already covered by existing
tests.

Opening issues in the tracker is also appreciated for reporting problems
you ran into but can\'t or don\'t want to solve on your own.

Finally, creating clones of other binutils tools (such as `nm`) with
**pyelftools** will be really nice. In general, any additional work done
using **pyelftools** helps refine and test the library.

## Tests

Tests must be run from the root development directory of **pyelftools**.

### readelf comparison tests

Since **pyelftools** essentially clones the functionality of some
existing tools in GNU binutils, it can be tested comprehensively by a
simple method of output comparison.

This is implemented in `test/run_readelf_tests.py`, which runs the
`scripts/readelf.py` script on a set of files with a variety of options,
and compares its output with the system\'s installed `readelf`.

Failures in this test suite frequently result from minor differences in
the output of `readelf`, which tends to change between versions. It may
also depend on the system the tool is run on (I run it on 64-bit Ubuntu,
x86-64). Take a look at the `READELF_PATH` variable in
`test/run_readelf_tests.py` to get an idea of the binutils version used.

### Unit tests

While initially the `readelf` comparison tests were top priority because
of the great coverage they provided relatively \"for free\", with time
unit testing also became important in **pyelftools**, due to intricacies
of some of the modules, especially in the DWARF parsing parts.

In addition, as the library gains maturity with time, bug fixes should
be verified by creating reproducer unit tests, to avoid the bugs coming
back in the future.

All unit tests can be executed by running `test/run_all_unittests.py`.

### Testing the examples

**pyelftools** comes with a few usage examples. I consider them a very
important part of the documentation, and therefore they should always be
kept functional.

To accomplish this, a special test script named
`test/run_examples_test.py` runs all examples on a sample ELF file, and
compares the output to a saved \"reference\" output. This makes sure
that the examples work correctly at all times.

### Running all tests on supported Python versions

Run `make test` to run all tests.

## Performance

While performance is important for reading large ELF files, it is not
the main design goal of **pyelftools**. That said, performance is not
neglected, and I do profile and optimize **pyelftools** occasionally
when something is running slower than expected. I don\'t want to start
growing C-extensions on top of it however. Pure Python *is* an important
design goal.

If you think that **pyelftools** runs too slowly for some particular
file, please open an issue and I\'ll see what can be done.

## Coding conventions

**pyelftools** is written in Python, following the [PEP
8](http://www.python.org/dev/peps/pep-0008/) style guide.

## Type checking

**pyelftools** is using and providing Type Hints, following [PEP
484](https://peps.python.org/pep-0484/). Please make sure new functions
and methods are properly type hinted. There are some known limitations
as **pyelftools** is dynamic for some types, which does not work well
for static typing.

pyelftools aims to use \[ty\](<https://docs.astral.sh/ty/>) as its type
checker.
