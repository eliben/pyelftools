#-------------------------------------------------------------------------------
# elftools: dwarf/compileunit.py
#
# DWARF compile unit
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from bisect import bisect_left
from .die import DIE


class CompileUnit(object):
    """ A DWARF compilation unit (CU).

            A normal compilation unit typically represents the text and data
            contributed to an executable by a single relocatable object file.
            It may be derived from several source files,
            including pre-processed "include files"

        Serves as a container and context to DIEs that describe objects and code
        belonging to a compilation unit.

        CU header entries can be accessed as dict keys from this object, i.e.
           cu = CompileUnit(...)
           cu['version']  # version field of the CU header

        To get the top-level DIE describing the compilation unit, call the
        get_top_DIE method.
    """
    def __init__(self, header, dwarfinfo, structs, cu_offset, cu_die_offset):
        """ header:
                CU header for this compile unit

            dwarfinfo:
                The DWARFInfo context object which created this one

            structs:
                A DWARFStructs instance suitable for this compile unit

            cu_offset:
                Offset in the stream to the beginning of this CU (its header)

            cu_die_offset:
                Offset in the stream of the top DIE of this CU
        """
        self.dwarfinfo = dwarfinfo
        self.header = header
        self.structs = structs
        self.cu_offset = cu_offset
        self.cu_die_offset = cu_die_offset

        # The abbreviation table for this CU. Filled lazily when DIEs are
        # requested.
        self._abbrev_table = None

        # A list of DIEs belonging to this CU.
        # This list is lazily constructed as DIEs are iterated over.
        self._dielist = []
        # A list of file offsets, corresponding (by index) to the DIEs
        # in `self._dielist`. This list exists separately from
        # `self._dielist` to make it binary searchable, enabling the
        # DIE population strategy used in `iter_DIE_children`.
        # Like `self._dielist`, this list is lazily constructed
        # as DIEs are iterated over.
        self._diemap = []

    def dwarf_format(self):
        """ Get the DWARF format (32 or 64) for this CU
        """
        return self.structs.dwarf_format

    def get_abbrev_table(self):
        """ Get the abbreviation table (AbbrevTable object) for this CU
        """
        if self._abbrev_table is None:
            self._abbrev_table = self.dwarfinfo.get_abbrev_table(
                self['debug_abbrev_offset'])
        return self._abbrev_table

    def get_top_DIE(self):
        """ Get the top DIE (which is either a DW_TAG_compile_unit or
            DW_TAG_partial_unit) of this CU
        """

        # Note that a top DIE always has minimal offset and is therefore
        # at the beginning of our lists, so no bisect is required.
        if len(self._diemap) > 0:
            return self._dielist[0]

        top = DIE(
                cu=self,
                stream=self.dwarfinfo.debug_info_sec.stream,
                offset=self.cu_die_offset)

        self._dielist.insert(0, top)
        self._diemap.insert(0, self.cu_die_offset)

        return top

    def iter_DIEs(self):
        """ Iterate over all the DIEs in the CU, in order of their appearance.
            Note that null DIEs will also be returned.
        """
        return self._iter_DIE_subtree(self.get_top_DIE())

    def iter_DIE_children(self, die):
        """ Given a DIE, yields either its children, without null DIE list
            terminator, or nothing, if that DIE has no children.

            The null DIE terminator is saved in that DIE when iteration ended.
        """
        if not die.has_children:
            return

        # `cur_offset` tracks the offset past our current DIE as we iterate
        # over children, providing the pivot as we bisect `self._diemap`
        # and ensuring that we insert our children (and child offsets)
        # in the correct order within both `self._dielist` and `self._diemap`.
        cur_offset = die.offset + die.size

        while True:
            i = bisect_left(self._diemap, cur_offset)
            # Note that `self._diemap` cannot be empty because a `die`, the argument,
            # is already parsed.
            if i < len(self._diemap) and cur_offset == self._diemap[i]:
                child = self._dielist[i]
            else:
                child = DIE(
                        cu=self,
                        stream=die.stream,
                        offset=cur_offset)
                self._dielist.insert(i, child)
                self._diemap.insert(i, cur_offset)

            child.set_parent(die)

            if child.is_null():
                die._terminator = child
                return

            yield child

            if not child.has_children:
                cur_offset += child.size
            elif "DW_AT_sibling" in child.attributes:
                sibling = child.attributes["DW_AT_sibling"]
                cur_offset = sibling.value + self.cu_offset
            else:
                # If no DW_AT_sibling attribute is provided by the producer
                # then the whole child subtree must be parsed to find its next
                # sibling. There is one zero byte representing null DIE
                # terminating children list. It is used to locate child subtree
                # bounds.

                # If children are not parsed yet, this instruction will manage
                # to recursive call of this function which will result in
                # setting of `_terminator` attribute of the `child`.
                if child._terminator is None:
                    for _ in self.iter_DIE_children(child):
                        pass

                cur_offset = child._terminator.offset + child._terminator.size

    #------ PRIVATE ------#

    def __getitem__(self, name):
        """ Implement dict-like access to header entries
        """
        return self.header[name]

    def _iter_DIE_subtree(self, die):
        """ Given a DIE, this yields it with its subtree including null DIEs
            (child list terminators).
        """
        yield die
        if die.has_children:
            for c in die.iter_children():
                for d in self._iter_DIE_subtree(c):
                    yield d
            yield die._terminator
