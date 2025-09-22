#include "ring_buffer_compat.h"
#include "simple_boost_queue.h"
#include <cstring>
#include <unordered_map>
#include <string>
#include <memory>
#include <unistd.h>
#include <boost/interprocess/shared_memory_object.hpp>

// 全局队列映射（用于兼容性）
static std::unordered_map<std::string, std::shared_ptr<SimpleBoostQueue>> g_queue_map;

// 兼容性函数实现
extern "C" {
    
RingBuffer* ring_buffer_create(size_t capacity) {
    // 创建一个匿名队列
    static int anonymous_counter = 0;
    std::string name = "anonymous_" + std::to_string(anonymous_counter++);
    return ring_buffer_create_named(name.c_str(), static_cast<uint32_t>(capacity));
}

RingBuffer* ring_buffer_create_named(const char* name, uint32_t size) {
    try {
        auto rb = new SimpleBoostQueue(std::string(name), size);
        return reinterpret_cast<RingBuffer*>(rb);
    } catch (const std::exception& e) {
        return nullptr;
    }
}

RingBuffer* ring_buffer_open(const char* name) {
    try {
        auto rb = new SimpleBoostQueue(std::string(name), 0); // size ignored for open
        return reinterpret_cast<RingBuffer*>(rb);
    } catch (const std::exception& e) {
        return nullptr;
    }
}

void ring_buffer_destroy(RingBuffer* rb) {
    if (rb) {
        delete reinterpret_cast<SimpleBoostQueue*>(rb);
    }
}

void ring_buffer_destroy_by_name(const char* name) {
    // 清理共享内存段
    try {
        std::string shm_name = "sage_queue_" + std::string(name);
        boost::interprocess::shared_memory_object::remove(shm_name.c_str());
    } catch (...) {
        // 忽略错误
    }
}

void ring_buffer_close(RingBuffer* rb) {
    if (rb) {
        reinterpret_cast<SimpleBoostQueue*>(rb)->close();
    }
}

int ring_buffer_put(RingBuffer* rb, const void* data, size_t size) {
    if (!rb) return -1;
    return reinterpret_cast<SimpleBoostQueue*>(rb)->put(data, static_cast<uint32_t>(size), -1) ? size : -1;
}

int ring_buffer_put_timeout(RingBuffer* rb, const void* data, uint32_t size, double timeout_sec) {
    if (!rb) return -1;
    return reinterpret_cast<SimpleBoostQueue*>(rb)->put(data, size, timeout_sec) ? size : -1;
}

int ring_buffer_get(RingBuffer* rb, void* data, size_t* size) {
    if (!rb || !size) return -1;
    uint32_t buffer_size = static_cast<uint32_t>(*size);
    bool success = reinterpret_cast<SimpleBoostQueue*>(rb)->get(data, &buffer_size, -1);
    *size = buffer_size;
    return success ? buffer_size : -1;
}

int ring_buffer_get_timeout(RingBuffer* rb, void* buffer, uint32_t buffer_size, double timeout_sec) {
    if (!rb) return -1;
    uint32_t actual_size = buffer_size;
    return reinterpret_cast<SimpleBoostQueue*>(rb)->get(buffer, &actual_size, timeout_sec) ? actual_size : -1;
}

int ring_buffer_try_get(RingBuffer* rb, void* data, size_t* size) {
    if (!rb || !size) return -1;
    uint32_t buffer_size = static_cast<uint32_t>(*size);
    bool success = reinterpret_cast<SimpleBoostQueue*>(rb)->get(data, &buffer_size, 0.0); // 0 timeout
    *size = buffer_size;
    return success ? buffer_size : -1;
}

// 兼容性读写函数
int ring_buffer_write(RingBuffer* rb, const void* data, uint32_t size) {
    return ring_buffer_put_timeout(rb, data, size, -1);
}

int ring_buffer_read(RingBuffer* rb, void* data, uint32_t size) {
    return ring_buffer_get_timeout(rb, data, size, -1);
}

int ring_buffer_peek(RingBuffer* rb, void* data, uint32_t size) {
    if (!rb) return -1;
    uint32_t actual_size = size;
    return reinterpret_cast<SimpleBoostQueue*>(rb)->peek(data, &actual_size) ? actual_size : -1;
}

// 状态查询
size_t ring_buffer_size(RingBuffer* rb) {
    return rb ? reinterpret_cast<SimpleBoostQueue*>(rb)->size() : 0;
}

uint32_t ring_buffer_capacity(RingBuffer* rb) {
    return rb ? reinterpret_cast<SimpleBoostQueue*>(rb)->size() : 0;
}

int ring_buffer_empty(RingBuffer* rb) {
    return rb ? reinterpret_cast<SimpleBoostQueue*>(rb)->is_empty() : 1;
}

bool ring_buffer_is_empty(RingBuffer* rb) {
    return rb ? reinterpret_cast<SimpleBoostQueue*>(rb)->is_empty() : true;
}

bool ring_buffer_is_full(RingBuffer* rb) {
    return rb ? reinterpret_cast<SimpleBoostQueue*>(rb)->is_full() : true;
}

uint32_t ring_buffer_available_read(RingBuffer* rb) {
    return rb ? reinterpret_cast<SimpleBoostQueue*>(rb)->available_read() : 0;
}

uint32_t ring_buffer_available_write(RingBuffer* rb) {
    return rb ? reinterpret_cast<SimpleBoostQueue*>(rb)->available_write() : 0;
}

void ring_buffer_clear(RingBuffer* rb) {
    if (!rb) return;
    
    // 清空队列（通过读取所有消息）
    char dummy_buffer[1024];
    uint32_t dummy_size = sizeof(dummy_buffer);
    
    while (!reinterpret_cast<SimpleBoostQueue*>(rb)->is_empty()) {
        dummy_size = sizeof(dummy_buffer);
        if (!reinterpret_cast<SimpleBoostQueue*>(rb)->get(dummy_buffer, &dummy_size, 0.001)) {
            break; // 超时或出错
        }
    }
}

// 引用管理（简化实现）
RingBufferRef* ring_buffer_get_ref(RingBuffer* rb) {
    if (!rb) return nullptr;
    
    RingBufferRef* ref = new RingBufferRef();
    strncpy(ref->name, "boost_queue", sizeof(ref->name) - 1);
    ref->size = reinterpret_cast<SimpleBoostQueue*>(rb)->size();
    ref->auto_cleanup = true;
    ref->creator_pid = getpid();
    
    return ref;
}

RingBuffer* ring_buffer_from_ref(RingBufferRef* ref) {
    if (!ref) return nullptr;
    return ring_buffer_open(ref->name);
}

void ring_buffer_release_ref(RingBufferRef* ref) {
    if (ref) {
        delete ref;
    }
}

} // extern "C"
