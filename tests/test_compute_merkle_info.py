# tests/test_compute_merkle_info.py

import unittest
import json
import hashlib
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from unittest.mock import patch
from stac_merkle_tree_cli.compute_merkle_info import (
    compute_merkle_object_hash,
    remove_merkle_fields,
    process_collection,
    process_catalog,
    is_item_directory
)


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
        selected_data = {field: stac_object[field] for field in hash_method['fields'] if field in stac_object}
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


class TestProcessCollection(unittest.TestCase):
    def setUp(self):
        """
        Set up a temporary directory for testing collections.
        """
        self.temp_dir = tempfile.mkdtemp()
        self.collections_dir = Path(self.temp_dir) / "collections"
        self.collections_dir.mkdir()

    def tearDown(self):
        """
        Clean up the temporary directory after tests.
        """
        shutil.rmtree(self.temp_dir)

    def create_collection(
        self,
        collection_id: str,
        items: List[Dict[str, Any]],
        sub_collections: Optional[List[Dict[str, Any]]] = None,
        sub_catalogs: Optional[List[Dict[str, Any]]] = None,
        nested_items: Optional[List[Dict[str, Any]]] = None,
        parent_dir: Optional[Path] = None  # New parameter
    ):
        """
        Helper function to create a collection with items, sub-collections, and sub-catalogs.

        Parameters:
        - collection_id (str): The ID of the collection to create.
        - items (List[Dict[str, Any]]): List of item dictionaries to include in the collection.
        - sub_collections (Optional[List[Dict[str, Any]]]): List of sub-collection dictionaries.
        - sub_catalogs (Optional[List[Dict[str, Any]]]): List of sub-catalog dictionaries.
        - nested_items (Optional[List[Dict[str, Any]]]): List of items directly within the collection directory.
        - parent_dir (Optional[Path]): The directory under which to create this collection. Defaults to self.collections_dir.
        """
        if parent_dir is None:
            parent_dir = self.collections_dir
        collection_dir = parent_dir / collection_id
        collection_dir.mkdir(parents=True, exist_ok=True)

        collection_json = {
            "type": "Collection",
            "id": collection_id,
            "description": f"Description for {collection_id}",
            "extent": {},
            "links": []
        }

        # Optionally add merkle:hash_method
        hash_method = {
            "function": "sha256",
            "fields": ["*"],
            "ordering": "ascending"
        }
        collection_json["merkle:hash_method"] = hash_method

        # Save collection.json
        collection_json_path = collection_dir / "collection.json"
        with collection_json_path.open('w', encoding='utf-8') as f:
            json.dump(collection_json, f, indent=2)

        # Create items
        for item in items:
            item_dir = collection_dir / item["id"]
            item_dir.mkdir(parents=True, exist_ok=True)
            item_path = item_dir / f"{item['id']}.json"
            with item_path.open('w', encoding='utf-8') as f:
                json.dump(item, f, indent=2)

        # Create sub-collections
        if sub_collections:
            for sub_col in sub_collections:
                sub_col_id = sub_col["id"]
                # Create 'collections' subdirectory within the current collection
                sub_collections_dir = collection_dir / "collections"
                sub_collections_dir.mkdir(exist_ok=True)
                # Recursively create sub-collections under the 'collections' subdirectory
                self.create_collection(
                    sub_col_id,
                    sub_col.get("items", []),
                    sub_col.get("sub_collections"),
                    sub_col.get("sub_catalogs"),
                    sub_col.get("nested_items"),
                    parent_dir=sub_collections_dir  # Pass the 'collections' subdirectory
                )

        # Create sub-catalogs
        if sub_catalogs:
            for sub_cat in sub_catalogs:
                sub_cat_id = sub_cat["id"]
                sub_cat_dir = collection_dir / sub_cat_id
                sub_cat_dir.mkdir(parents=True, exist_ok=True)
                sub_cat_json = {
                    "type": "Catalog",
                    "id": sub_cat_id,
                    "description": f"Description for {sub_cat_id}",
                    "links": []
                }
                # Optionally add merkle:hash_method
                sub_cat_json["merkle:hash_method"] = hash_method
                sub_cat_json_path = sub_cat_dir / "catalog.json"
                with sub_cat_json_path.open('w', encoding='utf-8') as f:
                    json.dump(sub_cat_json, f, indent=2)

                # Create collections within sub-catalogs
                for sub_cat_collection in sub_cat.get("collections", []):
                    self.create_collection(
                        sub_cat_collection["id"],
                        sub_cat_collection.get("items", []),
                        sub_cat_collection.get("sub_collections"),
                        sub_cat_collection.get("sub_catalogs"),
                        sub_cat_collection.get("nested_items"),
                        parent_dir=sub_cat_dir / "collections"  # Pass the 'collections' subdirectory
                    )

        # Create nested items if any (items directly within the collection directory)
        if nested_items:
            for item in nested_items:
                item_path = collection_dir / f"{item['id']}.json"
                with item_path.open('w', encoding='utf-8') as f:
                    json.dump(item, f, indent=2)

    def test_process_collection_with_nested_items(self):
        """
        Test processing a collection with items nested in their own directories.
        """
        collection_id = "collection_nested_items"
        items = [
            {
                "type": "Feature",
                "id": "item1",
                "properties": {
                    "datetime": "2024-10-18T12:00:00Z",
                    "other_property": "value1"
                },
                "geometry": {},
                "links": []
            },
            {
                "type": "Feature",
                "id": "item2",
                "properties": {
                    "datetime": "2024-10-19T12:00:00Z",
                    "other_property": "value2"
                },
                "geometry": {},
                "links": []
            }
        ]
        self.create_collection(
            collection_id,
            items=items,
            nested_items=[
                {
                    "type": "Feature",
                    "id": "item3",
                    "properties": {
                        "datetime": "2024-10-20T12:00:00Z",
                        "other_property": "value3"
                    },
                    "geometry": {},
                    "links": []
                }
            ]
        )

        collection_json_path = self.collections_dir / collection_id / "collection.json"

        # Define the hash_method
        hash_method = {
            "function": "sha256",
            "fields": ["*"],
            "ordering": "ascending",
            "description": "Test hash method."
        }

        # Process the collection via process_collection only
        collection_node = process_collection(collection_json_path, hash_method)

        # Assertions
        self.assertIsNotNone(collection_node)
        self.assertIn('node_id', collection_node)
        self.assertIn('merkle:object_hash', collection_node)
        self.assertIn('merkle:root', collection_node)
        self.assertIn('children', collection_node)

        self.assertEqual(collection_node['node_id'], collection_id)
        self.assertTrue(collection_node['merkle:object_hash'])
        self.assertTrue(collection_node['merkle:root'])
        self.assertEqual(len(collection_node['children']), 3)  # item1, item2, item3

        # Check individual items
        item_ids = {"item1", "item2", "item3"}
        for child in collection_node['children']:
            self.assertIn('node_id', child)
            self.assertIn('merkle:object_hash', child)
            self.assertIn(child['node_id'], item_ids)

    def test_process_collection_with_sub_collections_and_items_in_folders(self):
        """
        Test processing a collection with sub-collections and items nested in their own folders.
        """
        collection_id = "collection_with_subcollections"
        items = [
            {
                "type": "Feature",
                "id": "item1",
                "properties": {
                    "datetime": "2024-10-18T12:00:00Z",
                    "other_property": "value1"
                },
                "geometry": {},
                "links": []
            }
        ]
        sub_collections = [
            {
                "id": "sub_collection1",
                "items": [
                    {
                        "type": "Feature",
                        "id": "item2",
                        "properties": {
                            "datetime": "2024-10-19T12:00:00Z",
                            "other_property": "value2"
                        },
                        "geometry": {},
                        "links": []
                    }
                ],
                "sub_collections": [
                    {
                        "id": "sub_sub_collection1",
                        "items": [
                            {
                                "type": "Feature",
                                "id": "item3",
                                "properties": {
                                    "datetime": "2024-10-20T12:00:00Z",
                                    "other_property": "value3"
                                },
                                "geometry": {},
                                "links": []
                            }
                        ]
                    }
                ]
            }
        ]
        self.create_collection(
            collection_id,
            items=items,
            sub_collections=sub_collections
        )

        collection_json_path = self.collections_dir / collection_id / "collection.json"

        # Define the hash_method
        hash_method = {
            "function": "sha256",
            "fields": ["*"],
            "ordering": "ascending",
            "description": "Test hash method."
        }

        # Process the collection via process_collection only
        collection_node = process_collection(collection_json_path, hash_method)

        # Assertions
        self.assertIsNotNone(collection_node)
        self.assertIn('node_id', collection_node)
        self.assertIn('merkle:object_hash', collection_node)
        self.assertIn('merkle:root', collection_node)
        self.assertIn('children', collection_node)

        self.assertEqual(collection_node['node_id'], collection_id)
        self.assertTrue(collection_node['merkle:object_hash'])
        self.assertTrue(collection_node['merkle:root'])
        self.assertEqual(len(collection_node['children']), 2)  # item1 and sub_collection1

        # Check individual children
        child_ids = {child['node_id'] for child in collection_node['children']}
        self.assertIn('item1', child_ids)
        self.assertIn('sub_collection1', child_ids)

        # Further checks to ensure sub_collection1 has its children
        sub_collection_node = next((child for child in collection_node['children'] if child['node_id'] == 'sub_collection1'), None)
        self.assertIsNotNone(sub_collection_node)
        self.assertIn('children', sub_collection_node)
        self.assertEqual(len(sub_collection_node['children']), 2)  # item2 and sub_sub_collection1

        # Check sub_sub_collection1
        sub_sub_collection_node = next((child for child in sub_collection_node['children'] if child['node_id'] == 'sub_sub_collection1'), None)
        self.assertIsNotNone(sub_sub_collection_node)
        self.assertIn('children', sub_sub_collection_node)
        self.assertEqual(len(sub_sub_collection_node['children']), 1)  # item3

        # Check item2
        item2_node = next((child for child in sub_collection_node['children'] if child['node_id'] == 'item2'), None)
        self.assertIsNotNone(item2_node)
        self.assertIn('merkle:object_hash', item2_node)

        # Check item3
        item3_node = next((child for child in sub_sub_collection_node['children'] if child['node_id'] == 'item3'), None)
        self.assertIsNotNone(item3_node)
        self.assertIn('merkle:object_hash', item3_node)


class TestIsItemDirectory(unittest.TestCase):
    def setUp(self):
        """
        Set up a temporary directory for testing item directories.
        """
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """
        Clean up the temporary directory after tests.
        """
        shutil.rmtree(self.temp_dir)

    def test_is_item_directory_true(self):
        """
        Test that is_item_directory returns True for directories containing a single Feature JSON file.
        """
        item_dir = Path(self.temp_dir) / "itema"
        item_dir.mkdir()
        item_json = {
            "type": "Feature",
            "id": "itema",
            "properties": {},
            "geometry": {},
            "links": []
        }
        item_path = item_dir / "itema.json"
        with item_path.open('w', encoding='utf-8') as f:
            json.dump(item_json, f, indent=2)
        
        self.assertTrue(is_item_directory(item_dir))

    def test_is_item_directory_false_multiple_files(self):
        """
        Test that is_item_directory returns False for directories containing multiple JSON files.
        """
        item_dir = Path(self.temp_dir) / "itemb"
        item_dir.mkdir()
        item_json1 = {
            "type": "Feature",
            "id": "itemb1",
            "properties": {},
            "geometry": {},
            "links": []
        }
        item_json2 = {
            "type": "Feature",
            "id": "itemb2",
            "properties": {},
            "geometry": {},
            "links": []
        }
        item_path1 = item_dir / "itemb1.json"
        item_path2 = item_dir / "itemb2.json"
        with item_path1.open('w', encoding='utf-8') as f:
            json.dump(item_json1, f, indent=2)
        with item_path2.open('w', encoding='utf-8') as f:
            json.dump(item_json2, f, indent=2)
        
        self.assertFalse(is_item_directory(item_dir))

    def test_is_item_directory_false_non_feature(self):
        """
        Test that is_item_directory returns False for directories containing a single non-Feature JSON file.
        """
        item_dir = Path(self.temp_dir) / "itemc"
        item_dir.mkdir()
        non_feature_json = {
            "type": "Collection",
            "id": "itemc",
            "description": "A non-Feature type"
        }
        item_path = item_dir / "itemc.json"
        with item_path.open('w', encoding='utf-8') as f:
            json.dump(non_feature_json, f, indent=2)
        
        self.assertFalse(is_item_directory(item_dir))

    def test_is_item_directory_false_no_json_files(self):
        """
        Test that is_item_directory returns False for directories with no JSON files.
        """
        item_dir = Path(self.temp_dir) / "itemd"
        item_dir.mkdir()
        # No JSON files created
        self.assertFalse(is_item_directory(item_dir))


class TestProcessCatalog(unittest.TestCase):
    def setUp(self):
        """
        Set up a temporary directory for testing catalogs.
        """
        self.temp_dir = tempfile.mkdtemp()
        self.catalog_dir = Path(self.temp_dir) / "root_catalog"
        self.catalog_dir.mkdir()
        self.collections_dir = self.catalog_dir / "collections"
        self.collections_dir.mkdir()

    def tearDown(self):
        """
        Clean up the temporary directory after tests.
        """
        shutil.rmtree(self.temp_dir)

    def create_collection(
        self,
        collection_id: str,
        items: List[Dict[str, Any]],
        sub_collections: Optional[List[Dict[str, Any]]] = None,
        sub_catalogs: Optional[List[Dict[str, Any]]] = None,
        nested_items: Optional[List[Dict[str, Any]]] = None,
        parent_dir: Optional[Path] = None  # New parameter
    ):
        """
        Helper function to create a collection with items, sub-collections, and sub-catalogs.

        Parameters:
        - collection_id (str): The ID of the collection to create.
        - items (List[Dict[str, Any]]): List of item dictionaries to include in the collection.
        - sub_collections (Optional[List[Dict[str, Any]]]): List of sub-collection dictionaries.
        - sub_catalogs (Optional[List[Dict[str, Any]]]): List of sub-catalog dictionaries.
        - nested_items (Optional[List[Dict[str, Any]]]): List of items directly within the collection directory.
        - parent_dir (Optional[Path]): The directory under which to create this collection. Defaults to self.collections_dir.
        """
        if parent_dir is None:
            parent_dir = self.collections_dir
        collection_dir = parent_dir / collection_id
        collection_dir.mkdir(parents=True, exist_ok=True)

        collection_json = {
            "type": "Collection",
            "id": collection_id,
            "description": f"Description for {collection_id}",
            "extent": {},
            "links": []
        }

        # Optionally add merkle:hash_method
        hash_method = {
            "function": "sha256",
            "fields": ["*"],
            "ordering": "ascending"
        }
        collection_json["merkle:hash_method"] = hash_method

        # Save collection.json
        collection_json_path = collection_dir / "collection.json"
        with collection_json_path.open('w', encoding='utf-8') as f:
            json.dump(collection_json, f, indent=2)

        # Create items
        for item in items:
            item_dir = collection_dir / item["id"]
            item_dir.mkdir(parents=True, exist_ok=True)
            item_path = item_dir / f"{item['id']}.json"
            with item_path.open('w', encoding='utf-8') as f:
                json.dump(item, f, indent=2)

        # Create sub-collections
        if sub_collections:
            for sub_col in sub_collections:
                sub_col_id = sub_col["id"]
                # Create 'collections' subdirectory within the current collection
                sub_collections_dir = collection_dir / "collections"
                sub_collections_dir.mkdir(exist_ok=True)
                # Recursively create sub-collections under the 'collections' subdirectory
                self.create_collection(
                    sub_col_id,
                    sub_col.get("items", []),
                    sub_col.get("sub_collections"),
                    sub_col.get("sub_catalogs"),
                    sub_col.get("nested_items"),
                    parent_dir=sub_collections_dir  # Pass the 'collections' subdirectory
                )

        # Create sub-catalogs
        if sub_catalogs:
            for sub_cat in sub_catalogs:
                sub_cat_id = sub_cat["id"]
                sub_cat_dir = collection_dir / sub_cat_id
                sub_cat_dir.mkdir(parents=True, exist_ok=True)
                sub_cat_json = {
                    "type": "Catalog",
                    "id": sub_cat_id,
                    "description": f"Description for {sub_cat_id}",
                    "links": []
                }
                # Optionally add merkle:hash_method
                sub_cat_json["merkle:hash_method"] = hash_method
                sub_cat_json_path = sub_cat_dir / "catalog.json"
                with sub_cat_json_path.open('w', encoding='utf-8') as f:
                    json.dump(sub_cat_json, f, indent=2)

                # Create collections within sub-catalogs
                for sub_cat_collection in sub_cat.get("collections", []):
                    self.create_collection(
                        sub_cat_collection["id"],
                        sub_cat_collection.get("items", []),
                        sub_cat_collection.get("sub_collections"),
                        sub_cat_collection.get("sub_catalogs"),
                        sub_cat_collection.get("nested_items"),
                        parent_dir=sub_cat_dir / "collections"  # Pass the 'collections' subdirectory
                    )

        # Create nested items if any (items directly within the collection directory)
        if nested_items:
            for item in nested_items:
                item_path = collection_dir / f"{item['id']}.json"
                with item_path.open('w', encoding='utf-8') as f:
                    json.dump(item, f, indent=2)

    def test_process_catalog_simple(self):
        """
        Test processing a simple catalog with a single collection and items.
        """
        # Create collection and items
        collection_id = "collection1"
        collection_dir = self.collections_dir / collection_id
        collection_dir.mkdir()
        collection_json = {
            "type": "Collection",
            "id": collection_id,
            "description": "A simple collection",
            "extent": {},
            "links": []
        }
        hash_method = {
            "function": "sha256",
            "fields": ["*"],
            "ordering": "ascending"
        }
        collection_json["merkle:hash_method"] = hash_method

        collection_json_path = collection_dir / "collection.json"
        with collection_json_path.open('w', encoding='utf-8') as f:
            json.dump(collection_json, f, indent=2)

        # Create items
        item1 = {
            "type": "Feature",
            "id": "item1",
            "properties": {
                "datetime": "2024-10-23T12:00:00Z",
                "other_property": "value1"
            },
            "geometry": {},
            "links": []
        }
        item2 = {
            "type": "Feature",
            "id": "item2",
            "properties": {
                "datetime": "2024-10-24T12:00:00Z",
                "other_property": "value2"
            },
            "geometry": {},
            "links": []
        }
        item1_dir = collection_dir / "item1"
        item1_dir.mkdir()
        item1_path = item1_dir / "item1.json"
        with item1_path.open('w', encoding='utf-8') as f:
            json.dump(item1, f, indent=2)

        item2_dir = collection_dir / "item2"
        item2_dir.mkdir()
        item2_path = item2_dir / "item2.json"
        with item2_path.open('w', encoding='utf-8') as f:
            json.dump(item2, f, indent=2)

        # Create catalog.json
        catalog_json = {
            "type": "Catalog",
            "id": "root_catalog",
            "description": "Root Catalog",
            "links": []
        }
        catalog_json["merkle:hash_method"] = hash_method
        catalog_json_path = self.catalog_dir / "catalog.json"
        with catalog_json_path.open('w', encoding='utf-8') as f:
            json.dump(catalog_json, f, indent=2)

        # Process the catalog instead of processing the collection directly
        merkle_tree = process_catalog(catalog_json_path, hash_method)

        # Assertions
        self.assertIsNotNone(merkle_tree)
        self.assertIn('node_id', merkle_tree)
        self.assertIn('merkle:object_hash', merkle_tree)
        self.assertIn('merkle:root', merkle_tree)
        self.assertIn('children', merkle_tree)
        self.assertEqual(merkle_tree['node_id'], 'root_catalog')
        self.assertTrue(merkle_tree['merkle:object_hash'])
        self.assertTrue(merkle_tree['merkle:root'])
        self.assertEqual(len(merkle_tree['children']), 1)  # Only collection1

        # Check children (collections)
        collection_node = merkle_tree['children'][0]
        self.assertEqual(collection_node['node_id'], 'collection1')
        self.assertIn('merkle:object_hash', collection_node)
        self.assertIn('merkle:root', collection_node)
        self.assertIn('children', collection_node)
        self.assertEqual(len(collection_node['children']), 2)  # item1 and item2

        # Check items
        item_node1 = collection_node['children'][0]
        self.assertEqual(item_node1['node_id'], 'item1')
        self.assertIn('merkle:object_hash', item_node1)

        item_node2 = collection_node['children'][1]
        self.assertEqual(item_node2['node_id'], 'item2')
        self.assertIn('merkle:object_hash', item_node2)


if __name__ == '__main__':
    unittest.main()
