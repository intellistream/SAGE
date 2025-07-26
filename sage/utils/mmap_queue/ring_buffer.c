#define _GNU_SOURCE
#include "ring_buffer.h"
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>
#include <stdio.h>
#include <stdatomic.h>

// 内部工具函数
uint32_t next_power_of_2(uint32_t v) {
    if (v == 0) return 1;
    v--;
    v |= v >> 1;
    v |= v >> 2;
    v |= v >> 4;
    v |= v >> 8;
    v |= v >> 16;
    v++;
    return v;
}

bool is_power_of_2(uint32_t v) {
    return v != 0 && (v & (v - 1)) == 0;
}

static void init_process_shared_mutex(pthread_mutex_t* mutex) {
    pthread_mutexattr_t attr;
    pthread_mutexattr_init(&attr);
    pthread_mutexattr_setpshared(&attr, PTHREAD_PROCESS_SHARED);
    pthread_mutexattr_settype(&attr, PTHREAD_MUTEX_RECURSIVE);
    pthread_mutex_init(mutex, &attr);
    pthread_mutexattr_destroy(&attr);
}

ring_buffer_t* ring_buffer_create(const char* name, uint32_t size) {
    if (!name || strlen(name) == 0 || strlen(name) >= MAX_NAME_LEN) {
        return NULL;
    }
    
    char shm_name[256];
    snprintf(shm_name, sizeof(shm_name), "/sage_ringbuf_%s", name);
    
    // 确保大小是2的幂次，便于取模优化
    size = next_power_of_2(size);
    if (size < 1024) size = 1024; // 最小1KB
    
    uint32_t total_size = sizeof(ring_buffer_t) + size;
    
    // 创建共享内存
    int fd = shm_open(shm_name, O_CREAT | O_RDWR | O_EXCL, 0666);
    if (fd == -1) {
        if (errno == EEXIST) {
            // 已存在，尝试打开
            return ring_buffer_open(name);
        }
        return NULL;
    }
    
    // 设置大小
    if (ftruncate(fd, total_size) == -1) {
        close(fd);
        shm_unlink(shm_name);
        return NULL;
    }
    
    // 映射内存
    ring_buffer_t* rb = mmap(NULL, total_size, PROT_READ | PROT_WRITE, 
                           MAP_SHARED, fd, 0);
    close(fd);
    
    if (rb == MAP_FAILED) {
        shm_unlink(shm_name);
        return NULL;
    }
    
    // 初始化结构
    memset(rb, 0, sizeof(ring_buffer_t));
    rb->magic = RING_BUFFER_MAGIC;
    rb->version = RING_BUFFER_VERSION;
    rb->buffer_size = size;
    rb->head = 0;
    rb->tail = 0;
    rb->readers = 0;
    rb->writers = 0;
    rb->ref_count = 1;
    rb->process_count = 1;
    rb->creator_pid = getpid();
    rb->total_bytes_written = 0;
    rb->total_bytes_read = 0;
    strncpy(rb->name, name, MAX_NAME_LEN - 1);
    rb->name[MAX_NAME_LEN - 1] = '\0';
    
    // 初始化互斥锁（进程间共享）
    init_process_shared_mutex(&rb->ref_mutex);
    
    return rb;
}

ring_buffer_t* ring_buffer_open(const char* name) {
    if (!name || strlen(name) == 0) {
        return NULL;
    }
    
    char shm_name[256];
    snprintf(shm_name, sizeof(shm_name), "/sage_ringbuf_%s", name);
    
    int fd = shm_open(shm_name, O_RDWR, 0666);
    if (fd == -1) return NULL;
    
    // 先映射头部获取大小信息
    ring_buffer_t* header = mmap(NULL, sizeof(ring_buffer_t), 
                               PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (header == MAP_FAILED) {
        close(fd);
        return NULL;
    }
    
    if (header->magic != RING_BUFFER_MAGIC) {
        munmap(header, sizeof(ring_buffer_t));
        close(fd);
        return NULL;
    }
    
    uint32_t total_size = sizeof(ring_buffer_t) + header->buffer_size;
    munmap(header, sizeof(ring_buffer_t));
    
    // 重新映射完整区域
    ring_buffer_t* rb = mmap(NULL, total_size, PROT_READ | PROT_WRITE, 
                           MAP_SHARED, fd, 0);
    close(fd);
    
    if (rb == MAP_FAILED) {
        return NULL;
    }
    
    // 增加进程计数
    atomic_fetch_add(&rb->process_count, 1);
    
    return rb;
}

void ring_buffer_close(ring_buffer_t* rb) {
    if (!rb || rb->magic != RING_BUFFER_MAGIC) {
        return;
    }
    
    // 减少进程计数
    atomic_fetch_sub(&rb->process_count, 1);
    
    // 取消内存映射
    uint32_t total_size = sizeof(ring_buffer_t) + rb->buffer_size;
    munmap(rb, total_size);
}

void ring_buffer_destroy(const char* name) {
    if (!name) return;
    
    char shm_name[256];
    snprintf(shm_name, sizeof(shm_name), "/sage_ringbuf_%s", name);
    shm_unlink(shm_name);
}

uint32_t ring_buffer_available_read(ring_buffer_t* rb) {
    if (!rb || rb->magic != RING_BUFFER_MAGIC) {
        return 0;
    }
    
    uint64_t head = atomic_load(&rb->head);
    uint64_t tail = atomic_load(&rb->tail);
    return (uint32_t)(tail - head);
}

uint32_t ring_buffer_available_write(ring_buffer_t* rb) {
    if (!rb || rb->magic != RING_BUFFER_MAGIC) {
        return 0;
    }
    
    return rb->buffer_size - ring_buffer_available_read(rb) - 1;
}

bool ring_buffer_is_empty(ring_buffer_t* rb) {
    return ring_buffer_available_read(rb) == 0;
}

bool ring_buffer_is_full(ring_buffer_t* rb) {
    return ring_buffer_available_write(rb) == 0;
}

int ring_buffer_write(ring_buffer_t* rb, const void* data, uint32_t len) {
    if (!rb || !data || rb->magic != RING_BUFFER_MAGIC || len == 0) {
        return -1;
    }
    
    if (len > ring_buffer_available_write(rb)) {
        return -1; // 空间不足
    }
    
    atomic_fetch_add(&rb->writers, 1);
    
    uint64_t tail = atomic_load(&rb->tail);
    uint32_t pos = tail & (rb->buffer_size - 1);
    
    if (pos + len <= rb->buffer_size) {
        // 连续写入
        memcpy(&rb->data[pos], data, len);
    } else {
        // 分段写入（环绕）
        uint32_t first_part = rb->buffer_size - pos;
        memcpy(&rb->data[pos], data, first_part);
        memcpy(&rb->data[0], (const char*)data + first_part, len - first_part);
    }
    
    // 更新tail指针
    atomic_store(&rb->tail, tail + len);
    atomic_fetch_add(&rb->total_bytes_written, len);
    atomic_fetch_sub(&rb->writers, 1);
    
    return len;
}

int ring_buffer_read(ring_buffer_t* rb, void* data, uint32_t len) {
    if (!rb || !data || rb->magic != RING_BUFFER_MAGIC || len == 0) {
        return -1;
    }
    
    if (len > ring_buffer_available_read(rb)) {
        return -1; // 数据不足
    }
    
    atomic_fetch_add(&rb->readers, 1);
    
    uint64_t head = atomic_load(&rb->head);
    uint32_t pos = head & (rb->buffer_size - 1);
    
    if (pos + len <= rb->buffer_size) {
        // 连续读取
        memcpy(data, &rb->data[pos], len);
    } else {
        // 分段读取（环绕）
        uint32_t first_part = rb->buffer_size - pos;
        memcpy(data, &rb->data[pos], first_part);
        memcpy((char*)data + first_part, &rb->data[0], len - first_part);
    }
    
    // 更新head指针
    atomic_store(&rb->head, head + len);
    atomic_fetch_add(&rb->total_bytes_read, len);
    atomic_fetch_sub(&rb->readers, 1);
    
    return len;
}

int ring_buffer_peek(ring_buffer_t* rb, void* data, uint32_t len) {
    if (!rb || !data || rb->magic != RING_BUFFER_MAGIC || len == 0) {
        return -1;
    }
    
    if (len > ring_buffer_available_read(rb)) {
        return -1; // 数据不足
    }
    
    uint64_t head = atomic_load(&rb->head);
    uint32_t pos = head & (rb->buffer_size - 1);
    
    if (pos + len <= rb->buffer_size) {
        // 连续读取
        memcpy(data, &rb->data[pos], len);
    } else {
        // 分段读取（环绕）
        uint32_t first_part = rb->buffer_size - pos;
        memcpy(data, &rb->data[pos], first_part);
        memcpy((char*)data + first_part, &rb->data[0], len - first_part);
    }
    
    // 注意：peek不移动head指针
    return len;
}

ring_buffer_ref_t* ring_buffer_get_ref(ring_buffer_t* rb) {
    if (!rb || rb->magic != RING_BUFFER_MAGIC) {
        return NULL;
    }
    
    ring_buffer_ref_t* ref = malloc(sizeof(ring_buffer_ref_t));
    if (!ref) return NULL;
    
    strncpy(ref->name, rb->name, MAX_NAME_LEN);
    ref->size = rb->buffer_size;
    ref->auto_cleanup = false;
    ref->creator_pid = rb->creator_pid;
    
    // 增加引用计数
    ring_buffer_inc_ref(rb);
    
    return ref;
}

ring_buffer_t* ring_buffer_from_ref(const ring_buffer_ref_t* ref) {
    if (!ref) return NULL;
    
    ring_buffer_t* rb = ring_buffer_open(ref->name);
    if (rb) {
        ring_buffer_inc_ref(rb);
    }
    return rb;
}

int ring_buffer_inc_ref(ring_buffer_t* rb) {
    if (!rb || rb->magic != RING_BUFFER_MAGIC) {
        return -1;
    }
    
    pthread_mutex_lock(&rb->ref_mutex);
    uint32_t new_count = ++rb->ref_count;
    pthread_mutex_unlock(&rb->ref_mutex);
    
    return new_count;
}

int ring_buffer_dec_ref(ring_buffer_t* rb) {
    if (!rb || rb->magic != RING_BUFFER_MAGIC) {
        return -1;
    }
    
    // 先保存需要的值，避免在解锁后访问
    uint32_t total_size = sizeof(ring_buffer_t) + rb->buffer_size;
    char shm_name[256];
    snprintf(shm_name, sizeof(shm_name), "/sage_ringbuf_%s", rb->name);
    
    pthread_mutex_lock(&rb->ref_mutex);
    uint32_t new_count = --rb->ref_count;
    
    // 如果引用计数为0，清理资源
    if (new_count == 0) {
        // 销毁互斥锁（必须在munmap之前）
        pthread_mutex_unlock(&rb->ref_mutex);
        pthread_mutex_destroy(&rb->ref_mutex);
        
        // 取消映射并删除共享内存
        munmap(rb, total_size);
        shm_unlink(shm_name);
        return 0;
    }
    
    pthread_mutex_unlock(&rb->ref_mutex);
    return new_count;
}

void ring_buffer_release_ref(ring_buffer_ref_t* ref) {
    if (ref) {
        free(ref);
    }
}

void ring_buffer_get_stats(ring_buffer_t* rb, ring_buffer_stats_t* stats) {
    if (!rb || !stats || rb->magic != RING_BUFFER_MAGIC) {
        return;
    }
    
    stats->buffer_size = rb->buffer_size;
    stats->available_read = ring_buffer_available_read(rb);
    stats->available_write = ring_buffer_available_write(rb);
    stats->readers = atomic_load(&rb->readers);
    stats->writers = atomic_load(&rb->writers);
    stats->ref_count = atomic_load(&rb->ref_count);
    stats->total_bytes_written = atomic_load(&rb->total_bytes_written);
    stats->total_bytes_read = atomic_load(&rb->total_bytes_read);
    
    // 计算使用率
    if (rb->buffer_size > 0) {
        stats->utilization = (double)stats->available_read / (double)rb->buffer_size;
    } else {
        stats->utilization = 0.0;
    }
}

void ring_buffer_reset_stats(ring_buffer_t* rb) {
    if (!rb || rb->magic != RING_BUFFER_MAGIC) {
        return;
    }
    
    atomic_store(&rb->total_bytes_written, 0);
    atomic_store(&rb->total_bytes_read, 0);
}

int ring_buffer_write_batch(ring_buffer_t* rb, const void* const* data_ptrs, 
                           const uint32_t* lengths, uint32_t batch_count) {
    if (!rb || !data_ptrs || !lengths || rb->magic != RING_BUFFER_MAGIC || batch_count == 0) {
        return -1;
    }
    
    // 计算总长度
    uint32_t total_len = 0;
    for (uint32_t i = 0; i < batch_count; i++) {
        total_len += lengths[i];
    }
    
    if (total_len > ring_buffer_available_write(rb)) {
        return -1; // 空间不足
    }
    
    atomic_fetch_add(&rb->writers, 1);
    
    uint64_t tail = atomic_load(&rb->tail);
    uint32_t pos = tail & (rb->buffer_size - 1);
    
    // 批量写入
    for (uint32_t i = 0; i < batch_count; i++) {
        uint32_t len = lengths[i];
        const void* data = data_ptrs[i];
        
        if (pos + len <= rb->buffer_size) {
            // 连续写入
            memcpy(&rb->data[pos], data, len);
            pos += len;
        } else {
            // 分段写入（环绕）
            uint32_t first_part = rb->buffer_size - pos;
            memcpy(&rb->data[pos], data, first_part);
            memcpy(&rb->data[0], (const char*)data + first_part, len - first_part);
            pos = len - first_part;
        }
    }
    
    atomic_store(&rb->tail, tail + total_len);
    atomic_fetch_add(&rb->total_bytes_written, total_len);
    atomic_fetch_sub(&rb->writers, 1);
    
    return total_len;
}

int ring_buffer_read_batch(ring_buffer_t* rb, void** data_ptrs, 
                          uint32_t* lengths, uint32_t max_batch_count) {
    if (!rb || !data_ptrs || !lengths || rb->magic != RING_BUFFER_MAGIC || max_batch_count == 0) {
        return -1;
    }
    
    uint32_t available = ring_buffer_available_read(rb);
    if (available == 0) {
        return 0; // 无数据可读
    }
    
    atomic_fetch_add(&rb->readers, 1);
    
    uint64_t head = atomic_load(&rb->head);
    uint32_t pos = head & (rb->buffer_size - 1);
    uint32_t batch_count = 0;
    uint32_t total_read = 0;
    
    // 批量读取（这里简化实现，实际可能需要更复杂的协议）
    while (batch_count < max_batch_count && total_read < available) {
        uint32_t remaining = available - total_read;
        uint32_t chunk_size = remaining > 1024 ? 1024 : remaining;
        
        data_ptrs[batch_count] = malloc(chunk_size);
        if (!data_ptrs[batch_count]) break;
        
        if (pos + chunk_size <= rb->buffer_size) {
            memcpy(data_ptrs[batch_count], &rb->data[pos], chunk_size);
            pos += chunk_size;
        } else {
            uint32_t first_part = rb->buffer_size - pos;
            memcpy(data_ptrs[batch_count], &rb->data[pos], first_part);
            memcpy((char*)data_ptrs[batch_count] + first_part, &rb->data[0], chunk_size - first_part);
            pos = chunk_size - first_part;
        }
        
        lengths[batch_count] = chunk_size;
        total_read += chunk_size;
        batch_count++;
    }
    
    atomic_store(&rb->head, head + total_read);
    atomic_fetch_add(&rb->total_bytes_read, total_read);
    atomic_fetch_sub(&rb->readers, 1);
    
    return batch_count;
}
