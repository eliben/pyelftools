Introduction: what is pyelftools?
---------------------------------

**pyelftools** is a pure-Python library for parsing and analyzing ELF files
and DWARF debugging information. See the
`User's guide <https://github.com/eliben/pyelftools/wiki/User's-guide>`_
for more details.

Pre-requisites
--------------

As a user of **pyelftools**, one only needs Python to run. It works with
Python versions 2.6, 2.7 and 3.x (x >= 2). For hacking on **pyelftools** the
requirements are a bit more strict, please see the
`hacking guide <https://github.com/eliben/pyelftools/wiki/Hacking-guide>`_.

Installing
----------

**pyelftools** can be installed from PyPI (Python package index)::

    > pip install pyelftools

Alternatively, you can download the source distribution for the most recent and
historic versions from the *Downloads* tab on the `pyelftools project page
<https://github.com/eliben/pyelftools>`_ (by going to *Tags*). Then, you can
install from source, as usual::

    > python setup.py install

Since **pyelftools** is a work in progress, it's recommended to have the most
recent version of the code. This can be done by downloading the `master zip
file <https://github.com/eliben/pyelftools/archive/master.zip>`_ or just
cloning the Git repository.

How to use it?
--------------

**pyelftools** is a regular Python library: you import and invoke it from your
own code. For a detailed usage guide and links to examples, please consult the
`user's guide <https://github.com/eliben/pyelftools/wiki/User's-guide>`_.

License
-------

**pyelftools** is open source software. Its code is in the public domain. See
the ``LICENSE`` file for more details.

CI Status
---------

**pyelftools** has automatic testing enabled through the convenient
`Travis CI project <https://travis-ci.org>`_. Here is the latest build status:

.. image:: https://travis-ci.org/eliben/pyelftools.png?branch=master
  :align: center
  :target: https://travis-ci.org/eliben/pyelftools
