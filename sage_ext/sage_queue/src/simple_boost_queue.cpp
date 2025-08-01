#include "simple_boost_queue.h"
#include <iostream>
#include <unistd.h>
#include <cstring>

using namespace boost::interprocess;

// 构造函数
SimpleBoostQueue::SimpleBoostQueue(const std::string& queue_name, uint32_t size) 
    : name(queue_name), segment(nullptr), metadata(nullptr), queue(nullptr) {
    
    try {
        // 创建或打开共享内存段
        std::string shm_name = "sage_queue_" + queue_name;
        size_t shm_size = std::max(static_cast<size_t>(size * 2 + 65536), 1024UL * 1024UL); // 至少1MB
        
        try {
            // 尝试创建新的共享内存段
            segment = new managed_shared_memory(create_only, shm_name.c_str(), shm_size);
        } catch (const interprocess_exception& ex) {
            // 如果已存在，则打开
            try {
                segment = new managed_shared_memory(open_only, shm_name.c_str());
            } catch (const interprocess_exception& ex2) {
                // 如果打开失败，可能是权限问题，尝试先删除再创建
                shared_memory_object::remove(shm_name.c_str());
                segment = new managed_shared_memory(create_only, shm_name.c_str(), shm_size);
            }
        }
        
        // 创建分配器
        CharAllocator char_alloc(segment->get_segment_manager());
        StringAllocator string_alloc(segment->get_segment_manager());
        
        // 查找或创建队列元数据
        std::string meta_name = queue_name + "_meta";
        metadata = segment->find_or_construct<QueueMetadata>(meta_name.c_str())(size);
        
        // 查找或创建消息队列
        std::string queue_name_str = queue_name + "_queue";
        queue = segment->find_or_construct<MessageQueue>(queue_name_str.c_str())(string_alloc);
        
    } catch (const std::exception& e) {
        std::cerr << "Error creating SimpleBoostQueue: " << e.what() << std::endl;
        throw;
    }
}

// 析构函数
SimpleBoostQueue::~SimpleBoostQueue() {
    delete segment;
}

// 转换时间格式
boost::posix_time::ptime timeout_to_ptime(double timeout_sec) {
    if (timeout_sec < 0) {
        return boost::posix_time::pos_infin;
    }
    
    auto now = boost::posix_time::microsec_clock::universal_time();
    auto duration = boost::posix_time::milliseconds(static_cast<long>(timeout_sec * 1000));
    return now + duration;
}

// 放入数据
bool SimpleBoostQueue::put(const void* data, uint32_t data_size, double timeout_sec) {
    if (!segment || !metadata || !queue || metadata->closed) {
        return false;
    }
    
    scoped_lock<interprocess_mutex> lock(metadata->mutex);
    
    // 检查超时
    auto timeout = timeout_to_ptime(timeout_sec);
    
    if (timeout_sec >= 0) {
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
        // 创建分配器
        CharAllocator char_alloc(segment->get_segment_manager());
        
        // 创建消息字符串
        ShmString message(char_alloc);
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
bool SimpleBoostQueue::get(void* buffer, uint32_t* buffer_size, double timeout_sec) {
    if (!segment || !metadata || !queue || !buffer || !buffer_size || metadata->closed) {
        return false;
    }
    
    scoped_lock<interprocess_mutex> lock(metadata->mutex);
    
    // 检查超时
    auto timeout = timeout_to_ptime(timeout_sec);
    
    if (timeout_sec >= 0) {
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
    if (metadata) {
        scoped_lock<interprocess_mutex> lock(metadata->mutex);
        metadata->closed = true;
        metadata->not_empty.notify_all();
        metadata->not_full.notify_all();
    }
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
            std::cerr << "ring_buffer_create_named error: " << e.what() << std::endl;
            return nullptr;
        }
    }
    
    RingBufferStruct* ring_buffer_open(const char* name) {
        try {
            return new SimpleBoostQueue(std::string(name), 1000); // 默认大小
        } catch (const std::exception& e) {
            std::cerr << "ring_buffer_open error: " << e.what() << std::endl;
            return nullptr;
        }
    }
    
    void ring_buffer_destroy(RingBufferStruct* rb) {
        if (rb) {
            delete static_cast<SimpleBoostQueue*>(rb);
        }
    }
    
    int ring_buffer_put(RingBufferStruct* rb, const void* data, uint32_t size) {
        if (!rb) return -1;
        return static_cast<SimpleBoostQueue*>(rb)->put(data, size, -1) ? size : -1;
    }
    
    int ring_buffer_put_timeout(RingBufferStruct* rb, const void* data, uint32_t size, double timeout_sec) {
        if (!rb) return -1;
        return static_cast<SimpleBoostQueue*>(rb)->put(data, size, timeout_sec) ? size : -1;
    }
    
    int ring_buffer_get(RingBufferStruct* rb, void* buffer, uint32_t buffer_size) {
        if (!rb) return -1;
        uint32_t actual_size = buffer_size;
        return static_cast<SimpleBoostQueue*>(rb)->get(buffer, &actual_size, -1) ? actual_size : -1;
    }
    
    int ring_buffer_get_timeout(RingBufferStruct* rb, void* buffer, uint32_t buffer_size, double timeout_sec) {
        if (!rb) return -1;
        uint32_t actual_size = buffer_size;
        return static_cast<SimpleBoostQueue*>(rb)->get(buffer, &actual_size, timeout_sec) ? actual_size : -1;
    }
    
    // 兼容性操作
    int ring_buffer_write(RingBufferStruct* rb, const void* data, uint32_t size) {
        return ring_buffer_put(rb, data, size);
    }
    
    int ring_buffer_read(RingBufferStruct* rb, void* buffer, uint32_t size) {
        return ring_buffer_get(rb, buffer, size);
    }
    
    int ring_buffer_peek(RingBufferStruct* rb, void* buffer, uint32_t buffer_size) {
        if (!rb) return -1;
        uint32_t actual_size = buffer_size;
        return static_cast<SimpleBoostQueue*>(rb)->peek(buffer, &actual_size) ? actual_size : -1;
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
    
    uint32_t ring_buffer_size(RingBufferStruct* rb) {
        return rb ? static_cast<SimpleBoostQueue*>(rb)->size_limit() : 0;
    }
    
    void ring_buffer_close(RingBufferStruct* rb) {
        if (rb) {
            static_cast<SimpleBoostQueue*>(rb)->close();
        }
    }
    
    // 引用管理（简化实现）
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
}
