#ifndef SIMPLE_BOOST_QUEUE_H
#define SIMPLE_BOOST_QUEUE_H

#include <boost/interprocess/managed_shared_memory.hpp>
#include <boost/interprocess/containers/deque.hpp>
#include <boost/interprocess/containers/string.hpp>
#include <boost/interprocess/allocators/allocator.hpp>
#include <boost/interprocess/sync/interprocess_mutex.hpp>
#include <boost/interprocess/sync/interprocess_condition.hpp>
#include <boost/interprocess/sync/scoped_lock.hpp>
#include <atomic>
#include <string>
#include <cstdint>

using namespace boost::interprocess;

// 引用管理
typedef struct {
    char name[64];
    uint32_t size;
    int auto_cleanup;
    int creator_pid;
} RingBufferRef;

// 统计信息结构
typedef struct {
    uint32_t buffer_size;
    uint32_t available_read;
    uint32_t available_write;
    uint32_t readers;
    uint32_t writers;
    uint32_t ref_count;
    uint64_t total_bytes_written;
    uint64_t total_bytes_read;
    uint32_t utilization;
} RingBufferStats;

// Boost 相关类型定义
namespace boost_ipc = boost::interprocess;
typedef boost_ipc::allocator<char, boost_ipc::managed_shared_memory::segment_manager> CharAllocator;
typedef boost_ipc::basic_string<char, std::char_traits<char>, CharAllocator> ShmString;
typedef boost_ipc::allocator<ShmString, boost_ipc::managed_shared_memory::segment_manager> ShmStringAllocator;
typedef boost_ipc::deque<ShmString, ShmStringAllocator> ShmDeque;

// 队列元数据结构
struct QueueMetadata {
    boost_ipc::interprocess_mutex mutex;
    boost_ipc::interprocess_condition not_empty;
    boost_ipc::interprocess_condition not_full;
    std::atomic<uint32_t> current_size;
    std::atomic<uint32_t> max_size;
    std::atomic<bool> closed;
    std::atomic<uint32_t> ref_count;
    
    QueueMetadata(uint32_t size) : current_size(0), max_size(size), closed(false), ref_count(1) {}
};

// SimpleBoostQueue 类
struct SimpleBoostQueue {
    boost_ipc::managed_shared_memory* segment;
    QueueMetadata* metadata;
    ShmDeque* queue;
    std::string name;
    uint32_t ref_count;
    uint64_t total_bytes_written;
    uint64_t total_bytes_read;
    
    SimpleBoostQueue(const std::string& queue_name, uint32_t size);
    ~SimpleBoostQueue();
    
    bool put(const void* data, uint32_t data_size, double timeout_sec = -1);
    bool get(void* buffer, uint32_t* buffer_size, double timeout_sec = -1);
    bool peek(void* buffer, uint32_t* buffer_size);
    
    bool is_empty();
    bool is_full();
    uint32_t available_read();
    uint32_t available_write();
    uint32_t size_limit();
    void close();
    
    RingBufferStats get_stats() const;
};

// C 接口
typedef SimpleBoostQueue RingBufferStruct;

#ifdef __cplusplus
extern "C" {
#endif

    RingBufferStruct* ring_buffer_create(uint32_t size);
    RingBufferStruct* ring_buffer_create_named(const char* name, uint32_t size);
    RingBufferStruct* ring_buffer_open(const char* name);
    void ring_buffer_destroy(RingBufferStruct* rb);
    
    int ring_buffer_put(RingBufferStruct* rb, const void* data, uint32_t data_size, double timeout_sec);
    int ring_buffer_get(RingBufferStruct* rb, void* buffer, uint32_t* buffer_size, double timeout_sec);
    int ring_buffer_peek(RingBufferStruct* rb, void* buffer, uint32_t* buffer_size);
    
    int ring_buffer_is_empty(RingBufferStruct* rb);
    int ring_buffer_is_full(RingBufferStruct* rb);
    uint32_t ring_buffer_available_read(RingBufferStruct* rb);
    uint32_t ring_buffer_available_write(RingBufferStruct* rb);
    uint32_t ring_buffer_size_limit(RingBufferStruct* rb);
    void ring_buffer_close(RingBufferStruct* rb);
    
    // 引用管理
    RingBufferRef* ring_buffer_get_ref(RingBufferStruct* rb);
    RingBufferStruct* ring_buffer_from_ref(RingBufferRef* ref);
    void ring_buffer_release_ref(RingBufferRef* ref);
    int ring_buffer_inc_ref(RingBufferStruct* rb);
    int ring_buffer_dec_ref(RingBufferStruct* rb);
    
    // 统计信息
    RingBufferStats ring_buffer_get_stats(RingBufferStruct* rb);

#ifdef __cplusplus
}
#endif

#endif // SIMPLE_BOOST_QUEUE_H
