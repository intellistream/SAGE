import unittest
import numpy as np
import faiss
import os
from unittest.mock import patch
from sage.core.neuromem.search_engine.vdb_backend.faiss_backend import FaissBackend  # Replace with actual module name

class TestFaissBackend(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.dim = 4
        self.index_name = "test_index"
        self.vectors = [
            np.array([1.0, 0.0, 0.0, 0.0]),
            np.array([0.0, 1.0, 0.0, 0.0]),
            np.array([0.0, 0.0, 1.0, 0.0])
        ]
        self.ids = ["id1", "id2", "id3"]
        self.faiss_backend = FaissBackend(name=self.index_name, dim=self.dim)

    def test_initialization(self):
        """Test initialization with and without vectors/ids."""
        # Test basic initialization
        self.assertEqual(self.faiss_backend.index_name, self.index_name)
        self.assertEqual(self.faiss_backend.dim, self.dim)
        self.assertIsInstance(self.faiss_backend.index, faiss.IndexIDMap)
        self.assertEqual(self.faiss_backend.next_id, 1)
        self.assertEqual(len(self.faiss_backend.id_map), 0)
        self.assertEqual(len(self.faiss_backend.rev_map), 0)
        self.assertEqual(len(self.faiss_backend.tombstones), 0)

        # Test initialization with vectors and ids
        backend = FaissBackend(name=self.index_name, dim=self.dim, vectors=self.vectors, ids=self.ids)
        self.assertEqual(len(backend.id_map), 3)
        self.assertEqual(len(backend.rev_map), 3)
        self.assertEqual(backend.next_id, 4)
        self.assertEqual(backend.id_map[1], "id1")
        self.assertEqual(backend.rev_map["id2"], 2)

    def test_insert(self):
        """Test inserting a single vector and ID."""
        new_vector = np.array([0.0, 0.0, 0.0, 1.0])
        new_id = "id4"
        self.faiss_backend.insert(new_vector, new_id)
        self.assertEqual(self.faiss_backend.id_map[1], "id4")
        self.assertEqual(self.faiss_backend.rev_map["id4"], 1)
        self.assertEqual(self.faiss_backend.next_id, 2)
        self.assertEqual(self.faiss_backend.index.ntotal, 1)

        # Test inserting existing ID (should update)
        updated_vector = np.array([0.0, 0.0, 1.0, 1.0])
        self.faiss_backend.insert(updated_vector, new_id)
        self.assertEqual(self.faiss_backend.id_map[1], "id4")
        self.assertEqual(self.faiss_backend.index.ntotal, 1)  # Should replace, not add

    def test_batch_insert(self):
        """Test batch insertion of vectors and IDs."""
        self.faiss_backend.batch_insert(self.vectors, self.ids)
        self.assertEqual(self.faiss_backend.index.ntotal, 3)
        self.assertEqual(len(self.faiss_backend.id_map), 3)
        self.assertEqual(len(self.faiss_backend.rev_map), 3)
        self.assertEqual(self.faiss_backend.next_id, 4)
        self.assertEqual(self.faiss_backend.id_map[1], "id1")
        self.assertEqual(self.faiss_backend.rev_map["id3"], 3)

        # Test batch insert with duplicate IDs
        new_vectors = [np.array([0.0, 0.0, 0.0, 1.0])]
        new_ids = ["id1"]  # Duplicate ID
        self.faiss_backend.batch_insert(new_vectors, new_ids)
        self.assertEqual(self.faiss_backend.index.ntotal, 3)  # Should update, not add new

    def test_search(self):
        """Test vector search functionality."""
        self.faiss_backend.batch_insert(self.vectors, self.ids)
        query_vector = np.array([1.0, 0.0, 0.0, 0.0])  # Close to id1
        top_k = 2
        string_ids, distances = self.faiss_backend.search(query_vector, top_k)
        self.assertEqual(len(string_ids), 2)
        self.assertEqual(len(distances), 2)
        self.assertEqual(string_ids[0], "id1")  # Closest match
        self.assertAlmostEqual(distances[0], 0.0)  # Exact match
        self.assertIn(string_ids[1], ["id2", "id3"])  # Second closest
        self.assertAlmostEqual(distances[1], 2.0, places=5)  # Distance should be sqrt(2)^2 = 2

    def test_delete(self):
        """Test deletion functionality."""
        self.faiss_backend.batch_insert(self.vectors, self.ids)
        
        # Test deletion with tombstone (assuming IndexFlatL2 wrapped in IndexIDMap)
        self.faiss_backend.delete("id1")
        self.assertIn("id1", self.faiss_backend.tombstones)
        string_ids, _ = self.faiss_backend.search(np.array([1.0, 0.0, 0.0, 0.0]), 2)
        self.assertNotIn("id1", string_ids)

        # Test deletion with non-existent ID
        self.faiss_backend.delete("non_existent_id")
        self.assertNotIn("non_existent_id", self.faiss_backend.tombstones)

    def test_update(self):
        """Test updating a vector for an existing ID."""
        self.faiss_backend.batch_insert(self.vectors, self.ids)
        new_vector = np.array([0.0, 0.0, 0.0, 1.0])
        self.faiss_backend.update("id1", new_vector)
        string_ids, distances = self.faiss_backend.search(new_vector, 1)
        self.assertEqual(string_ids[0], "id1")
        self.assertAlmostEqual(distances[0], 0.0)

    @patch.dict(os.environ, {"FAISS_INDEX_TYPE": "IndexHNSWFlat"})
    def test_different_index_type(self):
        """Test initialization with a different index type (HNSW)."""
        backend = FaissBackend(name=self.index_name, dim=self.dim)
        self.assertIsInstance(backend.index, faiss.IndexIDMap)
        self.assertIsInstance(backend.index.index, faiss.IndexHNSWFlat)
        backend.batch_insert(self.vectors, self.ids)
        self.assertEqual(backend.index.ntotal, 3)

    def test_edge_cases(self):
        """Test edge cases like empty vectors, invalid dimensions."""
        # Test empty batch insert
        with self.assertRaises(AssertionError):
            self.faiss_backend.batch_insert([], ["id1"])

        # Test mismatched vectors and IDs
        with self.assertRaises(AssertionError):
            self.faiss_backend.batch_insert(self.vectors, ["id1", "id2"])

        # Test invalid vector dimension
        invalid_vector = np.array([1.0, 0.0])  # Wrong dimension
        with self.assertRaises(ValueError):
            self.faiss_backend.insert(invalid_vector, "id5")

if __name__ == "__main__":
    unittest.main()