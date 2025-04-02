User's guide
============

This is a brief user's guide for **pyelftools**.

Getting started
---------------

The easiest way to get started with **pyelftools** is by examining the examples
it comes with (in the ``examples/`` directory of the source distribution). Examples are heavily commented, and each begins with a short comment describing its purpose.

If you have a basic grasp of Python and are somewhat familiar with the problem
domain **pyelftools** aims to address (ELF and DWARF formats), you should be
able to get going just from looking at the examples - reading this guide is not
necessary.

Directory structure
-------------------

When you unzip (or untar) the source distribution package of **pyelftools**,
these are the directories you'll see:

* ``./``: root of the distribution, with a ``README``, ``LICENSE`` and other
  informational files.
* ``./elftools``: the source of the library/package itself. This is the directory that
  will get placed into your ``site-packages`` by the setup process.

  * ``./elftools/elf``: classes for parsing and decoding ELF.
  * ``./elftools/dwarf``: classes for parsing and decoding DWARF.
  * ``./elftools/common``: common utilities for the ELF and DWARF parts.
  * ``./elftools/construct``: the "construct" library used by **pyelftools** for low-level binary stream parsing.

* ``./scripts``: some useful scripts and tools built on top of the ``elftools`` package. For example - a clone of ``readelf``.
* ``./test``: tests for **pyelftools**, of interest mainly to those who wish to modify or extend the library, rather than simply use it. See the `Hacking guide <hacking-guide.rst>`_ for more details.

From this point on, ``elftools`` is going to refer only to the Python library, and **pyelftools** to the whole source distribution which includes, in addition to the library, also examples, scripts and tests.

Running the examples
""""""""""""""""""""

Running the examples is very easy. After installing **pyelftools** you can run them from anywhere by executing:

.. sourcecode:: text

  > python <path_to_pyelftools>/examples/<example_name> --test <elf_filename>

Even without installing **pyelftools**, you can run the examples from the root of the unzipped source distribution. So, for example, if you've unzipped it into ``$MYDIR``:

.. sourcecode:: text

  $MYDIR> python examples/examine_dwarf_info.py --test examples/sample_exe64.elf

Will run the ``examine_dwarf_info.py`` file on the sample ELF executable shipped with **pyelftools**.

Scripts and tools
-----------------

A variety of useful scripts and tools can be built on-top of the ``elftools`` library. For the time being, the only such script packaged with **pyelftools** is ``scripts/readelf.py``, which is a (fairly faithful) clone of the ``readelf`` program from GNU binutils. ``readelf.py`` serves at least these purposes:

#. A showcase for the abilities of ``elftools``. Its existence and ability to clone a lot of the functionality of GNU readelf is a powerful proof of concept for the library, showing that it indeed provides comprehensive ELF and DWARF parsing and decoding services.

#. A helpful example of usage for the library. You can examine its output and then look at the source code to see how it uses ``elftools`` to produce such output.

#. It's being used in the testing of ``elftools``.

Detailed usage
--------------

Basic concepts
""""""""""""""

All the classes mentioned in this and subsequent sections have comprehensive documentation strings that explain how to construct them and to use their methods. For convenience, whenever this guide mentions a class for the first time, it will also specify the file in which it can be found relative to the source distribution directory of **pyelftools**. The user is expected to examine this documentation for the classes that are of interest to him.

If you find any part of the documentation lacking, don't hesitate to file a report in the issue tracker (https://github.com/eliben/pyelftools/issues).

API levels
""""""""""

**pyelftools** can be seen as providing two different levels of APIs (although this isn't directly evident in the code). There's a low-level API that directly exposes the parsed contents of the streams representing ELF and DWARF data. Most of the code, however, is geared towards providing a high-level API that encapsulates these details in Python classes with attributes and behavior. This guide mostly focuses on the high-level API. For the low-level API take a look at the "Structs and headers" section and some of the examples.

Main entry point
""""""""""""""""

The main entry point to **pyelftools** is the ``ELFFile`` class (in file ``elftools/elf/elffile.py``). It simply accepts a stream object (which can be an open file, an in-memory ``StringIO`` or any other stream-like Python object), and does some basic analysis, such as verifying that the stream indeed contains a valid ELF object. Methods of this class allow you to enumerate the sections and segments it contains, as well as extracting the debug information contained within it.

ELF sections
""""""""""""

The main informational unit of an ELF file is a "section". The ``ELFFile`` entry point class has several methods for conveniently accessing the sections in an ELF file (for example, count the sections, get the Nth sections, iterate over all sections, etc.)

The object returned to represent a section will always implement at least the interface defined by the ``Section`` class (``elftools/elf/sections.py``). This class represents a generic ELF section, allowing dictionary-like access to its header, and getting its data as a buffer.

Some sections in ELF are special and their semantics is at least partially defined by the standard and various platform ABIs. **pyelftools** knows about these sections, and has special classes for representing them. For example, when reading a symbol table section from the stream, ``ELFFile`` will return a ``SymbolTableSection`` class (also in ``elftools/elf/sections.py``). This class provides additional methods for interacting with the symbol table. There are other special sections **pyelftools** is familiar with, for example ``StringTableSection`` (in the same file) and ``RelocationSection`` (in ``elftools/elf/relocation.py``).

ELF segments
""""""""""""

Similarly to sections, an ELF segment has a class in **pyelftools** to represent it. This is ``Segment`` (in file ``elftools/elf/segments.py``). To get to the object's segments, use the relevant methods in ``ELFFile`` to count and enumerate them. There are also some special segment classes that have more information about well-known segments. Take a look at ``elftools/elf/segments.py`` for more details.

Structs and headers
"""""""""""""""""""

Most objects in ELF and DWARF have "headers", and such objects usually provide dictionary-like access to attributes in these headers. The names of fields in the headers try to match the ELF and DWARF standards whenever possible. In any case, it is easy to examine the whole header by printing the ``header`` attribute (when it exists, it's mentioned as a publicly accessible attribute in the documentation string of the relevant class).

In addition, it's possible to see how these headers are parsed in the parts of **pyelftools** which define "structs". For ELF this is in ``elftools/elf/structs.py``, and for DWARF this is in ``elftools/dwarf/structs.py``. A word of warning: these are parts of the low-level API, use them at your own peril.

DWARF information
"""""""""""""""""

The main entry point for DWARF information in **pyelftools** is the class ``DWARFInfo`` in ``elftools/dwarf/dwarfinfo.py``. Care was taken to make ``DWARFInfo`` independent of ``ELFFile``, to allow its usage independently of any specific container (for example, to parse DWARF data directly emitted into memory or dumped to a file).

That said, the easiest way to get a ``DWARFInfo`` object is just to ask ``ELFFile`` for it. The latter has a method named ``has_dwarf_info`` which checks whether the ELF object has debugging information in it at all. If the answer is positive, use the ``get_dwarf_info`` method to get a ``DWARFInfo`` object representing this DWARF information. ``ELFFile`` does all the required book-keeping (including even relocation of DWARF sections), and the resulting ``DWARFInfo`` is ready for usage.

Contrary to ELF with its structured set of sections and segments, DWARF information is quite ad hoc for the special needs it serves. Each DWARF section contains different information that has to be decoded and interpreted in a special manner. **pyelftools** attempts to provide a convenient Pythonic API for this information whenever possible. There's no way around it - to even understand the API one must have some grasp of the `DWARF standard <https://dwarfstd.org/>`__.

Limitations
-----------

**pyelftools** is a work in progress, and some things still aren't implemented. Following is the current list of known limitations.

ELF
"""

* Extended numbering of segment and section headers.
* The current focus of the library is on Intel's x86 and x64 architectures, with some ARM support added recently.
* Special handling of TBSS sections .

DWARF
"""""

Some DWARF sections are not read and decoded yet:

* ``.debug_macinfo``

While it would certainly be nice to support all DWARF sections from the start, don't be deterred by this limitation - the *really* important parts of DWARF debug info are the ones already supported. Most of the missing sections don't contain additional debugging information, but are accelerated lookup tables for parts of it.





