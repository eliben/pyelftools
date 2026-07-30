import unittest
from types import SimpleNamespace
from typing import cast

from elftools.dwarf.datatype_cpp import describe_cpp_datatype
from elftools.dwarf.die import DIE


class TestDatatypeCpp(unittest.TestCase):
    def test_missing_type(self):
        die = cast(DIE, SimpleNamespace(attributes={}))

        self.assertEqual(describe_cpp_datatype(die), "None")


if __name__ == "__main__":
    unittest.main()
