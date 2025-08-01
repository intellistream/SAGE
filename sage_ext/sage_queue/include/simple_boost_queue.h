#ifndef SIMPLE_BOOST_QUEUE_H
#define SIMPLE_BOOST_QUEUE_H

#include <boost/interprocess/managed_shared_memory.hpp>
#include <boost/interprocess/containers/string.hpp>
#include <boost/interprocess/containers/deque.hpp>
#include <boost/interprocess/allocators/allocator.hpp>
#include <boost/interprocess/sync/interprocess_mutex.hpp>
#include <boost/interprocess/sync/interprocess_condition.hpp>
#include <boost/interprocess/sync/scoped_lock.hpp>
#include <boost/date_time/posix_time/posix_time.hpp>
#include <string>
#include <cstring>

namespace boost_ipc = boost::interprocess;

// 类型定义
typedef boost_ipc::allocator<char, boost_ipc::managed_shared_memory::segment_manager> CharAllocator;
typedef boost_ipc::basic_string<char, std::char_traits<char>, CharAllocator> ShmString;
typedef boost_ipc::allocator<ShmString, boost_ipc::managed_shared_memory::segment_manager> StringAllocator;
typedef boost_ipc::deque<ShmString, StringAllocator> MessageQueue;

// 队列元数据
struct QueueMetadata {
    boost_ipc::interprocess_mutex mutex;
    boost_ipc::interprocess_condition not_empty;
    boost_ipc::interprocess_condition not_full;
    uint32_t max_size;
    uint32_t current_size;
    bool closed;
    
    QueueMetadata(uint32_t max_sz) : max_size(max_sz), current_size(0), closed(false) {}
};

// 简化的队列结构体
struct SimpleBoostQueue {
    boost_ipc::managed_shared_memory* segment;
    QueueMetadata* metadata;
    MessageQueue* queue;
    std::string name;
    
    SimpleBoostQueue(const std::string& queue_name, uint32_t size);
    ~SimpleBoostQueue();
    
    bool put(const void* data, uint32_t size, double timeout_sec = -1);
    bool get(void* buffer, uint32_t* size, double timeout_sec = -1);
    bool peek(void* buffer, uint32_t* size);
    bool is_empty();
    bool is_full();
    uint32_t available_read();
    uint32_t available_write();
    uint32_t size_limit();
    void close();
};

// C 接口
extern "C" {
    typedef struct SimpleBoostQueue RingBufferStruct;
    
    // 基本操作
    RingBufferStruct* ring_buffer_create(uint32_t size);
    RingBufferStruct* ring_buffer_create_named(const char* name, uint32_t size);
    RingBufferStruct* ring_buffer_open(const char* name);
    void ring_buffer_destroy(RingBufferStruct* rb);
    
    // 数据操作
    int ring_buffer_put(RingBufferStruct* rb, const void* data, uint32_t size);
    int ring_buffer_put_timeout(RingBufferStruct* rb, const void* data, uint32_t size, double timeout_sec);
    int ring_buffer_get(RingBufferStruct* rb, void* buffer, uint32_t buffer_size);
    int ring_buffer_get_timeout(RingBufferStruct* rb, void* buffer, uint32_t buffer_size, double timeout_sec);
    
    // 兼容性操作
    int ring_buffer_write(RingBufferStruct* rb, const void* data, uint32_t size);
    int ring_buffer_read(RingBufferStruct* rb, void* buffer, uint32_t size);
    
    // 查询操作
    int ring_buffer_peek(RingBufferStruct* rb, void* buffer, uint32_t buffer_size);
    int ring_buffer_is_empty(RingBufferStruct* rb);
    int ring_buffer_is_full(RingBufferStruct* rb);
    uint32_t ring_buffer_available_read(RingBufferStruct* rb);
    uint32_t ring_buffer_available_write(RingBufferStruct* rb);
    uint32_t ring_buffer_size(RingBufferStruct* rb);
    void ring_buffer_close(RingBufferStruct* rb);
    
    // 引用管理
    typedef struct {
        char name[64];
        uint32_t size;
        int auto_cleanup;
        int creator_pid;
    } RingBufferRef;
    
    RingBufferRef* ring_buffer_get_ref(RingBufferStruct* rb);
    RingBufferStruct* ring_buffer_from_ref(RingBufferRef* ref);
    void ring_buffer_release_ref(RingBufferRef* ref);
}

#endif // SIMPLE_BOOST_QUEUE_H
