# tests/test_verify.py

import unittest

from stac_merkle_tree_cli.compute_merkle_info import compute_merkle_root
from stac_merkle_tree_cli.verify import verify_node


class TestVerifyNode(unittest.TestCase):
    """Tests for the verify_node function."""

    def setUp(self):
        """Set up test fixtures."""
        self.hash_method = {"function": "sha256", "ordering": "ascending"}

    def test_verify_single_item(self):
        """Test verification of a single item (leaf node)."""
        item_node = {
            "node_id": "item1",
            "type": "Item",
            "merkle:object_hash": "a" * 64,
        }
        result = verify_node(item_node, self.hash_method)
        self.assertTrue(result)

    def test_verify_collection_success(self):
        """Test verification of a collection with valid root."""
        child_hash = "b" * 64
        child = {
            "node_id": "item1",
            "type": "Item",
            "merkle:object_hash": child_hash,
        }

        self_hash = "c" * 64

        hashes = [child_hash, self_hash]
        hashes.sort()
        expected_root = compute_merkle_root(hashes, self.hash_method)

        collection_node = {
            "node_id": "collection1",
            "type": "Collection",
            "merkle:object_hash": self_hash,
            "merkle:root": expected_root,
            "children": [child],
        }

        self.assertTrue(verify_node(collection_node, self.hash_method))

    def test_verify_collection_failure(self):
        """Test verification fails when root is tampered."""
        collection_node = {
            "node_id": "collection1",
            "type": "Collection",
            "merkle:object_hash": "c" * 64,
            "merkle:root": "bad_root" * 8,
            "children": [
                {"node_id": "item1", "type": "Item", "merkle:object_hash": "b" * 64}
            ],
        }
        self.assertFalse(verify_node(collection_node, self.hash_method))

    def test_verify_nested_structure_success(self):
        """
        Test the 'Ripple Effect': Catalog -> Collection -> Item
        Catalog uses Collection's ROOT, Collection uses Item's OBJECT HASH.
        """
        item_hash = "1" * 64
        item_node = {"node_id": "i1", "type": "Item", "merkle:object_hash": item_hash}

        coll_obj_hash = "2" * 64
        hashes_l2 = [item_hash, coll_obj_hash]
        hashes_l2.sort()
        coll_root = compute_merkle_root(hashes_l2, self.hash_method)

        coll_node = {
            "node_id": "c1",
            "type": "Collection",
            "merkle:object_hash": coll_obj_hash,
            "merkle:root": coll_root,
            "children": [item_node],
        }

        cat_obj_hash = "3" * 64
        hashes_l1 = [coll_root, cat_obj_hash]
        hashes_l1.sort()
        cat_root = compute_merkle_root(hashes_l1, self.hash_method)

        cat_node = {
            "node_id": "root",
            "type": "Catalog",
            "merkle:object_hash": cat_obj_hash,
            "merkle:root": cat_root,
            "children": [coll_node],
        }

        self.assertTrue(verify_node(cat_node, self.hash_method))

    def test_verify_empty_collection_success(self):
        """Test verification of an empty collection with valid root."""
        self_hash = "d" * 64
        expected_root = compute_merkle_root([self_hash], self.hash_method)

        collection_node = {
            "node_id": "empty_collection",
            "type": "Collection",
            "merkle:object_hash": self_hash,
            "merkle:root": expected_root,
            "children": [],
        }
        self.assertTrue(verify_node(collection_node, self.hash_method))

    def test_verify_multiple_items_success(self):
        """Test verification of a collection with multiple items."""
        item1_hash = "e" * 64
        item2_hash = "f" * 64
        item3_hash = "0" * 64

        item1 = {"node_id": "item1", "type": "Item", "merkle:object_hash": item1_hash}
        item2 = {"node_id": "item2", "type": "Item", "merkle:object_hash": item2_hash}
        item3 = {"node_id": "item3", "type": "Item", "merkle:object_hash": item3_hash}

        coll_obj_hash = "1" * 64

        hashes = [item1_hash, item2_hash, item3_hash, coll_obj_hash]
        hashes.sort()
        expected_root = compute_merkle_root(hashes, self.hash_method)

        collection_node = {
            "node_id": "collection1",
            "type": "Collection",
            "merkle:object_hash": coll_obj_hash,
            "merkle:root": expected_root,
            "children": [item1, item2, item3],
        }

        self.assertTrue(verify_node(collection_node, self.hash_method))


if __name__ == "__main__":
    unittest.main()
