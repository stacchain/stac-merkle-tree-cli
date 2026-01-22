# tests/test_proofs.py

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from stac_merkle_tree_cli.proofs import (
    compute_binary_layer_proof,
    find_node_path,
    generate_item_proofs,
    update_item_with_link,
)


class TestComputeBinaryLayerProof(unittest.TestCase):
    def test_single_node(self):
        """Test proof generation with a single node."""
        hashes = ["0000000000000000000000000000000000000000000000000000000000000001"]
        proof = compute_binary_layer_proof(hashes, 0)
        self.assertEqual(proof, [])

    def test_two_nodes(self):
        """Test proof generation with two nodes."""
        hashes = [
            "0000000000000000000000000000000000000000000000000000000000000001",
            "0000000000000000000000000000000000000000000000000000000000000002",
        ]
        proof = compute_binary_layer_proof(hashes, 0)
        self.assertEqual(len(proof), 1)
        self.assertEqual(proof[0]["position"], "right")
        self.assertEqual(proof[0]["hash"], hashes[1])

    def test_three_nodes(self):
        """Test proof generation with three nodes (odd number)."""
        hashes = [
            "0000000000000000000000000000000000000000000000000000000000000001",
            "0000000000000000000000000000000000000000000000000000000000000002",
            "0000000000000000000000000000000000000000000000000000000000000003",
        ]
        proof = compute_binary_layer_proof(hashes, 0)
        self.assertEqual(len(proof), 2)
        self.assertEqual(proof[0]["position"], "right")
        self.assertEqual(proof[0]["hash"], hashes[1])

    def test_four_nodes(self):
        """Test proof generation with four nodes."""
        hashes = [
            "0000000000000000000000000000000000000000000000000000000000000001",
            "0000000000000000000000000000000000000000000000000000000000000002",
            "0000000000000000000000000000000000000000000000000000000000000003",
            "0000000000000000000000000000000000000000000000000000000000000004",
        ]
        proof = compute_binary_layer_proof(hashes, 0)
        self.assertEqual(len(proof), 2)

    def test_target_index_right_child(self):
        """Test proof for right child (odd index)."""
        hashes = [
            "0000000000000000000000000000000000000000000000000000000000000001",
            "0000000000000000000000000000000000000000000000000000000000000002",
            "0000000000000000000000000000000000000000000000000000000000000003",
            "0000000000000000000000000000000000000000000000000000000000000004",
        ]
        proof = compute_binary_layer_proof(hashes, 1)
        self.assertEqual(len(proof), 2)
        self.assertEqual(proof[0]["position"], "left")
        self.assertEqual(proof[0]["hash"], hashes[0])


class TestFindNodePath(unittest.TestCase):
    def setUp(self):
        """Set up test tree structure."""
        self.tree = {
            "node_id": "root",
            "type": "Catalog",
            "merkle:object_hash": "root_hash",
            "merkle:root": "root_root",
            "children": [
                {
                    "node_id": "collection1",
                    "type": "Collection",
                    "merkle:object_hash": "col1_hash",
                    "merkle:root": "col1_root",
                    "children": [
                        {
                            "node_id": "item1",
                            "type": "Item",
                            "merkle:object_hash": "item1_hash",
                        },
                        {
                            "node_id": "item2",
                            "type": "Item",
                            "merkle:object_hash": "item2_hash",
                        },
                    ],
                },
                {
                    "node_id": "collection2",
                    "type": "Collection",
                    "merkle:object_hash": "col2_hash",
                    "merkle:root": "col2_root",
                    "children": [
                        {
                            "node_id": "item3",
                            "type": "Item",
                            "merkle:object_hash": "item3_hash",
                        }
                    ],
                },
            ],
        }

    def test_find_root(self):
        """Test finding the root node."""
        path = find_node_path(self.tree, "root")
        self.assertIsNotNone(path)
        self.assertEqual(len(path), 1)
        self.assertEqual(path[0]["node_id"], "root")

    def test_find_collection(self):
        """Test finding a collection node."""
        path = find_node_path(self.tree, "collection1")
        self.assertIsNotNone(path)
        self.assertEqual(len(path), 2)
        self.assertEqual(path[0]["node_id"], "root")
        self.assertEqual(path[1]["node_id"], "collection1")

    def test_find_item(self):
        """Test finding an item node."""
        path = find_node_path(self.tree, "item1")
        self.assertIsNotNone(path)
        self.assertEqual(len(path), 3)
        self.assertEqual(path[0]["node_id"], "root")
        self.assertEqual(path[1]["node_id"], "collection1")
        self.assertEqual(path[2]["node_id"], "item1")

    def test_find_nonexistent_node(self):
        """Test finding a node that doesn't exist."""
        path = find_node_path(self.tree, "nonexistent")
        self.assertIsNone(path)

    def test_find_item_in_second_collection(self):
        """Test finding an item in the second collection."""
        path = find_node_path(self.tree, "item3")
        self.assertIsNotNone(path)
        self.assertEqual(len(path), 3)
        self.assertEqual(path[1]["node_id"], "collection2")
        self.assertEqual(path[2]["node_id"], "item3")


class TestUpdateItemWithLink(unittest.TestCase):
    def setUp(self):
        """Set up a temporary directory for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.item_path = Path(self.temp_dir) / "item.json"

    def tearDown(self):
        """Clean up the temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_add_proof_link_to_item(self):
        """Test adding a merkle-proof link to an item."""
        item_data = {
            "type": "Feature",
            "id": "test-item",
            "properties": {},
            "geometry": {},
            "links": [],
            "assets": {},
        }
        with self.item_path.open("w") as f:
            json.dump(item_data, f)

        update_item_with_link(
            self.item_path, "test-item.proof.json", "https://example.com/proofs"
        )

        with self.item_path.open("r") as f:
            updated_item = json.load(f)

        # Check that the link was added
        proof_links = [
            link for link in updated_item["links"] if link["rel"] == "merkle-proof"
        ]
        self.assertEqual(len(proof_links), 1)
        self.assertEqual(
            proof_links[0]["href"], "https://example.com/proofs/test-item.proof.json"
        )
        self.assertEqual(proof_links[0]["type"], "application/json")

    def test_replace_existing_proof_link(self):
        """Test that existing proof links are replaced."""
        item_data = {
            "type": "Feature",
            "id": "test-item",
            "properties": {},
            "geometry": {},
            "links": [
                {
                    "rel": "merkle-proof",
                    "href": "https://old.example.com/old.proof.json",
                    "type": "application/json",
                }
            ],
            "assets": {},
        }
        with self.item_path.open("w") as f:
            json.dump(item_data, f)

        update_item_with_link(
            self.item_path, "test-item.proof.json", "https://example.com/proofs"
        )

        with self.item_path.open("r") as f:
            updated_item = json.load(f)

        # Check that only one proof link exists
        proof_links = [
            link for link in updated_item["links"] if link["rel"] == "merkle-proof"
        ]
        self.assertEqual(len(proof_links), 1)
        self.assertEqual(
            proof_links[0]["href"], "https://example.com/proofs/test-item.proof.json"
        )

    def test_preserve_other_links(self):
        """Test that other links are preserved."""
        item_data = {
            "type": "Feature",
            "id": "test-item",
            "properties": {},
            "geometry": {},
            "links": [
                {"rel": "self", "href": "https://example.com/item.json"},
                {"rel": "parent", "href": "https://example.com/collection.json"},
            ],
            "assets": {},
        }
        with self.item_path.open("w") as f:
            json.dump(item_data, f)

        update_item_with_link(
            self.item_path, "test-item.proof.json", "https://example.com/proofs"
        )

        with self.item_path.open("r") as f:
            updated_item = json.load(f)

        # Check that other links are preserved
        self_links = [link for link in updated_item["links"] if link["rel"] == "self"]
        parent_links = [
            link for link in updated_item["links"] if link["rel"] == "parent"
        ]
        self.assertEqual(len(self_links), 1)
        self.assertEqual(len(parent_links), 1)


class TestGenerateItemProofs(unittest.TestCase):
    def setUp(self):
        """Set up a temporary catalog structure for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.catalog_dir = Path(self.temp_dir)
        self.proofs_dir = self.catalog_dir / "proofs"

        # Create a simple catalog structure
        self.create_test_catalog()

    def tearDown(self):
        """Clean up the temporary directory."""
        shutil.rmtree(self.temp_dir)

    def create_test_catalog(self):
        """Create a test catalog with items and merkle tree."""
        # Create collection directory
        collection_dir = self.catalog_dir / "collection1"
        collection_dir.mkdir()

        # Create items
        item1 = {
            "type": "Feature",
            "id": "item1",
            "properties": {},
            "geometry": {},
            "links": [],
            "assets": {},
        }
        item1_path = collection_dir / "item1.json"
        with item1_path.open("w") as f:
            json.dump(item1, f)

        item2 = {
            "type": "Feature",
            "id": "item2",
            "properties": {},
            "geometry": {},
            "links": [],
            "assets": {},
        }
        item2_path = collection_dir / "item2.json"
        with item2_path.open("w") as f:
            json.dump(item2, f)

        # Create merkle tree with valid hex hashes
        merkle_tree = {
            "node_id": "root",
            "type": "Catalog",
            "merkle:object_hash": "0000000000000000000000000000000000000000000000000000000000000001",
            "merkle:root": "0000000000000000000000000000000000000000000000000000000000000002",
            "children": [
                {
                    "node_id": "collection1",
                    "type": "Collection",
                    "merkle:object_hash": "0000000000000000000000000000000000000000000000000000000000000003",
                    "merkle:root": "0000000000000000000000000000000000000000000000000000000000000004",
                    "children": [
                        {
                            "node_id": "item1",
                            "type": "Item",
                            "merkle:object_hash": "0000000000000000000000000000000000000000000000000000000000000005",
                        },
                        {
                            "node_id": "item2",
                            "type": "Item",
                            "merkle:object_hash": "0000000000000000000000000000000000000000000000000000000000000006",
                        },
                    ],
                }
            ],
        }
        merkle_tree_path = self.catalog_dir / "merkle_tree.json"
        with merkle_tree_path.open("w") as f:
            json.dump(merkle_tree, f)

    def test_generate_proofs_creates_files(self):
        """Test that proof files are created."""
        merkle_tree_path = self.catalog_dir / "merkle_tree.json"
        generate_item_proofs(
            merkle_tree_path, str(self.proofs_dir), "https://example.com/proofs"
        )

        # Check that proof files were created
        proof_files = list(self.proofs_dir.glob("*.proof.json"))
        self.assertEqual(len(proof_files), 2)

    def test_proof_files_have_correct_structure(self):
        """Test that generated proof files have correct structure."""
        merkle_tree_path = self.catalog_dir / "merkle_tree.json"
        generate_item_proofs(
            merkle_tree_path, str(self.proofs_dir), "https://example.com/proofs"
        )

        # Check proof file structure
        proof_file = self.proofs_dir / "item1.proof.json"
        self.assertTrue(proof_file.exists())

        with proof_file.open("r") as f:
            proof = json.load(f)

        self.assertIn("target_hash", proof)
        self.assertIn("root", proof)
        self.assertIn("path", proof)

    def test_items_updated_with_proof_links(self):
        """Test that items are updated with proof links."""
        merkle_tree_path = self.catalog_dir / "merkle_tree.json"
        generate_item_proofs(
            merkle_tree_path, str(self.proofs_dir), "https://example.com/proofs"
        )

        # Check that item was updated with proof link
        item1_path = self.catalog_dir / "collection1" / "item1.json"
        with item1_path.open("r") as f:
            item1 = json.load(f)

        proof_links = [link for link in item1["links"] if link["rel"] == "merkle-proof"]
        self.assertEqual(len(proof_links), 1)
        self.assertIn("item1.proof.json", proof_links[0]["href"])


if __name__ == "__main__":
    unittest.main()
