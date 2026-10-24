# pyelftools

<p align="center">
    <a href="https://github.com/eliben/pyelftools/actions">
      <img alt="Logo" src="https://github.com/eliben/pyelftools/workflows/pyelftools-tests/badge.svg" />
    </a>
</p>

**pyelftools** is a pure-Python library for parsing and analyzing ELF
files and DWARF debugging information. See the [User\'s
guide](doc/user-guide.md) for more details.

## Pre-requisites

**pyelftools** requires Python 3.11 or later and has no external dependencies.
See the [CI configuration](.github/workflows/ci.yml) for the versions tested.

## Installing

The library is on PyPI as `pyelftools`; install it using your favorite
Python package manager.

For the source, clone this Git repository.

Since **pyelftools** has no external dependencies, it\'s also easy to
use it without installing, by locally adjusting `PYTHONPATH`.

## How to use it?

**pyelftools** is a regular Python library: you import and invoke it
from your own code. For a detailed usage guide and links to examples,
please consult the [user's guide](doc/user-guide.md).

## Contributing

See the [Hacking Guide](doc/hacking-guide.md).

## License

**pyelftools** is open source software. Its code is in the public
domain. See the `LICENSE` file for more details.
