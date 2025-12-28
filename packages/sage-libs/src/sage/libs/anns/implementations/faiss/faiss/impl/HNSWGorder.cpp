//add by ghr

#include <faiss/impl/HNSWGorder.h>

#include <queue>

#include <faiss/impl/FaissAssert.h>
#include <faiss/impl/HNSW.h>

namespace faiss {
namespace {

struct GorderQueue {
    struct Entry {
        int priority;
        idx_t node;
    };

    struct Compare {
        bool operator()(const Entry& a, const Entry& b) const {
            if (a.priority == b.priority) {
                return a.node > b.node;
            }
            return a.priority < b.priority;
        }
    };

    explicit GorderQueue(size_t n)
            : priorities(n, 0), removed(n, false), heap(Compare()) {
        for (idx_t i = 0; i < n; i++) {
            heap.emplace(Entry{0, i});
        }
    }

    void increment(idx_t node) {
        adjust(node, 1);
    }

    void decrement(idx_t node) {
        adjust(node, -1);
    }

    idx_t pop() {
        while (!heap.empty()) {
            Entry top = heap.top();
            heap.pop();
            if (removed[top.node]) {
                continue;
            }
            if (top.priority != priorities[top.node]) {
                continue;
            }
            removed[top.node] = true;
            return top.node;
        }
        FAISS_THROW_MSG("Gorder priority queue underflow");
    }

  private:
    void adjust(idx_t node, int delta) {
        if (removed[node]) {
            return;
        }
        priorities[node] += delta;
        heap.emplace(Entry{priorities[node], node});
    }

    std::vector<int> priorities;
    std::vector<bool> removed;
    std::priority_queue<Entry, std::vector<Entry>, Compare> heap;
};

} // namespace

std::vector<idx_t> compute_hnsw_gorder_old_to_new(
        const HNSW& graph,
        int window) {
    size_t n = graph.levels.size();
    std::vector<idx_t> pinv;
    if (n == 0) {
        return pinv;
    }
    if (window < 0) {
        window = 0;
    }

    std::vector<std::vector<HNSW::storage_idx_t>> out_edges(n);
    std::vector<std::vector<HNSW::storage_idx_t>> in_edges(n);

    for (idx_t node = 0; node < (idx_t)n; node++) {
        size_t begin = 0, end = 0;
        graph.neighbor_range(node, 0, &begin, &end);
        for (size_t idx = begin; idx < end; idx++) {
            HNSW::storage_idx_t dst = graph.neighbors[idx];
            if (dst < 0) {
                break;
            }
            out_edges[node].push_back(dst);
            in_edges[dst].push_back(node);
        }
    }

    GorderQueue queue(n);
    std::vector<idx_t> order(n, 0);

    idx_t seed = graph.entry_point >= 0 ? graph.entry_point : 0;
    queue.increment(seed);
    order[0] = queue.pop();

    for (size_t i = 1; i < n; i++) {
        idx_t v_e = order[i - 1];
        for (HNSW::storage_idx_t u : out_edges[v_e]) {
            queue.increment(u);
        }
        for (HNSW::storage_idx_t u : in_edges[v_e]) {
            queue.increment(u);
            for (HNSW::storage_idx_t v : out_edges[u]) {
                queue.increment(v);
            }
        }

        if (i > (size_t)(window + 1)) {
            idx_t v_b = order[i - window - 1];
            for (HNSW::storage_idx_t u : out_edges[v_b]) {
                queue.decrement(u);
            }
            for (HNSW::storage_idx_t u : in_edges[v_b]) {
                queue.decrement(u);
                for (HNSW::storage_idx_t v : out_edges[u]) {
                    queue.decrement(v);
                }
            }
        }
        order[i] = queue.pop();
    }

    pinv.resize(n);
    for (size_t i = 0; i < n; i++) {
        pinv[order[i]] = i;
    }
    return pinv;
}

} // namespace faiss
