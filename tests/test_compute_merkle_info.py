# tests/test_compute_merkle_info.py

import unittest
import json
import hashlib
import tempfile
import shutil
from pathlib import Path
from stac_merkle_tree_cli.compute_merkle_info import compute_merkle_object_hash, remove_merkle_fields, process_collection

class TestComputeMerkleObjectHash(unittest.TestCase):
    def test_compute_hash_all_fields_item(self):
        """
        Test hashing all fields for a STAC Item, ensuring Merkle fields are excluded.
        """
        stac_object = {
            "type": "Feature",
            "id": "test-item",
            "properties": {
                "datetime": "2024-10-15T12:00:00Z",
                "other_property": "value",
                "merkle:object_hash": "should be excluded"
            },
            "geometry": {},
            "links": [],
            "assets": {},
            "merkle:object_hash": "should be excluded at top level",
            "merkle:hash_method": "should be excluded at top level"
        }

        hash_method = {
            "function": "sha256",
            "fields": ["*"],
            "ordering": "ascending",
            "description": "Test hash method."
        }

        result = compute_merkle_object_hash(stac_object, hash_method)

        # Expected data excludes Merkle fields recursively
        expected_data = {
            "type": "Feature",
            "id": "test-item",
            "properties": {
                "datetime": "2024-10-15T12:00:00Z",
                "other_property": "value"
            },
            "geometry": {},
            "links": [],
            "assets": {}
        }
        expected_json_str = json.dumps(expected_data, sort_keys=True, separators=(',', ':'))
        expected_hash = hashlib.sha256(expected_json_str.encode('utf-8')).hexdigest()
        self.assertEqual(result, expected_hash)

    def test_compute_hash_all_fields_collection(self):
        """
        Test hashing all fields for a STAC Collection, ensuring Merkle fields are excluded.
        """
        stac_object = {
            "type": "Collection",
            "id": "test-collection",
            "description": "A test collection",
            "extent": {},
            "links": [],
            "merkle:object_hash": "should be excluded",
            "merkle:hash_method": "should be excluded",
            "merkle:root": "should be excluded"
        }

        hash_method = {
            "function": "sha256",
            "fields": ["*"],
            "ordering": "ascending",
            "description": "Test hash method."
        }

        result = compute_merkle_object_hash(stac_object, hash_method)

        # Expected data excludes Merkle fields
        expected_data = {
            "type": "Collection",
            "id": "test-collection",
            "description": "A test collection",
            "extent": {},
            "links": []
        }
        expected_json_str = json.dumps(expected_data, sort_keys=True, separators=(',', ':'))
        expected_hash = hashlib.sha256(expected_json_str.encode('utf-8')).hexdigest()
        self.assertEqual(result, expected_hash)

    def test_compute_hash_specific_fields_item(self):
        """
        Test hashing specific fields for a STAC Item, ensuring Merkle fields are excluded.
        """
        stac_object = {
            "type": "Feature",
            "id": "test-item",
            "properties": {
                "other_property": "value",
                "datetime": "2024-10-15T12:00:00Z",
                "extra_property": "should be excluded",
                "merkle:object_hash": "should be excluded"
            },
            "geometry": {},
            "links": []
        }

        hash_method = {
            "function": "sha256",
            "fields": ["id", "properties"],
            "ordering": "ascending",
            "description": "Test hash method with specific fields."
        }

        result = compute_merkle_object_hash(stac_object, hash_method)

        # Expected data includes only specified fields, excluding Merkle fields
        selected_data = {field: stac_object[field] for field in hash_method['fields']}
        expected_data = remove_merkle_fields(selected_data)

        # Debugging: Print the expected data being hashed
        print("Expected data in test:", json.dumps(expected_data, indent=2, sort_keys=True))
        print("Expected JSON string in test:", json.dumps(expected_data, sort_keys=True, separators=(',', ':')))

        expected_json_str = json.dumps(expected_data, sort_keys=True, separators=(',', ':'))

        # Compute expected hash
        expected_hash = hashlib.sha256(expected_json_str.encode('utf-8')).hexdigest()

        # Debugging: Print actual data being hashed in the function
        print("Data to hash in function:", json.dumps(expected_data, indent=2, sort_keys=True))
        print("JSON string in function:", expected_json_str)
        print("Expected hash:", expected_hash)
        print("Actual hash:", result)

        self.assertEqual(result, expected_hash)

    def test_compute_hash_unsupported_function(self):
        """
        Test behavior when an unsupported hash function is specified.
        """
        stac_object = {
            "id": "test-object"
        }
        hash_method = {
            "function": "unsupported-hash",
            "fields": ["*"],
            "ordering": "ascending",
            "description": "Test unsupported hash function."
        }
        with self.assertRaises(ValueError) as context:
            compute_merkle_object_hash(stac_object, hash_method)
        self.assertIn("Unsupported hash function", str(context.exception))

    def test_compute_hash_missing_fields(self):
        """
        Test behavior when specified fields are missing from the object.
        """
        stac_object = {
            "id": "test-object",
            "some_field": "some value"
        }
        hash_method = {
            "function": "sha256",
            "fields": ["non_existent_field"],
            "ordering": "ascending",
            "description": "Test with missing fields."
        }
        result = compute_merkle_object_hash(stac_object, hash_method)
        # Expected data is empty because the specified field doesn't exist
        expected_data = {}
        expected_json_str = json.dumps(expected_data, sort_keys=True, separators=(',', ':'))
        expected_hash = hashlib.sha256(expected_json_str.encode('utf-8')).hexdigest()
        self.assertEqual(result, expected_hash)

    def test_compute_hash_different_hash_functions(self):
        """
        Test hashing with different hash functions.
        """
        stac_object = {
            "id": "test-object"
        }
        hash_functions = ["sha256", "md5", "sha1", "sha512"]
        for func in hash_functions:
            hash_method = {
                "function": func,
                "fields": ["*"],
                "ordering": "ascending",
                "description": f"Test with hash function {func}."
            }
            result = compute_merkle_object_hash(stac_object, hash_method)
            expected_data = {
                "id": "test-object"
            }
            expected_json_str = json.dumps(expected_data, sort_keys=True, separators=(',', ':'))
            hash_func = getattr(hashlib, func.replace('-', '').lower())
            expected_hash = hash_func(expected_json_str.encode('utf-8')).hexdigest()
            self.assertEqual(result, expected_hash)

    def test_compute_hash_excludes_merkle_fields(self):
        """
        Test that Merkle fields are excluded from the hash computation.
        """
        stac_object = {
            "id": "test-object",
            "merkle:object_hash": "should be excluded",
            "merkle:hash_method": "should be excluded",
            "merkle:root": "should be excluded",
            "other_field": "value"
        }
        hash_method = {
            "function": "sha256",
            "fields": ["*"],
            "ordering": "ascending",
            "description": "Test exclusion of Merkle fields."
        }
        result = compute_merkle_object_hash(stac_object, hash_method)
        # Expected data excludes Merkle fields
        expected_data = {
            "id": "test-object",
            "other_field": "value"
        }
        expected_json_str = json.dumps(expected_data, sort_keys=True, separators=(',', ':'))
        expected_hash = hashlib.sha256(expected_json_str.encode('utf-8')).hexdigest()
        self.assertEqual(result, expected_hash)

    def test_process_collection_with_nested_items(self):
        """
        Test processing a collection with nested items.
        """
        # Create a temporary directory to simulate the file structure
        temp_dir = tempfile.mkdtemp()
        try:
            # Create collection.json file
            collection_path = Path(temp_dir) / "collection.json"
            collection_json = {
                "type": "Collection",
                "id": "test-collection",
                "description": "A test collection",
                "extent": {},
                "links": [],
                "merkle:object_hash": "should be excluded",
                "merkle:hash_method": {
                    "function": "sha256",
                    "fields": ["*"],
                    "ordering": "ascending"
                }
            }
            with open(collection_path, 'w', encoding='utf-8') as f:
                json.dump(collection_json, f, indent=2)

            # Create nested item files
            item1_path = Path(temp_dir) / "item1" / "item1.json"
            item1_path.parent.mkdir(parents=True, exist_ok=True)
            item_json = {
                "type": "Feature",
                "id": "test-item",
                "properties": {
                    "datetime": "2024-10-15T12:00:00Z",
                    "other_property": "value"
                },
                "geometry": {},
                "links": []
            }
            with open(item1_path, 'w', encoding='utf-8') as f:
                json.dump(item_json, f, indent=2)

            item2_path = Path(temp_dir) / "item2" / "item2.json"
            item2_path.parent.mkdir(parents=True, exist_ok=True)
            with open(item2_path, 'w', encoding='utf-8') as f:
                json.dump(item_json, f, indent=2)

            # Set hash_method
            hash_method = {
                "function": "sha256",
                "fields": ["*"],
                "ordering": "ascending"
            }

            # Call process_collection function
            collection_hash = process_collection(collection_path, hash_method)

            # Assertions
            self.assertTrue(collection_hash)
        finally:
            # Clean up the temporary directory
            shutil.rmtree(temp_dir)

if __name__ == '__main__':
    unittest.main()
