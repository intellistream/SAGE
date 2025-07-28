#ifndef RING_BUFFER_H
#define RING_BUFFER_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct RingBuffer RingBuffer;

RingBuffer* ring_buffer_create(size_t capacity);
void ring_buffer_destroy(RingBuffer* rb);
int ring_buffer_put(RingBuffer* rb, const void* data, size_t size);
int ring_buffer_get(RingBuffer* rb, void* data, size_t* size);
int ring_buffer_try_get(RingBuffer* rb, void* data, size_t* size);
size_t ring_buffer_size(RingBuffer* rb);
int ring_buffer_empty(RingBuffer* rb);
void ring_buffer_clear(RingBuffer* rb);

#ifdef __cplusplus
}
#endif

#endif