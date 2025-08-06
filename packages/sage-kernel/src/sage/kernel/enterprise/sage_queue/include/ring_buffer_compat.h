#ifndef RING_BUFFER_H
#define RING_BUFFER_H

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

// 为了兼容性，重新定义结构体
typedef struct RingBuffer RingBuffer;
typedef struct RingBuffer RingBufferStruct;

// 基础队列操作
RingBuffer* ring_buffer_create(size_t capacity);
RingBuffer* ring_buffer_create_named(const char* name, uint32_t size);
RingBuffer* ring_buffer_open(const char* name);
void ring_buffer_destroy(RingBuffer* rb);
void ring_buffer_destroy_by_name(const char* name);
void ring_buffer_close(RingBuffer* rb);

// 数据读写
int ring_buffer_put(RingBuffer* rb, const void* data, size_t size);
int ring_buffer_put_timeout(RingBuffer* rb, const void* data, uint32_t size, double timeout_sec);
int ring_buffer_get(RingBuffer* rb, void* data, size_t* size);
int ring_buffer_get_timeout(RingBuffer* rb, void* buffer, uint32_t buffer_size, double timeout_sec);
int ring_buffer_try_get(RingBuffer* rb, void* data, size_t* size);

// 兼容性读写函数
int ring_buffer_write(RingBuffer* rb, const void* data, uint32_t size);
int ring_buffer_read(RingBuffer* rb, void* data, uint32_t size);
int ring_buffer_peek(RingBuffer* rb, void* data, uint32_t size);

// 状态查询
size_t ring_buffer_size(RingBuffer* rb);
uint32_t ring_buffer_capacity(RingBuffer* rb);
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

#ifdef __cplusplus
}
#endif

#endif // RING_BUFFER_H
