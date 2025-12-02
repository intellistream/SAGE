import time

import numpy as np
from plsh_python import Index


def create_random_dense_vector(dimensions: int) -> np.ndarray:
    return np.random.uniform(-1.0, 1.0, size=dimensions).astype(np.float32)


def create_random_sparse_vector(dimensions: int, sparsity: float = 0.9) -> np.ndarray:
    sparse_vec = np.zeros(dimensions, dtype=np.float32)
    num_non_zero_elements = int(dimensions * (1 - sparsity))
    non_zero_indices = np.random.choice(dimensions, num_non_zero_elements, replace=False)
    sparse_vec[non_zero_indices] = np.random.uniform(-1.0, 1.0, size=num_non_zero_elements)
    return sparse_vec


def normalize(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def calculate_l2_distance(v1: np.ndarray, v2: np.ndarray) -> float:
    return np.linalg.norm(v1 - v2)


def find_ground_truth_dense_topk(
    query_point: np.ndarray,
    all_data: np.ndarray,
    radius: float,
    topk: int,
    query_id_to_exclude: int,
):
    results = []
    for i, vec in enumerate(all_data):
        if i == query_id_to_exclude:
            continue
        dist = calculate_l2_distance(query_point, vec)
        if dist <= radius:
            results.append((i, dist))

    results.sort(key=lambda x: x[1])

    return results[:topk]


def main():
    print("\n--- PLSH Python Demo (Dense or Sparse vectors, fixed) ---")

    dimensions = 32
    k = 8
    m = 60
    num_threads = 4

    initial_points = 20000
    streaming_points = 80000
    total_points = initial_points + streaming_points
    merge_threshold = 20000

    data_type = input("(dense/sparse): ").strip().lower()

    print("\n[CONFIG]")
    print(f"  - Dimensions: {dimensions}, k={k}, m={m}")
    print(
        f"  - Data Size: {initial_points} (initial) + {streaming_points} (streaming) = {total_points}"
    )

    print("\n[PHASE 1: Generating Data]")
    if data_type == "dense":
        all_data = np.array(
            [normalize(create_random_dense_vector(dimensions)) for _ in range(total_points)]
        )
    elif data_type == "sparse":
        all_data = np.array(
            [normalize(create_random_sparse_vector(dimensions)) for _ in range(total_points)]
        )
    else:
        print("error: invalid data type. Choose 'dense' or 'sparse'.")
        return

    print(f"  - Generated {total_points} normalized {data_type} vectors.")

    print("\n[PHASE 2: Initial Index Build]")
    index = Index(dimensions=dimensions, k=k, m=m, num_threads=num_threads)
    init_ids = list(range(initial_points))
    index.build(all_data[:initial_points], initial_points, init_ids)
    print(f"  - Built index with {initial_points} points.")

    print("\n[PHASE 3: Streaming Inserts & Periodic Merging]")
    start_time = time.time()
    insert_count_since_merge = 0

    for i in range(streaming_points):
        idx = initial_points + i
        vec = all_data[idx : idx + 1]  # shape (1, dim)
        index.insert(vec, [idx])
        insert_count_since_merge += 1

        if insert_count_since_merge >= merge_threshold:
            print(f"  -> Reached {merge_threshold} inserts. Triggering merge...")
            index.merge_delta_to_static()
            insert_count_since_merge = 0

    if insert_count_since_merge > 0:
        print("  -> Final merge for remaining inserts...")
        index.merge_delta_to_static()

    elapsed = time.time() - start_time
    qps = streaming_points / elapsed if streaming_points > 0 else 0
    print(
        f"  - Inserted + merged {streaming_points} streaming points in {elapsed:.2f} s ({qps:.2f} ops/sec)"
    )

    print("\n[PHASE 4: Query Performance Test]")
    num_queries = 200
    topk = 10
    query_start = time.time()
    for i in range(num_queries):
        qvec = all_data[i]
        ids, dists = index.query_topk(qvec, k=topk)
        _ = (ids, dists)
    query_end = time.time()
    query_duration = query_end - query_start
    query_qps = num_queries / query_duration
    avg_latency = (query_duration * 1000) / num_queries
    print(f"  - Query QPS: {query_qps:.2f} ops/sec")
    print(f"  - Avg Latency: {avg_latency:.2f} ms/query")

    print("\n[PHASE 5: Recall Verification]")
    query_idx = 0
    query_vec = all_data[query_idx]
    radius = 1.2
    topk = 1000

    ids, dists = index.query_topk(query_vec, k=topk)
    lsh_ids = [i - 1 for i in ids]
    lsh_results = list(zip(lsh_ids, dists))

    ground_truth = find_ground_truth_dense_topk(query_vec, all_data, radius, topk, query_idx)

    gt_ids = set(i for i, _ in ground_truth)
    true_positives = sum(1 for i, _ in lsh_results if i in gt_ids)
    recall = true_positives / len(ground_truth) if ground_truth else 1.0

    print(f"  - Ground Truth Neighbors: {len(ground_truth)}")
    print(f"  - LSH Found Neighbors: {len(lsh_results)}")
    print(f"  - Correctly Found: {true_positives}")
    print(f"  - Recall: {recall * 100:.2f}%")

    print("\n--- Demo Finished ---")


if __name__ == "__main__":
    main()
