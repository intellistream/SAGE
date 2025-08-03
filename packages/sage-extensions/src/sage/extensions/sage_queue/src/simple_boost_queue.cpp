#include "simple_boost_queue.h"
#include <iostream>
#include <chrono>
#include <cstring>
#include <unistd.h>
#include <boost/date_time/posix_time/posix_time.hpp>

using namespace boost::interprocess;
using namespace std::chrono;

// 构造函数
SimpleBoostQueue::SimpleBoostQueue(const std::string& queue_name, uint32_t size)
    : segment(nullptr), metadata(nullptr), queue(nullptr), name(queue_name),
      ref_count(1), total_bytes_written(0), total_bytes_read(0) {
    
    try {
        // 创建或打开共享内存段
        segment = new managed_shared_memory(open_or_create, queue_name.c_str(), 65536);
        
        // 创建队列元数据
        metadata = segment->find_or_construct<QueueMetadata>("metadata")(size);
        
        // 创建队列
        ShmStringAllocator alloc(segment->get_segment_manager());
        queue = segment->find_or_construct<ShmDeque>("queue")(alloc);
        
        std::cout << "SimpleBoostQueue initialized: " << queue_name 
                  << " with size limit: " << size << std::endl;
                  
    } catch (const std::exception& e) {
        std::cerr << "Error creating SimpleBoostQueue: " << e.what() << std::endl;
        if (segment) {
            delete segment;
            segment = nullptr;
        }
    }
}

// 析构函数
SimpleBoostQueue::~SimpleBoostQueue() {
    if (segment) {
        delete segment;
    }
}

// 超时转换辅助函数
boost::posix_time::ptime timeout_to_ptime(double timeout_sec) {
    if (timeout_sec < 0) {
        return boost::posix_time::pos_infin;  // 无限等待
    }
    auto now = boost::posix_time::microsec_clock::universal_time();
    auto duration = boost::posix_time::milliseconds(static_cast<long>(timeout_sec * 1000));
    return now + duration;
}

// 添加数据
bool SimpleBoostQueue::put(const void* data, uint32_t data_size, double timeout_sec) {
    if (!segment || !metadata || !queue || metadata->closed) {
        return false;
    }
    
    scoped_lock<interprocess_mutex> lock(metadata->mutex);
    
    // 等待有空间可写
    auto timeout = timeout_to_ptime(timeout_sec);
    
    if (timeout_sec >= 0) {
        while (metadata->current_size >= metadata->max_size && !metadata->closed) {
            if (!metadata->not_full.timed_wait(lock, timeout)) {
                return false;  // 超时
            }
        }
    } else {
        while (metadata->current_size >= metadata->max_size && !metadata->closed) {
            metadata->not_full.wait(lock);
        }
    }
    
    if (metadata->closed) {
        return false;
    }
    
    try {
        // 创建字符串分配器
        CharAllocator char_alloc(segment->get_segment_manager());
        
        // 创建消息字符串
        ShmString message(char_alloc);
        message.assign(static_cast<const char*>(data), data_size);
        
        // 添加到队列
        queue->push_back(message);
        metadata->current_size++;
        
        // 更新统计信息
        total_bytes_written += data_size;
        
        // 通知等待的消费者
        metadata->not_empty.notify_one();
        
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Error in put: " << e.what() << std::endl;
        return false;
    }
}

// 获取数据
bool SimpleBoostQueue::get(void* buffer, uint32_t* buffer_size, double timeout_sec) {
    if (!segment || !metadata || !queue || !buffer || !buffer_size || metadata->closed) {
        return false;
    }
    
    scoped_lock<interprocess_mutex> lock(metadata->mutex);
    
    // 等待有数据可读
    auto timeout = timeout_to_ptime(timeout_sec);
    
    if (timeout_sec >= 0) {
        while (queue->empty() && !metadata->closed) {
            if (!metadata->not_empty.timed_wait(lock, timeout)) {
                return false;  // 超时
            }
        }
    } else {
        while (queue->empty() && !metadata->closed) {
            metadata->not_empty.wait(lock);
        }
    }
    
    if (metadata->closed || queue->empty()) {
        return false;
    }
    
    try {
        ShmString& message = queue->front();
        uint32_t message_size = message.size();
        
        if (*buffer_size < message_size) {
            *buffer_size = message_size;
            return false;
        }
        
        // 复制数据
        std::memcpy(buffer, message.c_str(), message_size);
        *buffer_size = message_size;
        
        // 从队列中移除
        queue->pop_front();
        metadata->current_size--;
        
        // 更新统计信息
        total_bytes_read += message_size;
        
        // 通知等待的生产者
        metadata->not_full.notify_one();
        
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Error in get: " << e.what() << std::endl;
        return false;
    }
}

// 窥视数据
bool SimpleBoostQueue::peek(void* buffer, uint32_t* buffer_size) {
    if (!segment || !metadata || !queue || !buffer || !buffer_size) {
        return false;
    }
    
    scoped_lock<interprocess_mutex> lock(metadata->mutex);
    
    if (queue->empty()) {
        return false;
    }
    
    try {
        ShmString& message = queue->front();
        uint32_t message_size = message.size();
        
        if (*buffer_size < message_size) {
            *buffer_size = message_size;
            return false;
        }
        
        std::memcpy(buffer, message.c_str(), message_size);
        *buffer_size = message_size;
        
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Error in peek: " << e.what() << std::endl;
        return false;
    }
}

// 其他方法实现
bool SimpleBoostQueue::is_empty() {
    if (!metadata || !queue) return true;
    scoped_lock<interprocess_mutex> lock(metadata->mutex);
    return queue->empty();
}

bool SimpleBoostQueue::is_full() {
    if (!metadata) return true;
    scoped_lock<interprocess_mutex> lock(metadata->mutex);
    return metadata->current_size >= metadata->max_size;
}

uint32_t SimpleBoostQueue::available_read() {
    if (!metadata) return 0;
    scoped_lock<interprocess_mutex> lock(metadata->mutex);
    return metadata->current_size;
}

uint32_t SimpleBoostQueue::available_write() {
    if (!metadata) return 0;
    scoped_lock<interprocess_mutex> lock(metadata->mutex);
    return metadata->max_size - metadata->current_size;
}

uint32_t SimpleBoostQueue::size_limit() {
    if (!metadata) return 0;
    return metadata->max_size;
}

void SimpleBoostQueue::close() {
    // 对于 Boost.Interprocess 实现，我们不设置 closed 标志
    // 因为共享内存应该在进程间保持持久性
    // 只是清理本地资源
    if (metadata) {
        // 通知任何等待的线程
        metadata->not_empty.notify_all();
        metadata->not_full.notify_all();
    }
}

RingBufferStats SimpleBoostQueue::get_stats() const {
    RingBufferStats stats = {0};
    
    if (!queue || !metadata) {
        return stats;
    }
    
    scoped_lock<interprocess_mutex> lock(metadata->mutex);
    
    stats.buffer_size = metadata->max_size;
    stats.available_read = metadata->current_size;
    stats.available_write = metadata->max_size - metadata->current_size;
    stats.readers = 0;  // Boost不跟踪读者数量
    stats.writers = 0;  // Boost不跟踪写者数量
    stats.ref_count = metadata->ref_count.load();
    stats.total_bytes_written = total_bytes_written;
    stats.total_bytes_read = total_bytes_read;
    
    // 计算利用率 (0-100)
    if (stats.buffer_size > 0) {
        stats.utilization = (stats.available_read * 100) / stats.buffer_size;
    }
    
    return stats;
}

// C 接口实现
extern "C" {
    RingBufferStruct* ring_buffer_create(uint32_t size) {
        // 创建匿名队列
        static int counter = 0;
        std::string name = "anonymous_" + std::to_string(counter++);
        return ring_buffer_create_named(name.c_str(), size);
    }
    
    RingBufferStruct* ring_buffer_create_named(const char* name, uint32_t size) {
        try {
            return new SimpleBoostQueue(std::string(name), size);
        } catch (const std::exception& e) {
            std::cerr << "Error creating named ring buffer: " << e.what() << std::endl;
            return nullptr;
        }
    }
    
    RingBufferStruct* ring_buffer_open(const char* name) {
        try {
            return new SimpleBoostQueue(std::string(name), 1024);  // 默认大小
        } catch (const std::exception& e) {
            std::cerr << "Error opening ring buffer: " << e.what() << std::endl;
            return nullptr;
        }
    }
    
    void ring_buffer_destroy(RingBufferStruct* rb) {
        if (rb) {
            delete static_cast<SimpleBoostQueue*>(rb);
        }
    }
    
    void ring_buffer_destroy_named(const char* name) {
        if (name) {
            try {
                shared_memory_object::remove(name);
            } catch (const std::exception& e) {
                std::cerr << "Error removing shared memory: " << e.what() << std::endl;
            }
        }
    }
    
    int ring_buffer_put(RingBufferStruct* rb, const void* data, uint32_t data_size, double timeout_sec) {
        return rb ? static_cast<SimpleBoostQueue*>(rb)->put(data, data_size, timeout_sec) : 0;
    }
    
    int ring_buffer_get(RingBufferStruct* rb, void* buffer, uint32_t* buffer_size, double timeout_sec) {
        return rb ? static_cast<SimpleBoostQueue*>(rb)->get(buffer, buffer_size, timeout_sec) : 0;
    }
    
    int ring_buffer_peek(RingBufferStruct* rb, void* buffer, uint32_t* buffer_size) {
        return rb ? static_cast<SimpleBoostQueue*>(rb)->peek(buffer, buffer_size) : 0;
    }
    
    // SageQueue 兼容接口
    int ring_buffer_write(RingBufferStruct* rb, const void* data, uint32_t data_size) {
        return rb ? static_cast<SimpleBoostQueue*>(rb)->put(data, data_size, -1) : 0;
    }
    
    int ring_buffer_read(RingBufferStruct* rb, void* buffer, uint32_t buffer_size) {
        if (!rb) return 0;
        uint32_t actual_size = buffer_size;
        bool success = static_cast<SimpleBoostQueue*>(rb)->get(buffer, &actual_size, -1);
        return success ? actual_size : 0;
    }
    
    int ring_buffer_is_empty(RingBufferStruct* rb) {
        return rb ? static_cast<SimpleBoostQueue*>(rb)->is_empty() : 1;
    }
    
    int ring_buffer_is_full(RingBufferStruct* rb) {
        return rb ? static_cast<SimpleBoostQueue*>(rb)->is_full() : 1;
    }
    
    uint32_t ring_buffer_available_read(RingBufferStruct* rb) {
        return rb ? static_cast<SimpleBoostQueue*>(rb)->available_read() : 0;
    }
    
    uint32_t ring_buffer_available_write(RingBufferStruct* rb) {
        return rb ? static_cast<SimpleBoostQueue*>(rb)->available_write() : 0;
    }
    
    uint32_t ring_buffer_size_limit(RingBufferStruct* rb) {
        return rb ? static_cast<SimpleBoostQueue*>(rb)->size_limit() : 0;
    }
    
    void ring_buffer_close(RingBufferStruct* rb) {
        if (rb) {
            static_cast<SimpleBoostQueue*>(rb)->close();
        }
    }
    
    // 引用管理
    RingBufferRef* ring_buffer_get_ref(RingBufferStruct* rb) {
        if (!rb) return nullptr;
        
        RingBufferRef* ref = new RingBufferRef();
        auto queue = static_cast<SimpleBoostQueue*>(rb);
        strncpy(ref->name, queue->name.c_str(), 63);
        ref->name[63] = '\0';
        ref->size = queue->size_limit();
        ref->auto_cleanup = 1;
        ref->creator_pid = getpid();
        
        return ref;
    }
    
    RingBufferStruct* ring_buffer_from_ref(RingBufferRef* ref) {
        if (!ref) return nullptr;
        return ring_buffer_open(ref->name);
    }
    
    void ring_buffer_release_ref(RingBufferRef* ref) {
        if (ref) {
            delete ref;
        }
    }
    
    int ring_buffer_inc_ref(RingBufferStruct* rb) {
        // Boost.Interprocess doesn't use reference counting like the original
        // implementation, so we'll just return 1 to indicate success
        return rb ? 1 : 0;
    }
    
    RingBufferStats ring_buffer_get_stats(RingBufferStruct* rb) {
        RingBufferStats stats = {0, 0, 0, 0, 0, 0, 0, 0, 0};
        if (rb) {
            stats = static_cast<SimpleBoostQueue*>(rb)->get_stats();
        }
        return stats;
    }
    
    void ring_buffer_get_stats_ptr(RingBufferStruct* rb, RingBufferStats* stats) {
        if (rb && stats) {
            *stats = static_cast<SimpleBoostQueue*>(rb)->get_stats();
        }
    }
    
    void ring_buffer_reset_stats(RingBufferStruct* rb) {
        if (rb) {
            auto* queue = static_cast<SimpleBoostQueue*>(rb);
            queue->total_bytes_written = 0;
            queue->total_bytes_read = 0;
        }
    }
    
    int ring_buffer_dec_ref(RingBufferStruct* rb) {
        // Similarly, just return 1 for success or 0 for failure
        return rb ? 1 : 0;
    }
}
