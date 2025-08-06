#include "boost_ring_buffer.h"
#include <iostream>
#include <chrono>
#include <sstream>
#include <algorithm>

using namespace boost::interprocess;

// 构造函数
BoostRingBuffer::BoostRingBuffer(const std::string& queue_name, uint32_t size) 
    : name(queue_name), segment(nullptr), metadata(nullptr), queue(nullptr), 
      char_alloc(nullptr), string_alloc(nullptr) {
    
    try {
        // 创建或打开共享内存段
        std::string shm_name = "sage_queue_" + queue_name;
        size_t shm_size = size + 65536; // 额外空间用于元数据和管理
        
        try {
            // 尝试创建新的共享内存段
            segment = new managed_shared_memory(create_only, shm_name.c_str(), shm_size);
        } catch (const interprocess_exception& ex) {
            // 如果已存在，则打开
            segment = new managed_shared_memory(open_only, shm_name.c_str());
        }
        
        // 创建分配器
        char_alloc = new CharAllocator(segment->get_segment_manager());
        string_alloc = new StringAllocator(segment->get_segment_manager());
        
        // 查找或创建队列元数据
        std::string meta_name = queue_name + "_meta";
        metadata = segment->find_or_construct<QueueMetadata>(meta_name.c_str())(size);
        
        // 查找或创建消息队列
        std::string queue_name_str = queue_name + "_queue";
        queue = segment->find_or_construct<MessageQueue>(queue_name_str.c_str())(*string_alloc);
        
    } catch (const std::exception& e) {
        std::cerr << "Error creating BoostRingBuffer: " << e.what() << std::endl;
        throw;
    }
}

// 析构函数
BoostRingBuffer::~BoostRingBuffer() {
    delete char_alloc;
    delete string_alloc;
    delete segment;
}

// 放入数据
bool BoostRingBuffer::put(const void* data, uint32_t data_size, double timeout_sec) {
    if (!segment || !metadata || !queue || metadata->closed) {
        return false;
    }
    
    scoped_lock<interprocess_mutex> lock(metadata->mutex);
    
    // 检查超时
    if (timeout_sec >= 0) {
        auto timeout = std::chrono::steady_clock::now() + 
                      std::chrono::milliseconds(static_cast<int64_t>(timeout_sec * 1000));
        
        while (metadata->current_size >= metadata->max_size && !metadata->closed) {
            if (!metadata->not_full.timed_wait(lock, timeout)) {
                return false; // 超时
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
        // 创建消息字符串
        ShmString message(*char_alloc);
        message.assign(static_cast<const char*>(data), data_size);
        
        // 添加到队列
        queue->push_back(message);
        metadata->current_size++;
        
        // 通知等待的消费者
        metadata->not_empty.notify_one();
        
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Error in put: " << e.what() << std::endl;
        return false;
    }
}

// 获取数据
bool BoostRingBuffer::get(void* buffer, uint32_t* buffer_size, double timeout_sec) {
    if (!segment || !metadata || !queue || !buffer || !buffer_size || metadata->closed) {
        return false;
    }
    
    scoped_lock<interprocess_mutex> lock(metadata->mutex);
    
    // 检查超时
    if (timeout_sec >= 0) {
        auto timeout = std::chrono::steady_clock::now() + 
                      std::chrono::milliseconds(static_cast<int64_t>(timeout_sec * 1000));
        
        while (queue->empty() && !metadata->closed) {
            if (!metadata->not_empty.timed_wait(lock, timeout)) {
                return false; // 超时
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
        // 获取消息
        ShmString& message = queue->front();
        uint32_t message_size = message.size();
        
        // 检查缓冲区大小
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
        
        // 通知等待的生产者
        metadata->not_full.notify_one();
        
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Error in get: " << e.what() << std::endl;
        return false;
    }
}

// 窥视数据
bool BoostRingBuffer::peek(void* buffer, uint32_t* buffer_size) {
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
bool BoostRingBuffer::is_empty() {
    if (!metadata || !queue) return true;
    scoped_lock<interprocess_mutex> lock(metadata->mutex);
    return queue->empty();
}

bool BoostRingBuffer::is_full() {
    if (!metadata) return true;
    scoped_lock<interprocess_mutex> lock(metadata->mutex);
    return metadata->current_size >= metadata->max_size;
}

uint32_t BoostRingBuffer::available_read() {
    if (!metadata) return 0;
    scoped_lock<interprocess_mutex> lock(metadata->mutex);
    return metadata->current_size;
}

uint32_t BoostRingBuffer::available_write() {
    if (!metadata) return 0;
    scoped_lock<interprocess_mutex> lock(metadata->mutex);
    return metadata->max_size - metadata->current_size;
}

uint32_t BoostRingBuffer::size() {
    if (!metadata) return 0;
    return metadata->max_size;
}

void BoostRingBuffer::close() {
    if (metadata) {
        scoped_lock<interprocess_mutex> lock(metadata->mutex);
        metadata->closed = true;
        metadata->not_empty.notify_all();
        metadata->not_full.notify_all();
    }
}

// C 接口实现
extern "C" {
    RingBufferStruct* ring_buffer_create_named(const char* name, uint32_t size) {
        try {
            return new BoostRingBuffer(std::string(name), size);
        } catch (const std::exception& e) {
            std::cerr << "ring_buffer_create_named error: " << e.what() << std::endl;
            return nullptr;
        }
    }
    
    RingBufferStruct* ring_buffer_open(const char* name) {
        try {
            return new BoostRingBuffer(std::string(name), 0); // size ignored for open
        } catch (const std::exception& e) {
            std::cerr << "ring_buffer_open error: " << e.what() << std::endl;
            return nullptr;
        }
    }
    
    void ring_buffer_destroy(RingBufferStruct* rb) {
        if (rb) {
            delete static_cast<BoostRingBuffer*>(rb);
        }
    }
    
    int ring_buffer_put(RingBufferStruct* rb, const void* data, uint32_t size) {
        if (!rb) return -1;
        return static_cast<BoostRingBuffer*>(rb)->put(data, size, -1) ? size : -1;
    }
    
    int ring_buffer_put_timeout(RingBufferStruct* rb, const void* data, uint32_t size, double timeout_sec) {
        if (!rb) return -1;
        return static_cast<BoostRingBuffer*>(rb)->put(data, size, timeout_sec) ? size : -1;
    }
    
    int ring_buffer_get(RingBufferStruct* rb, void* buffer, uint32_t buffer_size) {
        if (!rb) return -1;
        uint32_t actual_size = buffer_size;
        return static_cast<BoostRingBuffer*>(rb)->get(buffer, &actual_size, -1) ? actual_size : -1;
    }
    
    int ring_buffer_get_timeout(RingBufferStruct* rb, void* buffer, uint32_t buffer_size, double timeout_sec) {
        if (!rb) return -1;
        uint32_t actual_size = buffer_size;
        return static_cast<BoostRingBuffer*>(rb)->get(buffer, &actual_size, timeout_sec) ? actual_size : -1;
    }
    
    int ring_buffer_peek(RingBufferStruct* rb, void* buffer, uint32_t buffer_size) {
        if (!rb) return -1;
        uint32_t actual_size = buffer_size;
        return static_cast<BoostRingBuffer*>(rb)->peek(buffer, &actual_size) ? actual_size : -1;
    }
    
    int ring_buffer_is_empty(RingBufferStruct* rb) {
        return rb ? static_cast<BoostRingBuffer*>(rb)->is_empty() : 1;
    }
    
    int ring_buffer_is_full(RingBufferStruct* rb) {
        return rb ? static_cast<BoostRingBuffer*>(rb)->is_full() : 1;
    }
    
    uint32_t ring_buffer_available_read(RingBufferStruct* rb) {
        return rb ? static_cast<BoostRingBuffer*>(rb)->available_read() : 0;
    }
    
    uint32_t ring_buffer_available_write(RingBufferStruct* rb) {
        return rb ? static_cast<BoostRingBuffer*>(rb)->available_write() : 0;
    }
    
    uint32_t ring_buffer_size(RingBufferStruct* rb) {
        return rb ? static_cast<BoostRingBuffer*>(rb)->size() : 0;
    }
    
    void ring_buffer_close(RingBufferStruct* rb) {
        if (rb) {
            static_cast<BoostRingBuffer*>(rb)->close();
        }
    }
}
