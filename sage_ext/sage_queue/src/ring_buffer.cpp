#include <vector>
#include <thread>
#include <chrono>
#include <atomic>
#include <cstring>
#include <memory>
#include <string>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>
#include <map>
#include <mutex>
#include <semaphore.h>
#include <cstdio>
#include <ctime>
#include "ring_buffer.h"

// 跨进程共享内存结构
struct SharedMemoryQueue {
    size_t capacity;
    std::atomic<size_t> head{0};
    std::atomic<size_t> tail{0};
    std::atomic<size_t> count{0};
    sem_t put_semaphore;
    sem_t get_semaphore;
    char data[];  // 柔性数组成员，存储实际数据
};

struct RingBuffer {
    SharedMemoryQueue* shared_queue;
    int shm_fd;
    size_t shm_size;
    std::string name;
    bool is_owner;  // 是否是创建者
};

// 计算共享内存大小
size_t calculate_shm_size(size_t capacity) {
    return sizeof(SharedMemoryQueue) + capacity;
}

extern "C" {

RingBuffer* ring_buffer_create(size_t capacity) {
    // 为了向后兼容，使用默认名称创建命名队列
    char default_name[64];
    snprintf(default_name, sizeof(default_name), "rb_%d_%ld", getpid(), (long)time(nullptr));
    return ring_buffer_create_named(default_name, capacity);
}

RingBuffer* ring_buffer_create_named(const char* name, size_t capacity) {
    if (!name) return nullptr;

    auto* rb = new RingBuffer();
    rb->name = std::string("/") + name;  // POSIX共享内存名称必须以/开头
    rb->shm_size = calculate_shm_size(capacity);
    rb->is_owner = false;

    // 尝试创建共享内存
    rb->shm_fd = shm_open(rb->name.c_str(), O_CREAT | O_EXCL | O_RDWR, 0666);
    if (rb->shm_fd == -1) {
        if (errno == EEXIST) {
            // 已存在，打开现有的
            rb->shm_fd = shm_open(rb->name.c_str(), O_RDWR, 0666);
            if (rb->shm_fd == -1) {
                delete rb;
                return nullptr;
            }
        } else {
            delete rb;
            return nullptr;
        }
    } else {
        // 新创建的，设置大小
        rb->is_owner = true;
        if (ftruncate(rb->shm_fd, rb->shm_size) == -1) {
            close(rb->shm_fd);
            shm_unlink(rb->name.c_str());
            delete rb;
            return nullptr;
        }
    }

    // 映射共享内存
    void* addr = mmap(nullptr, rb->shm_size, PROT_READ | PROT_WRITE, 
                      MAP_SHARED, rb->shm_fd, 0);
    if (addr == MAP_FAILED) {
        close(rb->shm_fd);
        if (rb->is_owner) {
            shm_unlink(rb->name.c_str());
        }
        delete rb;
        return nullptr;
    }

    rb->shared_queue = static_cast<SharedMemoryQueue*>(addr);

    // 如果是创建者，初始化共享结构
    if (rb->is_owner) {
        rb->shared_queue->capacity = capacity;
        rb->shared_queue->head.store(0);
        rb->shared_queue->tail.store(0);
        rb->shared_queue->count.store(0);
        
        // 初始化信号量
        if (sem_init(&rb->shared_queue->put_semaphore, 1, 0) == -1 ||
            sem_init(&rb->shared_queue->get_semaphore, 1, 0) == -1) {
            munmap(addr, rb->shm_size);
            close(rb->shm_fd);
            shm_unlink(rb->name.c_str());
            delete rb;
            return nullptr;
        }
    }

    return rb;
}

RingBuffer* ring_buffer_open(const char* name) {
    if (!name) return nullptr;
    
    // 尝试打开现有的共享内存
    std::string shm_name = std::string("/") + name;
    int shm_fd = shm_open(shm_name.c_str(), O_RDWR, 0666);
    if (shm_fd == -1) {
        // 不存在，创建一个新的
        return ring_buffer_create_named(name, 1024 * 1024);
    }

    // 获取大小
    struct stat st;
    if (fstat(shm_fd, &st) == -1) {
        close(shm_fd);
        return nullptr;
    }

    auto* rb = new RingBuffer();
    rb->name = shm_name;
    rb->shm_fd = shm_fd;
    rb->shm_size = st.st_size;
    rb->is_owner = false;

    // 映射共享内存
    void* addr = mmap(nullptr, rb->shm_size, PROT_READ | PROT_WRITE, 
                      MAP_SHARED, rb->shm_fd, 0);
    if (addr == MAP_FAILED) {
        close(rb->shm_fd);
        delete rb;
        return nullptr;
    }

    rb->shared_queue = static_cast<SharedMemoryQueue*>(addr);
    return rb;
}

void ring_buffer_destroy(RingBuffer* rb) {
    if (rb) {
        if (rb->shared_queue) {
            // 如果是创建者，销毁信号量
            if (rb->is_owner) {
                sem_destroy(&rb->shared_queue->put_semaphore);
                sem_destroy(&rb->shared_queue->get_semaphore);
            }
            munmap(rb->shared_queue, rb->shm_size);
        }
        
        if (rb->shm_fd != -1) {
            close(rb->shm_fd);
        }
        
        // 如果是创建者，删除共享内存
        if (rb->is_owner && !rb->name.empty()) {
            shm_unlink(rb->name.c_str());
        }
        
        delete rb;
    }
}

int ring_buffer_put(RingBuffer* rb, const void* data, size_t size) {
    if (!rb || !data || size == 0 || !rb->shared_queue) return -1;

    // 检查是否有足够空间（包括长度字段）
    size_t total_size = sizeof(size_t) + size;
    if (rb->shared_queue->count.load() * (sizeof(size_t) + 1024) >= rb->shared_queue->capacity) {
        return -1; // 队列满
    }

    // 原子操作获取写入位置
    size_t current_tail = rb->shared_queue->tail.fetch_add(total_size) % rb->shared_queue->capacity;
    
    // 写入数据长度
    *reinterpret_cast<size_t*>(rb->shared_queue->data + current_tail) = size;
    
    // 写入数据
    memcpy(rb->shared_queue->data + current_tail + sizeof(size_t), data, size);
    
    // 增加计数
    rb->shared_queue->count.fetch_add(1);
    
    // 发信号给等待的读者
    sem_post(&rb->shared_queue->get_semaphore);
    
    return 0;
}

int ring_buffer_get(RingBuffer* rb, void* data, size_t* size) {
    if (!rb || !data || !size || !rb->shared_queue) return -1;

    // 检查是否有数据
    if (rb->shared_queue->count.load() == 0) {
        return -1; // 队列空
    }

    // 原子操作获取读取位置
    size_t current_head = rb->shared_queue->head.load();
    
    // 读取数据长度
    size_t data_size = *reinterpret_cast<size_t*>(rb->shared_queue->data + current_head);
    
    // 检查缓冲区大小
    if (*size < data_size) {
        return -2; // 缓冲区太小
    }
    
    // 复制数据
    memcpy(data, rb->shared_queue->data + current_head + sizeof(size_t), data_size);
    *size = data_size;
    
    // 更新头指针
    size_t total_size = sizeof(size_t) + data_size;
    rb->shared_queue->head.fetch_add(total_size);
    
    // 减少计数
    rb->shared_queue->count.fetch_sub(1);
    
    // 发信号给等待的写者
    sem_post(&rb->shared_queue->put_semaphore);
    
    return 0;
}

int ring_buffer_try_get(RingBuffer* rb, void* data, size_t* size) {
    // 非阻塞版本，与 get 相同
    return ring_buffer_get(rb, data, size);
}

size_t ring_buffer_size(RingBuffer* rb) {
    return rb && rb->shared_queue ? rb->shared_queue->count.load() : 0;
}

int ring_buffer_empty(RingBuffer* rb) {
    return rb && rb->shared_queue ? (rb->shared_queue->count.load() == 0 ? 1 : 0) : 1;
}

void ring_buffer_clear(RingBuffer* rb) {
    if (!rb || !rb->shared_queue) return;
    
    rb->shared_queue->head.store(0);
    rb->shared_queue->tail.store(0);
    rb->shared_queue->count.store(0);
}
}

// 新增函数：按名称销毁队列
void ring_buffer_destroy_by_name(const char* name) {
    // 这个函数主要用于清理，在当前内存实现中不需要做什么
    // 在共享内存实现中，这里会清理共享内存段
}

// 引用管理相关的函数（使用头文件中定义的结构体）
RingBufferRef* ring_buffer_get_ref(RingBuffer* rb) {
    if (!rb) return nullptr;

    auto* ref = new RingBufferRef();
    strncpy(ref->name, "memory_queue", sizeof(ref->name) - 1);
    ref->size = rb->capacity;
    ref->auto_cleanup = true;
    ref->creator_pid = getpid();
    return ref;
}

RingBuffer* ring_buffer_from_ref(RingBufferRef* ref) {
    if (!ref) return nullptr;
    return ring_buffer_create(ref->size);
}

void ring_buffer_release_ref(RingBufferRef* ref) {
    if (ref) {
        delete ref;
    }
}

int ring_buffer_inc_ref(RingBuffer* rb) {
    // 简单的引用计数（在真实实现中应该是原子的）
    return rb ? 1 : -1;
}

int ring_buffer_dec_ref(RingBuffer* rb) {
    // 简单的引用计数
    return rb ? 0 : -1;
}

// 状态查询函数
bool ring_buffer_is_empty(RingBuffer* rb) {
    return rb ? (rb->current_size.load() == 0) : true;
}

bool ring_buffer_is_full(RingBuffer* rb) {
    return rb ? (rb->current_size.load() >= rb->capacity) : false;
}

uint32_t ring_buffer_available_read(RingBuffer* rb) {
    if (!rb) return 0;

    // 返回实际的消息数量，而不是字节数
    // Python层会用这个来判断是否有数据可读
    size_t count = rb->current_size.load();
    return count > 0 ? 1 : 0;  // 简化：只要有消息就返回1，没有就返回0
}

uint32_t ring_buffer_available_write(RingBuffer* rb) {
    return rb ? (rb->capacity - rb->current_size.load()) : 0;
}

// 读写操作的兼容性函数
int ring_buffer_write(RingBuffer* rb, const void* data, uint32_t size) {
    return ring_buffer_put(rb, data, size) == 0 ? size : -1;
}

int ring_buffer_read(RingBuffer* rb, void* data, uint32_t size) {
    size_t actual_size = size;
    int result = ring_buffer_get(rb, data, &actual_size);
    return result == 0 ? actual_size : -1;
}

int ring_buffer_peek(RingBuffer* rb, void* data, uint32_t size) {
    if (!rb || !data || size == 0) return -1;

    // 简化的 peek 实现：直接使用 try_dequeue + enqueue，但要保证原子性
    std::vector<uint8_t> item;

    // 由于 ConcurrentQueue 没有真正的 peek，我们使用一个简单的方法：
    // 暂时取出数据，复制后立即放回
    if (rb->queue.try_dequeue(item)) {
        uint32_t item_size = item.size();

        // 立即将数据放回队列，尽量保持顺序
        rb->queue.enqueue(item);  // 注意：这里使用拷贝，不是 move

        // 然后返回数据给调用者
        if (size >= item_size) {
            std::memcpy(data, item.data(), item_size);
            return item_size;
        } else {
            return -2; // 缓冲区太小
        }
    }
    return -1; // 队列为空
}

// 统计信息相关函数（使用头文件中定义的结构体）
void ring_buffer_get_stats(RingBuffer* rb, RingBufferStats* stats) {
    if (!rb || !stats) return;

    stats->buffer_size = rb->capacity;
    stats->available_read = rb->current_size.load();
    stats->available_write = rb->capacity - rb->current_size.load();
    stats->readers = 1;
    stats->writers = 1;
    stats->ref_count = 1;
    stats->total_bytes_written = 0;
    stats->total_bytes_read = 0;
    stats->utilization = (double)rb->current_size.load() / rb->capacity;
}

void ring_buffer_reset_stats(RingBuffer* rb) {
    // 重置统计信息（当前实现中暂不实际存储这些统计）
}

void ring_buffer_close(RingBuffer* rb) {
    // 关闭操作，当前实现中等同于不做任何操作
    // 实际的清理由destroy完成
}

} // extern "C"