from __future__ import annotations
from typing import Callable, Optional, Tuple
import pyphonetics  # type: ignore
import Levenshtein  # type: ignore

from src.lib.identity import Identity
from src.lib.declared_names_table import (
    DeclaredNamesTable,
    DeclaredProperty,
    DECLARED_PRIMARY,
    DECLARED_VARIANT,
    KNOWN_PROPERTY,
)
from src.lib.parse_error import ParseError
from src.reporter.name_column_parser import FOUND_PROPERTY

SynonymMap = dict[str, list[Identity]]  # identity.primary yields the primary
FABRICATED_NAME = Identity.Property("fabricated to unify name")


class IdentityCatalog:
    """Dictionary mapping identities to all known and proposed variations of their
    names, including a 'primary' variation, which has the longest name. Each node in
    the catalog provides either a list of Identity objects representing different
    names of the same identity or a list of different people sharing a portion of
    their names in common."""

    rsoundex = pyphonetics.RefinedSoundex()  # type: ignore
    lein = pyphonetics.Lein()  # type: ignore

    class _NameNode:
        """A node representing a component of an identity name for inclusion in a
        tree that is specific to the last name, organizing name variety under that
        last name."""

        # _NameNode is a nested class so that it can begin with '_' and yet still
        # be accessed for testing purposes (via IdentityCatalog).

        def __init__(self, name: Optional[str]):
            self.name = name  # portion of name associated with this node
            self.identities: Optional[
                list[Identity]
            ] = None  # identities having present name
            self.child_map: Optional[
                list[Tuple[Optional[str], IdentityCatalog._NameNode]]
            ] = None
            self.parent: Optional[IdentityCatalog._NameNode] = None

        def add_child(self, child: IdentityCatalog._NameNode) -> None:
            if self.child_map is None:  # this approach optimizes memory use
                self.child_map = [(child.name, child)]
            else:
                self.child_map.append((child.name, child))
            child.parent = self

        def add_identity(self, identity: Identity) -> None:
            if self.identities is None:  # this approach optimizes memory use
                self.identities = [identity]
            else:
                self.identities.append(identity)

        def add_identities(self, identities: list[Identity]) -> None:
            if self.identities is None:  # this approach optimizes memory use
                self.identities = identities[:]  # make a copy
            else:
                self.identities += identities

        def get_child(self, key: Optional[str]) -> Optional[IdentityCatalog._NameNode]:
            if self.child_map is None:
                return None
            for mapping in self.child_map:
                if mapping[0] == key:
                    return mapping[1]
            return None

        def print(self, level: int) -> None:
            name = '"%s"' % self.name if self.name is not None else "None"
            print(" " * level * 2, "%s:" % name)
            level += 1
            if self.identities is not None:
                identities = ['"%s"' % str(p) for p in self.identities]
                print(" " * level * 2, ", ".join(identities))
            if self.child_map is not None:
                for mapping in self.child_map:
                    mapping[1].print(level)

    def __init__(self, declared_names_table: Optional[DeclaredNamesTable] = None):
        self._declared_names_table = declared_names_table
        self._identities_by_name: dict[str, Identity] = {}
        self._last_name_trees: dict[str, IdentityCatalog._NameNode] = {}
        self._synonyms_by_primary_name: SynonymMap = {}
        self._is_compiled = False
        self._autocorrected_names: dict[str, bool] = {}
        self._lexically_modified_names: dict[str, bool] = {}
        self._already_added: list[Identity] = []

    def add(self, identity: Identity) -> None:
        """Adds an identity to the catalog."""

        # Merge duplicate instances of identity into the same instance, keeping
        # a record of all their associated raw names.

        identity_name = str(identity)
        try:
            existing_identity = self._identities_by_name[identity_name]
            existing_identity.occurrence_count += 1
            existing_identity.merge_with(identity)
        except KeyError:
            self._identities_by_name[identity_name] = identity

    def compile(self) -> None:
        """Compiles all the added names into last name trees. Used primarily in tests
        for examining last name trees prior to consolidation."""

        if not self._is_compiled:
            for identity in self._identities_by_name.values():
                self._add_identity_to_tree(identity)
            self._is_compiled = True

    def correct_and_consolidate(
        self,
        unify_names_by_sound: bool = False,
        merge_with_reference_names: bool = False,
    ) -> None:
        """Consolidates variant names under their primary names, inferring associated
        names by their common initials, when possible, and applying the officially
        designated variants from the provided table of declared names.."""

        # First record the names that have been lexically altered and then apply
        # any declared corrections.

        for identity in self._identities_by_name.values():
            identity_name = str(identity)
            raw_names = identity.get_raw_names()
            if raw_names is not None:
                for raw_name in raw_names:
                    if raw_name != identity_name:
                        self._lexically_modified_names[raw_name] = True
            if self._declared_names_table:
                self._declared_names_table.correct_identity_name(identity)

        # Unify names by the similarity of their pronunciation, except for distinctions
        # found among the declared names. Done by correcting names.

        if unify_names_by_sound:
            if self._is_compiled:
                raise Exception("Too late to unify by sound; catalog already compiled")
            self._unify_last_names_by_sound()

        # Reconstruct the catalog using the corrected names.

        identities_with_corrected_duplicates = list(self._identities_by_name.values())
        self._identities_by_name = {}
        for identity in identities_with_corrected_duplicates:
            identity.occurrence_count -= 1  # undo additional add
            self.add(identity)

        # Add all known names so they can occur as primaries for variants of them
        # that are found in the data, even if they themselves aren't in the data.

        if self._declared_names_table:
            for identity in self._declared_names_table.get_known_identity_iterator():
                if merge_with_reference_names or identity.has_property(KNOWN_PROPERTY):
                    self.add(identity)

        # Build the name trees, hierarchically organizing names by last names and
        # common initials, so that primaries and variants can be identified.

        if not self._is_compiled:
            self.compile()

        # Generate the synonymous variants from consolidated node trees.

        self._compute_synonyms()

        # Revise primary names to conform with declared primary names.

        if self._declared_names_table is not None:
            # Duplicate the items so that reconciliation may modify the dictionary.
            items = list(self._identities_by_name.items())
            for identity_name, identity in items:
                self._reconcile_with_declared_names(
                    identity_name, identity, merge_with_reference_names
                )

        # Reconstruct the node tree from scratch, including the new declared primary
        # identities but not the new declared variants, but this time don't reconsolidate
        # or apply the declared names table. The primaries need to be re-evaluated because
        # some conflicting primaries may have been deleted, allowing for greature
        # unification of names; don't include the declared variants in this consolidation
        # because they'll mess up the new unification.

        self._last_name_trees = {}
        declared_variants: list[Identity] = []
        for identity in self._identities_by_name.values():
            if self._is_declared_variant(identity):
                if identity is self._get_top_primary(identity):
                    self._add_identity_to_tree(identity)
                else:
                    declared_variants.append(identity)
            else:
                # Clear the primaries of the identities that can be mapped to new
                # primaries, excluding all declaree identities.
                identity.primary = None
                self._add_identity_to_tree(identity)

        # Reconsolidate the node tree, respecting the established declared primaries
        # and reintegrating the declared variants that had been withheld.

        self._synonyms_by_primary_name = {}
        self._compute_synonyms()
        for variant in declared_variants:
            variant.primary = self._get_top_primary(variant)
            self._synonyms_by_primary_name[str(variant.primary)].append(variant)

        # Remove all primaries not containing a found variant and all variants
        # of found primaries that are not themselves found in the data.

        primary_names_to_remove: list[str] = []
        for primary_name, synonyms in self._synonyms_by_primary_name.items():
            found_data = False
            for identity in synonyms:
                if identity.has_property(FOUND_PROPERTY):
                    found_data = True
                elif identity.primary is not identity:
                    synonyms.remove(identity)
                    del self._identities_by_name[str(identity)]
            if not found_data:
                # Can't delete from a collection over which we're iterating.
                primary_names_to_remove.append(primary_name)
        for primary_name in primary_names_to_remove:
            del self._synonyms_by_primary_name[primary_name]

        # This code confirms that all primaries have been set up properly.
        #
        # for primary_name, synonyms in self._synonyms_by_primary_name.items():
        #     primary = synonyms[0]
        #     for identity in synonyms:
        #         assert identity.primary is primary

        # Add missing declared properties to the names.

        if self._declared_names_table is not None:
            for identity in self._identities_by_name.values():
                self._declared_names_table.add_properties(identity)

    def count_identities(self):
        return len(self._identities_by_name)

    def count_primaries(self):
        return len(self._synonyms_by_primary_name)

    def find_variant(
        self, last_name: str, test: Callable[[Identity], bool]
    ) -> Optional[Identity]:
        # TODO: This method was being used for test purposes.
        return self._find_variant(self._last_name_trees[last_name.lower()], test)

    def get_identities(self) -> list[Identity]:
        return list(self._identities_by_name.values())

    def get_identity_by_name(self, name: str) -> Identity:
        return self._identities_by_name[name]

    def get_synonyms(self) -> SynonymMap:
        """Returns a dictionary mapping each primary identity name to a list of the
        names secondary names that are considered synonymous with the primary name.
        The catalog must have previously been consolidated via `consolidate()`."""

        return self._synonyms_by_primary_name

    def is_autocorrected_name(self, raw_name: str) -> bool:
        try:
            return self._autocorrected_names[raw_name]
        except KeyError:
            return False

    def is_lexically_modified_name(self, raw_name: str) -> bool:
        try:
            return self._lexically_modified_names[raw_name]
        except KeyError:
            return False

    def _add_identity_to_tree(self, identity: Identity) -> Identity:
        """Added the identity to the tree for its last name, placing the identity
        at the appropriate place in the tree, reflecting common inititals."""

        # Look up the identity last name in the catalog to find the root node
        # for the last name's name tree. If the name is found, either point to the
        # node for the identity name suffix or else create an node for the suffix.

        last_name_key = identity.last_name.lower()
        suffix_key = (
            identity.name_suffix.lower() if identity.name_suffix is not None else None
        )
        try:
            last_name_node = self._last_name_trees[last_name_key]
            leaf_node = last_name_node.get_child(suffix_key)
            if leaf_node is None:
                leaf_node = IdentityCatalog._NameNode(suffix_key)
                last_name_node.add_child(leaf_node)

        # If the last name is not in the catalog, create an node for it and
        # give a child for the identity name suffix.

        except KeyError:
            last_name_node = IdentityCatalog._NameNode(identity.last_name)
            self._last_name_trees[last_name_key] = last_name_node
            leaf_node = IdentityCatalog._NameNode(suffix_key)
            last_name_node.add_child(leaf_node)

        if identity.initial_names is not None:

            # Step down existing portion of tree that matches the initial names.

            child_node: Optional[IdentityCatalog._NameNode] = leaf_node
            it = _InitialNameKeyIterator(identity.initial_names.lower())
            current_name: Optional[str] = None
            while child_node is not None and it.has_next():
                leaf_node = child_node
                try:
                    current_name = next(it)
                except ParseError as e:
                    raise Exception(
                        "Failed to parse '%s': %s" % (str(identity), e.message)
                    )
                child_node = child_node.get_child(current_name)

            # If we reached a leaf of the tree, extend the tree to accommodate
            # any remaining initial names of the provided identity.

            if child_node is None:
                child_node = IdentityCatalog._NameNode(current_name)
                leaf_node.add_child(child_node)
                leaf_node = child_node
                while it.has_next():
                    child_node = IdentityCatalog._NameNode(next(it))
                    leaf_node.add_child(child_node)
                    leaf_node = child_node
                if child_node is not None:
                    leaf_node = child_node
            else:
                leaf_node = child_node

        # Indicate that an identity has the name sequence at this point in tree,
        # and return the standard instance of Identity for this name.

        if leaf_node.identities is None:
            leaf_node.add_identity(identity)
        else:
            found_identity = False
            for leaf_identity in leaf_node.identities:
                if leaf_identity == identity:
                    found_identity = True
                    leaf_identity.merge_with(identity)
                    break
            if not found_identity:
                leaf_node.add_identity(identity)
        return leaf_node.identities[0]  # type: ignore

    def _add_synonyms(self, for_identity: Identity, synonyms: list[Identity]) -> None:
        identity_name = str(self._get_top_primary(for_identity))
        try:
            self._synonyms_by_primary_name[identity_name] += synonyms
        except KeyError:
            self._synonyms_by_primary_name[identity_name] = synonyms

    def _collect_branch_identities(self, node: IdentityCatalog._NameNode) -> None:
        """Push identities in the tree to their next lower branching point, leaf, or
        identity with a declared and previously-established primary. Assign the primary
        for each identity to the first identity listed among the synonyms at this
        point, unless this first identity already has a primary, in which case assign
        each identity a primary equal to that of the first identity's primary."""

        # Push the identities down to either the end of the current branch (where it
        # either branches into multiple children or there are no children) or to the
        # node for a declared identity with a previously-established primary, stopping
        # the downward push only after reaching a branching node or a leaf node.

        collected_identities: list[Identity] = []
        while node.child_map and len(node.child_map) == 1:
            if node.identities is not None:
                first_identity = node.identities[0]
                # Don't push down declared names or full names that are only single-
                # letter abbreviations.
                if first_identity.has_property(DeclaredProperty) or (
                    first_identity.initial_names is None
                    and len(first_identity.last_name) == 2
                    and first_identity.last_name[1] == "."
                ):
                    self._make_synonymous(node, collected_identities)
                    collected_identities = []
                else:
                    collected_identities += node.identities
                    node.identities = None
            node = node.child_map[0][1]

        # Collect the identities in each child branch.

        self._make_synonymous(node, collected_identities)
        if node.child_map:
            for mapping in node.child_map:
                self._collect_branch_identities(mapping[1])

    def _collect_leaf_nodes(
        self,
        leaf_nodes: list[IdentityCatalog._NameNode],
        below_node: IdentityCatalog._NameNode,
    ) -> None:
        """Adds to `distinct_identities` all instances of Identity found in the leaf
        nodes of the subtree rooted at `node`."""

        if below_node.child_map is None:
            assert below_node.identities is not None
            leaf_nodes.append(below_node)
        else:
            for mapping in below_node.child_map:
                self._collect_leaf_nodes(leaf_nodes, mapping[1])

    def _collect_synonyms(self, node: IdentityCatalog._NameNode) -> None:
        """Collect the synonyms for the branch of the tree starting at `node` for
        their associated primaries, and then do the same for each child branch."""

        while True:
            if node.identities is not None:
                branch_identity = node.identities[0]
                assert branch_identity.primary is not None
                self._add_synonyms(branch_identity.primary, node.identities)
            if not node.child_map or len(node.child_map) != 1:
                break
            node = node.child_map[0][1]

        # Collect the synonyms in each child branch.

        if node.child_map:
            for mapping in node.child_map:
                self._collect_synonyms(mapping[1])

    def _compute_synonyms(self):
        """Compute and assemble apparently synonymous identities."""

        # Consolidates apparently synonymous identities together at the ends of their
        # branches, allowing for subsequent retrieval of the synonyms for any last
        # name and of the primary synonym for any given identity.

        for root_node in self._last_name_trees.values():
            leaf_nodes = self._get_leaf_nodes(root_node)
            self._consolidate_tree(root_node, leaf_nodes)
            self._collect_branch_identities(root_node)

        # Generate the synonymous variants according to the consolidated node trees.

        for last_name in self._last_name_trees.keys():
            self._collect_synonyms(self._last_name_trees[last_name.lower()])

    def _consolidate_tree(
        self,
        root_node: IdentityCatalog._NameNode,
        distinct_identity_nodes: list[IdentityCatalog._NameNode],
    ) -> None:
        """Revises the node tree by treating any initial for a name as equivalent
        to a name that has that initial, provided that no two different names have
        that initial."""

        for identity_node in distinct_identity_nodes:
            identities = identity_node.identities
            assert identities is not None
            # Only consider reassigning identities not known to be primaries.
            if identities[0].primary is not identities[0]:
                identity_node_stack: list[IdentityCatalog._NameNode] = []
                node = identity_node
                while node is not None:
                    identity_node_stack.append(node)
                    node = node.parent
                self._reassign_identity(root_node, identity_node_stack, None, False)

    def _find_variant(
        self, node: IdentityCatalog._NameNode, test: Callable[[Identity], bool]
    ) -> Optional[Identity]:
        if node.identities is not None:
            for identity in node.identities:
                if test(identity):
                    return identity
        if node.child_map is not None:
            for mapping in node.child_map:
                identity = self._find_variant(mapping[1], test)
                if identity is not None:
                    return identity
        return None

    def _get_leaf_nodes(
        self, root_node: IdentityCatalog._NameNode
    ) -> list[IdentityCatalog._NameNode]:
        """Returns a list of all the nodes that are leaf nodes of the tree."""

        leaf_nodes: list[IdentityCatalog._NameNode] = []
        self._collect_leaf_nodes(leaf_nodes, root_node)
        return leaf_nodes

    def _get_top_primary(self, identity: Identity) -> Identity:
        """Returns the root primary to which the identity ultimately maps."""

        primary = identity.primary
        assert primary is not None
        while primary.primary is not primary:
            assert primary.primary is not None, "Identity(%s).primary" % str(primary)
            primary = primary.primary
        return primary

    def _infer_descendent_names(
        self, test_initial_names: str, identity_node: IdentityCatalog._NameNode
    ) -> None:
        """Create a new Identity with an inferred name for each node in this
        branch corresponding to at least one identity, and add this inferred
        identity to the start of the node's list of identities so that it ends
        up becoming the primary Identity for the remaining instances."""

        if identity_node.identities is not None:
            identity = identity_node.identities[0]
            identity_initial_names = identity.initial_names
            assert identity_initial_names
            diff_offset = 0
            while diff_offset < len(test_initial_names):
                if (
                    test_initial_names[diff_offset]
                    != identity_initial_names[diff_offset]
                ):
                    break
                diff_offset += 1
            end_of_test_names = diff_offset
            while (
                end_of_test_names < len(test_initial_names)
                and test_initial_names[end_of_test_names] != " "
            ):
                end_of_test_names += 1
            inferred_identity = Identity(
                identity.last_name,
                (
                    test_initial_names[0:end_of_test_names]
                    + identity_initial_names[diff_offset + 1 :]
                ),
                identity.name_suffix,
                [FABRICATED_NAME],
            )
            identity_node.identities.insert(0, inferred_identity)

        if identity_node.child_map is not None:
            for mapping in identity_node.child_map:
                self._infer_descendent_names(test_initial_names, mapping[1])

    def _is_declared_variant(self, identity: Identity) -> bool:
        """Indicates whether the identity is a variant of a declared name."""

        primary = identity.primary
        if primary is None:
            return False

        is_declared_variant = primary.has_property(DeclaredProperty)
        while primary is not None and primary.primary is not primary:
            primary = primary.primary
            if primary is not None and not is_declared_variant:
                is_declared_variant = primary.has_property(DeclaredProperty)
        return is_declared_variant

    def _make_synonymous(
        self, node: IdentityCatalog._NameNode, collected_identities: list[Identity]
    ) -> None:
        """Makes the identities already at the given node synonymous with the
        provided identities, setting all their primaries to the first identity
        already in the node."""

        if collected_identities:
            if node.identities is None:
                node.identities = collected_identities
            else:
                node.identities += collected_identities

        if node.identities:
            primary_identity = node.identities[0]
            for identity in node.identities:
                identity.primary = primary_identity

    def _move_variant_to_primary(
        self, variant: Identity, new_primary: Identity
    ) -> None:
        """Move the indicated variant from variant.primary to the indicated primary,
        which must already be a primary the catalog, though it need not have any
        variants. If the variant and the primary are the same identity, make the
        variant a primary. Regardless, also move variations of the variant to the new
        primary. Note that the provided variant may already be its own primary."""

        new_primary_name = str(new_primary)
        old_primary = variant.primary
        assert old_primary is not None
        old_primary_name = str(old_primary)
        new_primary_variants = self._synonyms_by_primary_name[new_primary_name]
        old_primary_variants = self._synonyms_by_primary_name[old_primary_name]

        # Place the variant in its new position.

        if variant == new_primary:  # if turning the variant into a primary
            if old_primary is variant:  # if variant is already this primary
                return  # nothing to do
            old_primary_variants.remove(variant)
            self._synonyms_by_primary_name[new_primary_name] = [variant]
        else:  # if variant will be a variant under the new primary
            if variant.primary is variant:  # if variant is already a primary
                del self._synonyms_by_primary_name[old_primary_name]
                for old_primary_variant in old_primary_variants:
                    new_primary_variants.append(old_primary_variant)
                    old_primary_variant.primary = new_primary
                old_primary_variants.clear()
            else:
                new_primary_variants.append(variant)
                old_primary_variants.remove(variant)

        variant.primary = new_primary

        # If the old primary was fabricated, all variants have to be removed for a
        # subsequent reassessment of whether a fabricated identity is still needed.

        if old_primary.has_property(FABRICATED_NAME):
            for remaining_variant in old_primary_variants:
                self._synonyms_by_primary_name[str(remaining_variant)] = [
                    remaining_variant
                ]
                remaining_variant.primary = remaining_variant
            del self._synonyms_by_primary_name[old_primary_name]

    def _prune_identity_branch(
        self,
        identity_node: IdentityCatalog._NameNode,
        matched_node: IdentityCatalog._NameNode,
    ) -> None:
        """Prune from the tree the branch containing the indicated identity up to
        where it branches from other identities in the tree. In the process, append
        all identities encountered to the provided `matched_node`."""

        if identity_node.identities is not None:
            matched_node.add_identities(identity_node.identities)
        child_node = identity_node
        node = identity_node.parent
        while (
            node is not None and node.child_map is not None and len(node.child_map) == 1
        ):
            if node.identities is not None:  # is never identity_node
                matched_node.add_identities(node.identities)
            child_node = node
            node = node.parent
        if node is not None and node.child_map is not None:
            assert len(node.child_map) > 1
            for mapping in node.child_map:
                if mapping[1] == child_node:
                    node.child_map.remove(mapping)

    def _reassign_identity(
        self,
        test_node: IdentityCatalog._NameNode,
        identity_node_stack: list[IdentityCatalog._NameNode],
        test_initial_names: Optional[str],
        is_on_inferred_branch: bool,
    ) -> bool:
        """Finds the longest name in the `test_node` tree for the identity whose
        branch of nodes are found in `identity_node_stack`, which lists nodes
        deepest first. Once found, if it is different from the branch indicated by
        the stack, move the identities in that branch over to the found node and
        then delete the found node up to the point where it branches."""

        # On each call, compare test_node and the last element of identity_node_stack
        # for agreement. If they agree, unify the identity_node_stack branch with the
        # test_node and return True. If they disagree, return False.

        # If we land at the original identity node, no reassignment is available.

        if test_node is identity_node_stack[0]:
            return False
        identity_node = identity_node_stack.pop()  # corresponds to test_node
        test_name = test_node.name
        identity_name = identity_node.name
        if test_node.identities is not None:
            test_initial_names = test_node.identities[0].initial_names

        # Handle the case where the test and identity node names are the same.

        if test_name == identity_name:

            # A test node that has no children matches an identity node that has no
            # children; otherwise the identity node has the more complete name, in
            # which case we might need to add an inferred name.

            if test_node.child_map is None:
                if identity_node.child_map is None:
                    self._prune_identity_branch(identity_node, test_node)
                    return True
                elif is_on_inferred_branch and (
                    test_node.identities is None
                    or not test_node.identities[0].has_property(DeclaredProperty)
                ):

                    # Move the remainder of the identity branch to the test branch.

                    orphan_identity_node = identity_node
                    identity_node = identity_node_stack.pop()
                    test_node.add_child(identity_node)

                    # Create an inferred Identity for descendent names.

                    assert test_initial_names is not None
                    self._infer_descendent_names(test_initial_names, identity_node)

                    # Prune the bit of the identity branch that we're not keeping.

                    self._prune_identity_branch(orphan_identity_node, test_node)
                    return True

            # If the test node has children, continue testing with the children.

            else:
                if identity_node.child_map is None:
                    if identity_node is not test_node:
                        self._prune_identity_branch(identity_node, test_node)
                    return True
                for mapping in test_node.child_map:
                    if self._reassign_identity(
                        mapping[1],
                        identity_node_stack,
                        test_initial_names,
                        is_on_inferred_branch,
                    ):
                        return True

        # If the present nodes do not exactly equal in name and the test node is
        # a full name and the identity node is an initial, it's possible that the
        # initial is for a child of the test node.

        elif (
            test_node.child_map is not None
            and identity_name is not None
            and test_name is not None
            and identity_name[1] == "."
            and test_name[1] != "."
        ):
            for mapping in test_node.child_map:
                if mapping[0] == identity_name:
                    # Attempt to map identity to a subtree of test_node.
                    identity_node_stack.append(identity_node)
                    if self._reassign_identity(
                        mapping[1], identity_node_stack, test_initial_names, True
                    ):
                        return True
                    identity_node_stack.pop()  # revert to prior state

        # If no match was found in this subtree, put the current identity node back
        # on the stack for use by other branches that the caller tries.

        identity_node_stack.append(identity_node)
        return False

    def _reconcile_with_declared_names(
        self, identity_name: str, identity: Identity, merge_with_reference_names: bool
    ) -> None:

        # Determine the primary that declared for the identity.

        assert self._declared_names_table is not None
        new_primary = self._declared_names_table.get_primary(
            identity_name, merge_with_reference_names
        )

        # Handle the case where the the identity's primary is a declared name.

        if new_primary is not None:

            # Indicate that the identity is in the declared names table and that its
            # assigned primary is to remain unchanged in subsequent processes.

            if new_primary == identity:
                identity.add_property(DECLARED_PRIMARY)
            else:
                identity.add_property(DECLARED_VARIANT)

            # If the declared names table confirms the identity's current primary,
            # just mark the primary as confirmed.

            if new_primary == identity.primary:
                assert identity.primary is not None
                identity.primary.add_property(DECLARED_PRIMARY)

            # If the declared names table remaps the identity to a different primary,
            # move the identity to the new primary.

            else:

                # If the new primary already exists among the collected identities, make
                # it primary if it isn't already primary.

                new_primary_name = str(new_primary)
                if new_primary_name in self._identities_by_name:
                    new_primary = self._identities_by_name[new_primary_name]
                    new_primary.add_property(DECLARED_PRIMARY)
                    if new_primary.primary is not new_primary:
                        if new_primary.primary is None:
                            raise Exception(
                                "identity = %s, identity.primary = %s, new_primary = %s, %s"
                                % (
                                    str(identity),
                                    str(identity.primary),
                                    new_primary_name,
                                    str([p.name for p in identity.get_properties()]),
                                )
                            )
                        assert new_primary.primary is not None
                        self._synonyms_by_primary_name[new_primary_name] = [new_primary]
                        self._move_variant_to_primary(new_primary, new_primary)

                # If the new primary does not already exist among the collected
                # identities, record the new primary.

                else:
                    new_primary.primary = new_primary
                    self._identities_by_name[new_primary_name] = new_primary
                    self._synonyms_by_primary_name[new_primary_name] = [new_primary]

                # Moved the provided identity and its implied variants to the new primary.

                self._move_variant_to_primary(identity, new_primary)

    def _to_sound_code(self, name: str) -> str:

        # RefinedSoundex seems to be the most discriminat, but it occassionall goofs,
        # so I'm joining it with the liberal Lein algorithm to undo the goofs.

        try:
            sound_code1: str = self.rsoundex.phonetics(name)  # type: ignore
            sound_code2: str = self.lein.phonetics(name)  # type: ignore
        except IndexError:
            # If a phonetic code is not avialable for a character, require exact name.
            return "=" + name
        return "%s/%s" % (sound_code1, sound_code2)

    def _unify_last_names_by_sound(self) -> None:

        # Assign a sound code to each identity for how its last name is pronounced,
        # and group the identities by the pronunciations of their last names.

        name_groups_by_sound: dict[str, list[_NameTracker]] = {}

        for identity in self._identities_by_name.values():

            last_name_sound = self._to_sound_code(identity.last_name)
            tracker = _NameTracker(identity)
            try:
                name_groups_by_sound[last_name_sound].append(tracker)
            except KeyError:
                name_groups_by_sound[last_name_sound] = [tracker]

        # Unify the names in each group of similarly-pronounced last names.

        starting_tracker = _NameTracker(Identity("dummy"))

        for name_group in name_groups_by_sound.values():
            if len(name_group) == 1:
                continue  # ignore groups of one, which having nothing to unify
            if not self._declared_names_table:
                continue  # skip this loop and avoid an indentation

            # Identify all declared last names from this group.

            declared_name_tracker_map: dict[str, _NameTracker] = {}
            for name_tracker in name_group:
                lower_last_name = name_tracker.lower_name
                if lower_last_name in declared_name_tracker_map:
                    declared_name_tracker_map[lower_last_name].merge(name_tracker)
                elif self._declared_names_table.is_declared_last_name(lower_last_name):
                    declared_name_tracker_map[lower_last_name] = name_tracker

            # Change last names to their closest declared name, if any is closest,
            # keeping track of identities not closest to any one declared name.

            uncorrected_name_tracker_map: dict[str, _NameTracker] = {}
            for undeclared_name_tracker in name_group:
                lower_undeclared_name = undeclared_name_tracker.lower_name
                if undeclared_name_tracker.lower_name not in declared_name_tracker_map:
                    closest_name_tracker: Optional[_NameTracker] = None
                    closest_distance = 1000
                    for declared_name_tracker in declared_name_tracker_map.values():
                        distance: int = Levenshtein.distance(  # type: ignore
                            lower_undeclared_name,
                            declared_name_tracker.lower_name,
                        )
                        if distance < closest_distance:
                            closest_distance = distance
                            closest_name_tracker = declared_name_tracker
                        elif distance == closest_distance:
                            closest_name_tracker = None
                    if closest_name_tracker is None:
                        if lower_undeclared_name in uncorrected_name_tracker_map:
                            uncorrected_name_tracker_map[lower_undeclared_name].merge(
                                undeclared_name_tracker
                            )
                        else:
                            uncorrected_name_tracker_map[
                                lower_undeclared_name
                            ] = undeclared_name_tracker
                    else:
                        self._change_last_name(
                            undeclared_name_tracker, closest_name_tracker.name
                        )

            # For the names that are equally close to multiple declared last names or
            # that aren't close to any declared last names because there are no
            # declared last names with this pronunciation, apply another algorithm.
            # But if there's only one name left, it can't correct to any other name.

            if len(uncorrected_name_tracker_map) > 1:

                # Use a spelling that occurs at least two more times than all
                # other spellings, if such a spelling exists.

                uncorrected_name_trackers = uncorrected_name_tracker_map.values()

                max_tracker = starting_tracker
                for name_tracker in uncorrected_name_trackers:
                    if name_tracker.count >= max_tracker.count:
                        max_tracker = name_tracker

                at_least_two_greater = True
                for name_tracker in uncorrected_name_trackers:
                    if (
                        name_tracker is not max_tracker
                        and name_tracker.count >= max_tracker.count - 2
                    ):
                        at_least_two_greater = False

                if at_least_two_greater:
                    for name_tracker in uncorrected_name_trackers:
                        self._change_last_name(name_tracker, max_tracker.name)

                # If no such spelling exists, use the spelling that all spellings
                # are closest to according to the sum of their distances apart, if
                # any one such spelling exists.

                else:
                    distance_sums: list[int] = []
                    for name_tracker1 in uncorrected_name_trackers:
                        sum: int = 0
                        for name_tracker2 in uncorrected_name_trackers:
                            sum += Levenshtein.distance(  # type: ignore
                                name_tracker1.lower_name, name_tracker2.lower_name
                            )
                        distance_sums.append(sum)

                    min_tracker = starting_tracker
                    min_sum = 100000
                    for i, name_tracker in enumerate(uncorrected_name_trackers):
                        if distance_sums[i] < min_sum:
                            min_sum = distance_sums[i]
                            min_tracker = name_tracker
                        elif distance_sums[i] == min_sum:
                            max_tracker = None

                    if min_tracker is not None:
                        for name_tracker in uncorrected_name_trackers:
                            self._change_last_name(name_tracker, min_tracker.name)

    def _change_last_name(self, name_tracker: _NameTracker, new_last_name: str) -> None:
        for identity in name_tracker.identities:
            # Only mark as phonetically altered names that actually change.
            if identity.last_name != new_last_name:
                raw_names = identity.get_raw_names()
                if raw_names is not None:
                    for raw_name in raw_names:
                        self._autocorrected_names[raw_name] = True
        name_tracker.set_last_name(new_last_name)  # must follow above


class _InitialNameKeyIterator:
    def __init__(self, initial_names: str):
        # In order to save memory, avoids creating an array via split().
        self._initial_names: str = initial_names
        self._offset: int = 0
        self._next_key: Optional[str] = None

    def __iter__(self):
        return self

    def __next__(self) -> str:
        if self._next_key is not None:
            key = self._next_key
            self._next_key = None
            return key
        if self._offset == len(self._initial_names):
            raise StopIteration
        next_offset = self._initial_names.find(" ", self._offset)
        if next_offset < 0:
            next_offset = len(self._initial_names)
            key = self._initial_names[self._offset : next_offset]
        else:
            key = self._initial_names[self._offset : next_offset]
            next_offset += 1
        if len(key) < 2:
            raise ParseError("Initial name '%s' too short" % key)
        if key[1] != ".":
            self._next_key = key
            key = key[0] + "."
        self._offset = next_offset
        return key

    def has_next(self) -> bool:
        return self._next_key is not None or self._offset != len(self._initial_names)


class _NameTracker:
    def __init__(self, identity: Identity):
        self.name = identity.last_name
        self.lower_name = self.name.lower()
        self.count = identity.occurrence_count
        self.identities = [identity]

    def merge(self, other: _NameTracker) -> None:
        self.count += other.count
        self.identities += other.identities

    def set_last_name(self, last_name: str) -> None:
        for identity in self.identities:
            identity.last_name = last_name
