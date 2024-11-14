# tests/test_compute_merkle_info.py

import unittest
from stac_merkle_tree_cli.compute_merkle_info import compute_merkle_object_hash

class TestComputeMerkleObjectHash(unittest.TestCase):
    def test_compute_hash_all_fields(self):
        stac_object = {
            "id": "test-item",
            "properties": {
                "datetime": "2024-10-15T12:00:00Z",
                "other_property": "value"
            },
            "geometry": {}
        }
        hash_method = {
            "function": "sha256",
            "fields": ["*"],
            "ordering": "ascending",
            "description": "Test hash method."
        }
        expected_hash = "..."  # Compute the expected hash manually or using known input
        result = compute_merkle_object_hash(stac_object, hash_method)
        self.assertEqual(len(result), 64)  # SHA-256 produces 64 hex characters

if __name__ == '__main__':
    unittest.main()
