#-------------------------------------------------------------------------------
# elftools: dwarf/compileunit.py
#
# DWARF compile unit
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from functools import lru_cache
from .die import DIE
from ..common.utils import dwarf_assert


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

        # Cache of Top DIE of this CU
        self._top_die = None
        self.configure_die_cache()

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
        if self._top_die is not None:
            return self._top_die

        top = DIE(
                cu=self,
                stream=self.dwarfinfo.debug_info_sec.stream,
                offset=self.cu_die_offset)

        top._translate_indirect_attributes() # Can't translate indirect attributes until the top DIE has been parsed to the end
        self._top_die = top
        return top

    def has_top_DIE(self):
        """ Returns whether the top DIE in this CU has already been parsed and cached.
            No parsing on demand!
        """
        return self._top_die is not None

    @property
    def size(self):
        return self['unit_length'] + self.structs.initial_length_field_size()

    def get_DIE_from_refaddr(self, refaddr):
        """ Obtain a DIE contained in this CU from a reference.

            refaddr:
                The offset into the .debug_info section, which must be
                contained in this CU or a DWARFError will be raised.

            When using a reference class attribute with a form that is
            relative to the compile unit, add unit add the compile unit's
            .cu_addr before calling this function.
        """
        # All DIEs are after the cu header and within the unit
        dwarf_assert(
            self.cu_die_offset <= refaddr < self.cu_offset + self.size,
            'refaddr %s not in DIE range of CU %s' % (refaddr, self.cu_offset))

        return self._get_cached_DIE(refaddr)

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

        # `cur_offset` tracks the stream offset of the next DIE to yield
        # as we iterate over our children,
        cur_offset = die.offset + die.size

        while True:
            child = self._get_cached_DIE(cur_offset)

            child.set_parent(die)

            if child.is_null():
                die._terminator = child
                return

            yield child

            if not child.has_children:
                cur_offset += child.size
            elif "DW_AT_sibling" in child.attributes:
                sibling = child.attributes["DW_AT_sibling"]
                if sibling.form in ('DW_FORM_ref1', 'DW_FORM_ref2',
                                    'DW_FORM_ref4', 'DW_FORM_ref8',
                                    'DW_FORM_ref', 'DW_FORM_ref_udata'):
                    cur_offset = sibling.value + self.cu_offset
                elif sibling.form == 'DW_FORM_ref_addr':
                    cur_offset = sibling.value
                else:
                    raise NotImplementedError('sibling in form %s' % sibling.form)
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
    def configure_die_cache(self, cachesize = None):
        @lru_cache(maxsize=cachesize)
        def _get_cached_DIE(offset):
            """ Given a DIE offset, look it up in the cache.  If not present,
                parse the DIE and insert it into the cache.

                offset:
                    The offset of the DIE in the debug_info section to retrieve.

                The stream reference is copied from the top DIE.  The top die will
                also be parsed and cached if needed.

                See also get_DIE_from_refaddr(self, refaddr).
            """
            # The top die must be in the cache if any DIE is in the cache.
            # The stream is the same for all DIEs in this CU, so populate
            # the top DIE and obtain a reference to its stream.

            top_die_stream = self.get_top_DIE().stream
            die = DIE(cu=self, stream=top_die_stream, offset=offset)

            return die

        self._get_cached_DIE = _get_cached_DIE

    #------ PRIVATE ------#

    def __getitem__(self, name):
        """ Implement dict-like access to header entries
        """
        return self.header[name]

    def _iter_DIE_subtree(self, die):
        """ Given a DIE, this yields it with its subtree including null DIEs
            (child list terminators).
        """
        # If the die is an imported unit, replace it with what it refers to if
        # we can
        if die.tag == 'DW_TAG_imported_unit' and self.dwarfinfo.supplementary_dwarfinfo:
            die = die.get_DIE_from_attribute('DW_AT_import')
        yield die
        if die.has_children:
            for c in die.iter_children():
                for d in die.cu._iter_DIE_subtree(c):
                    yield d
            yield die._terminator


