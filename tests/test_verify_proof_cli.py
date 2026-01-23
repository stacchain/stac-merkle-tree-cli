# tests/test_verify_proof_cli.py

import json
import tempfile
import unittest
from pathlib import Path

from click.testing import CliRunner

from stac_merkle_tree_cli.cli import main
from stac_merkle_tree_cli.verify_proof import compute_hash, verify_item


class TestVerifyProofCommand(unittest.TestCase):
    """Tests for the verify-proof CLI command."""

    def setUp(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_verify_proof_success_ignore_links(self):
        """Test successful verification with --ignore-links (default)."""
        # Create a simple item
        item = {
            "id": "test-item",
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [0, 0]},
            "properties": {"datetime": "2024-01-01T00:00:00Z"},
            "assets": {},
            "links": [{"rel": "self", "href": "http://example.com/item.json"}],
        }

        # Compute hash without links
        clean_item = {
            k: v
            for k, v in item.items()
            if k
            not in ["merkle:object_hash", "merkle:root", "merkle:hash_method", "links"]
        }
        target_hash = compute_hash(clean_item)

        # Create a simple proof
        proof = {
            "target_hash": target_hash,
            "root": target_hash,
            "path": [],
        }

        # Write files
        item_path = self.temp_path / "item.json"
        proof_path = self.temp_path / "item.proof.json"

        with item_path.open("w") as f:
            json.dump(item, f)
        with proof_path.open("w") as f:
            json.dump(proof, f)

        # Run command with default --ignore-links
        result = self.runner.invoke(
            main, ["verify-proof", str(item_path), str(proof_path)]
        )

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Verification SUCCESS", result.output)

    def test_verify_proof_success_include_links(self):
        """Test successful verification with --include-links."""
        # Create a simple item with links
        item = {
            "id": "test-item",
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [0, 0]},
            "properties": {"datetime": "2024-01-01T00:00:00Z"},
            "assets": {},
            "links": [{"rel": "self", "href": "http://example.com/item.json"}],
        }

        # Compute hash WITH links
        clean_item = {
            k: v
            for k, v in item.items()
            if k not in ["merkle:object_hash", "merkle:root", "merkle:hash_method"]
        }
        target_hash = compute_hash(clean_item)

        # Create a simple proof
        proof = {
            "target_hash": target_hash,
            "root": target_hash,
            "path": [],
        }

        # Write files
        item_path = self.temp_path / "item.json"
        proof_path = self.temp_path / "item.proof.json"

        with item_path.open("w") as f:
            json.dump(item, f)
        with proof_path.open("w") as f:
            json.dump(proof, f)

        # Run command with --include-links
        result = self.runner.invoke(
            main, ["verify-proof", str(item_path), str(proof_path), "--include-links"]
        )

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Verification SUCCESS", result.output)

    def test_verify_proof_failure_mismatch_links_setting(self):
        """Test failure when links setting doesn't match between proof generation and verification."""
        # Create a simple item with links
        item = {
            "id": "test-item",
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [0, 0]},
            "properties": {"datetime": "2024-01-01T00:00:00Z"},
            "assets": {},
            "links": [{"rel": "self", "href": "http://example.com/item.json"}],
        }

        # Compute hash WITH links (as if proof was generated with --include-links)
        clean_item_with_links = {
            k: v
            for k, v in item.items()
            if k not in ["merkle:object_hash", "merkle:root", "merkle:hash_method"]
        }
        target_hash = compute_hash(clean_item_with_links)

        # Create a simple proof
        proof = {
            "target_hash": target_hash,
            "root": target_hash,
            "path": [],
        }

        # Write files
        item_path = self.temp_path / "item.json"
        proof_path = self.temp_path / "item.proof.json"

        with item_path.open("w") as f:
            json.dump(item, f)
        with proof_path.open("w") as f:
            json.dump(proof, f)

        # Run command with --ignore-links (default) - should fail
        result = self.runner.invoke(
            main, ["verify-proof", str(item_path), str(proof_path)]
        )

        self.assertEqual(result.exit_code, 1)
        self.assertIn("Verification FAILED", result.output)

    def test_verify_proof_failure_data_tampered(self):
        """Test failure when item data has been tampered with."""
        # Create a simple item
        item = {
            "id": "test-item",
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [0, 0]},
            "properties": {"datetime": "2024-01-01T00:00:00Z"},
            "assets": {},
            "links": [],
        }

        # Compute hash
        clean_item = {
            k: v
            for k, v in item.items()
            if k
            not in ["merkle:object_hash", "merkle:root", "merkle:hash_method", "links"]
        }
        target_hash = compute_hash(clean_item)

        # Create a simple proof
        proof = {
            "target_hash": target_hash,
            "root": target_hash,
            "path": [],
        }

        # Write files
        item_path = self.temp_path / "item.json"
        proof_path = self.temp_path / "item.proof.json"

        with item_path.open("w") as f:
            json.dump(item, f)
        with proof_path.open("w") as f:
            json.dump(proof, f)

        # Tamper with the item
        item["properties"]["datetime"] = "2024-01-02T00:00:00Z"
        with item_path.open("w") as f:
            json.dump(item, f)

        # Run command - should fail
        result = self.runner.invoke(
            main, ["verify-proof", str(item_path), str(proof_path)]
        )

        self.assertEqual(result.exit_code, 1)
        self.assertIn("Identity Mismatch", result.output)

    def test_verify_proof_failure_invalid_json(self):
        """Test failure when proof file is invalid JSON."""
        # Create a simple item
        item = {
            "id": "test-item",
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [0, 0]},
            "properties": {"datetime": "2024-01-01T00:00:00Z"},
            "assets": {},
            "links": [],
        }

        # Write files
        item_path = self.temp_path / "item.json"
        proof_path = self.temp_path / "item.proof.json"

        with item_path.open("w") as f:
            json.dump(item, f)

        # Write invalid JSON to proof file
        with proof_path.open("w") as f:
            f.write("{ invalid json }")

        # Run command - should fail
        result = self.runner.invoke(
            main, ["verify-proof", str(item_path), str(proof_path)]
        )

        self.assertEqual(result.exit_code, 1)
        self.assertIn("Invalid JSON", result.output)

    def test_verify_proof_failure_missing_file(self):
        """Test failure when item or proof file doesn't exist."""
        item_path = self.temp_path / "nonexistent_item.json"
        proof_path = self.temp_path / "nonexistent_proof.json"

        # Run command - should fail
        result = self.runner.invoke(
            main, ["verify-proof", str(item_path), str(proof_path)]
        )

        self.assertNotEqual(result.exit_code, 0)


class TestVerifyItemFunction(unittest.TestCase):
    """Tests for the verify_item function with ignore_links parameter."""

    def test_verify_item_ignore_links_true(self):
        """Test verify_item with ignore_links=True (default)."""
        item = {
            "id": "test-item",
            "type": "Feature",
            "properties": {"datetime": "2024-01-01T00:00:00Z"},
            "links": [{"rel": "self", "href": "http://example.com"}],
        }

        clean_item = {
            k: v
            for k, v in item.items()
            if k
            not in ["merkle:object_hash", "merkle:root", "merkle:hash_method", "links"]
        }
        target_hash = compute_hash(clean_item)

        proof = {
            "target_hash": target_hash,
            "root": target_hash,
            "path": [],
        }

        result = verify_item(item, proof, ignore_links=True)
        self.assertTrue(result)

    def test_verify_item_ignore_links_false(self):
        """Test verify_item with ignore_links=False."""
        item = {
            "id": "test-item",
            "type": "Feature",
            "properties": {"datetime": "2024-01-01T00:00:00Z"},
            "links": [{"rel": "self", "href": "http://example.com"}],
        }

        clean_item = {
            k: v
            for k, v in item.items()
            if k not in ["merkle:object_hash", "merkle:root", "merkle:hash_method"]
        }
        target_hash = compute_hash(clean_item)

        proof = {
            "target_hash": target_hash,
            "root": target_hash,
            "path": [],
        }

        result = verify_item(item, proof, ignore_links=False)
        self.assertTrue(result)

    def test_verify_item_mismatch_with_ignore_links_true(self):
        """Test verify_item fails when links are included but ignore_links=True."""
        item = {
            "id": "test-item",
            "type": "Feature",
            "properties": {"datetime": "2024-01-01T00:00:00Z"},
            "links": [{"rel": "self", "href": "http://example.com"}],
        }

        # Proof was generated WITH links
        clean_item = {
            k: v
            for k, v in item.items()
            if k not in ["merkle:object_hash", "merkle:root", "merkle:hash_method"]
        }
        target_hash = compute_hash(clean_item)

        proof = {
            "target_hash": target_hash,
            "root": target_hash,
            "path": [],
        }

        # Verify with ignore_links=True (default) - should fail
        result = verify_item(item, proof, ignore_links=True)
        self.assertFalse(result)
