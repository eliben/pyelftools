Introduction: what is pyelftools?
---------------------------------

**pyelftools** is a pure-Python library for parsing and analyzing ELF files
and DWARF debugging information. See the
`User's guide <https://bitbucket.org/eliben/pyelftools/wiki/Userguide>`_
for more details.

Pre-requisites
--------------

As a user of **pyelftools**, one only needs Python to run. It works with
Python versions 2.6, 2.7 and 3.x (x >= 2). For hacking on **pyelftools** the
requirements are a bit more strict, please see the
`hacking guide <https://bitbucket.org/eliben/pyelftools/wiki/Hacking>`_.

Installing
----------

**pyelftools** can be installed from PyPI (Python package index)::

    > pip install pyelftools

Alternatively, you can download the source distribution for the most recent and
historic versions from the *Downloads* tab on the `pyelftools project page
<https://bitbucket.org/eliben/pyelftools>`_ (by going to *Tags*). Then, you can
install from source, as usual::

    > python setup.py install

Since **pyelftools** is a work in progress, it's recommended to have the most
recent version of the code. This can be done by downloading the ``tip`` tag
("trunk") from *Downloads* or just cloning the Mercurial repository.

How to use it?
--------------

**pyelftools** is a regular Python library: you import and invoke it from your
own code. For a detailed usage guide and links to examples, please consult the
`user's guide <https://bitbucket.org/eliben/pyelftools/wiki/Userguide>`_.

License
-------

**pyelftools** is open source software. Its code is in the public domain. See
the ``LICENSE`` file for more details.




