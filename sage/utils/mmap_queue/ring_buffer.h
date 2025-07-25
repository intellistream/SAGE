#ifndef SAGE_RING_BUFFER_H
#define SAGE_RING_BUFFER_H

#define _GNU_SOURCE
#include <stdint.h>
#include <stdbool.h>
#include <pthread.h>
#include <sys/types.h>

#define RING_BUFFER_MAGIC 0x53414745424C4B52ULL  // "SAGEBLKR"
#define MAX_NAME_LEN 64
#define RING_BUFFER_VERSION 1

typedef struct {
    uint64_t magic;                     // 魔数，用于验证
    uint32_t version;                   // 版本号
    uint32_t buffer_size;               // 缓冲区大小（2的幂次）
    volatile uint64_t head;             // 读指针
    volatile uint64_t tail;             // 写指针
    volatile uint32_t readers;          // 当前读者计数
    volatile uint32_t writers;          // 当前写者计数
    volatile uint32_t ref_count;        // 引用计数
    volatile uint32_t process_count;    // 进程计数
    pthread_mutex_t ref_mutex;          // 引用计数互斥锁
    char name[MAX_NAME_LEN];            // 缓冲区名称
    pid_t creator_pid;                  // 创建者进程ID
    uint64_t total_bytes_written;       // 总写入字节数（统计用）
    uint64_t total_bytes_read;          // 总读取字节数（统计用）
    char padding[64 - 40];              // 缓存行对齐
    char data[0];                       // 实际数据区域
} ring_buffer_t;

// 可序列化的引用结构
typedef struct {
    char name[MAX_NAME_LEN];
    uint32_t size;
    bool auto_cleanup;                  // 是否自动清理
    pid_t creator_pid;                  // 创建者PID
} ring_buffer_ref_t;

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
    double utilization;                 // 使用率
} ring_buffer_stats_t;

#ifdef __cplusplus
extern "C" {
#endif

// 基础 API
ring_buffer_t* ring_buffer_create(const char* name, uint32_t size);
ring_buffer_t* ring_buffer_open(const char* name);
void ring_buffer_close(ring_buffer_t* rb);
void ring_buffer_destroy(const char* name);

// 读写操作
int ring_buffer_write(ring_buffer_t* rb, const void* data, uint32_t len);
int ring_buffer_read(ring_buffer_t* rb, void* data, uint32_t len);
int ring_buffer_peek(ring_buffer_t* rb, void* data, uint32_t len);

// 状态查询
uint32_t ring_buffer_available_read(ring_buffer_t* rb);
uint32_t ring_buffer_available_write(ring_buffer_t* rb);
bool ring_buffer_is_empty(ring_buffer_t* rb);
bool ring_buffer_is_full(ring_buffer_t* rb);

// 引用管理
ring_buffer_ref_t* ring_buffer_get_ref(ring_buffer_t* rb);
ring_buffer_t* ring_buffer_from_ref(const ring_buffer_ref_t* ref);
void ring_buffer_release_ref(ring_buffer_ref_t* ref);
int ring_buffer_inc_ref(ring_buffer_t* rb);
int ring_buffer_dec_ref(ring_buffer_t* rb);

// 统计和诊断
void ring_buffer_get_stats(ring_buffer_t* rb, ring_buffer_stats_t* stats);
void ring_buffer_reset_stats(ring_buffer_t* rb);

// 高级操作
int ring_buffer_write_batch(ring_buffer_t* rb, const void* const* data_ptrs, 
                           const uint32_t* lengths, uint32_t batch_count);
int ring_buffer_read_batch(ring_buffer_t* rb, void** data_ptrs, 
                          uint32_t* lengths, uint32_t max_batch_count);

// 内部工具函数
uint32_t next_power_of_2(uint32_t v);
bool is_power_of_2(uint32_t v);

#ifdef __cplusplus
}
#endif

#endif // SAGE_RING_BUFFER_H
