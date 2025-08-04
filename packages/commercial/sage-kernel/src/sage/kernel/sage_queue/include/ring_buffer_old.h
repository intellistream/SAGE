#ifndef RING_BUFFER_H
#define RING_BUFFER_H

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct RingBuffer RingBuffer;

// 基础队列操作
RingBuffer* ring_buffer_create(size_t capacity);
RingBuffer* ring_buffer_open(const char* name);
void ring_buffer_destroy(RingBuffer* rb);
void ring_buffer_destroy_by_name(const char* name);
void ring_buffer_close(RingBuffer* rb);

// 数据读写
int ring_buffer_put(RingBuffer* rb, const void* data, size_t size);
int ring_buffer_get(RingBuffer* rb, void* data, size_t* size);
int ring_buffer_try_get(RingBuffer* rb, void* data, size_t* size);

// 兼容性读写函数
int ring_buffer_write(RingBuffer* rb, const void* data, uint32_t size);
int ring_buffer_read(RingBuffer* rb, void* data, uint32_t size);
int ring_buffer_peek(RingBuffer* rb, void* data, uint32_t size);

// 状态查询
size_t ring_buffer_size(RingBuffer* rb);
int ring_buffer_empty(RingBuffer* rb);
bool ring_buffer_is_empty(RingBuffer* rb);
bool ring_buffer_is_full(RingBuffer* rb);
uint32_t ring_buffer_available_read(RingBuffer* rb);
uint32_t ring_buffer_available_write(RingBuffer* rb);
void ring_buffer_clear(RingBuffer* rb);

// 引用管理
typedef struct {
    char name[64];
    size_t size;
    bool auto_cleanup;
    int creator_pid;
} RingBufferRef;

RingBufferRef* ring_buffer_get_ref(RingBuffer* rb);
RingBuffer* ring_buffer_from_ref(RingBufferRef* ref);
void ring_buffer_release_ref(RingBufferRef* ref);
int ring_buffer_inc_ref(RingBuffer* rb);
int ring_buffer_dec_ref(RingBuffer* rb);

// 统计信息
typedef struct {
    uint32_t buffer_size;
    uint32_t available_read;
    uint32_t available_write;
    uint32_t readers;
    uint32_t writers;
    uint32_t ref_count;
    uint64_t total_bytes_written;
    uint64_t total_bytes_read;
    double utilization;
} RingBufferStats;

void ring_buffer_get_stats(RingBuffer* rb, RingBufferStats* stats);
void ring_buffer_reset_stats(RingBuffer* rb);

#ifdef __cplusplus
}
#endif

#endif