#include "ring_buffer.h"
#include "concurrentqueue.h"
#include <cstring>
#include <memory>

struct RingBuffer {
    moodycamel::ConcurrentQueue<std::vector<uint8_t>> queue;
    size_t capacity;
    std::atomic<size_t> current_size{0};
};

extern "C" {

RingBuffer* ring_buffer_create(size_t capacity) {
    return new RingBuffer{moodycamel::ConcurrentQueue<std::vector<uint8_t>>(), capacity, 0};
}

void ring_buffer_destroy(RingBuffer* rb) {
    if (rb) {
        delete rb;
    }
}

int ring_buffer_put(RingBuffer* rb, const void* data, size_t size) {
    if (!rb || !data || size == 0) return -1;

    if (rb->current_size.load() >= rb->capacity) {
        return -1; // 队列满
    }

    std::vector<uint8_t> item(static_cast<const uint8_t*>(data),
                              static_cast<const uint8_t*>(data) + size);

    if (rb->queue.enqueue(std::move(item))) {
        rb->current_size.fetch_add(1);
        return 0;
    }
    return -1;
}

int ring_buffer_get(RingBuffer* rb, void* data, size_t* size) {
    if (!rb || !data || !size) return -1;

    std::vector<uint8_t> item;
    if (rb->queue.wait_dequeue(item)) {  // 阻塞等待
        if (*size >= item.size()) {
            std::memcpy(data, item.data(), item.size());
            *size = item.size();
            rb->current_size.fetch_sub(1);
            return 0;
        }
        // 数据太大，重新放回队列
        rb->queue.enqueue(std::move(item));
        return -2; // 缓冲区太小
    }
    return -1;
}

int ring_buffer_try_get(RingBuffer* rb, void* data, size_t* size) {
    if (!rb || !data || !size) return -1;

    std::vector<uint8_t> item;
    if (rb->queue.try_dequeue(item)) {  // 非阻塞
        if (*size >= item.size()) {
            std::memcpy(data, item.data(), item.size());
            *size = item.size();
            rb->current_size.fetch_sub(1);
            return 0;
        }
        rb->queue.enqueue(std::move(item));
        return -2;
    }
    return -1; // 队列空
}

size_t ring_buffer_size(RingBuffer* rb) {
    return rb ? rb->current_size.load() : 0;
}

int ring_buffer_empty(RingBuffer* rb) {
    return rb ? (rb->current_size.load() == 0 ? 1 : 0) : 1;
}

void ring_buffer_clear(RingBuffer* rb) {
    if (!rb) return;

    std::vector<uint8_t> dummy;
    while (rb->queue.try_dequeue(dummy)) {
        rb->current_size.fetch_sub(1);
    }
}

} // extern "C"