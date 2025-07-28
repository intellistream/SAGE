--- ring_buffer.c 修复建议 ---

以下是发现的主要问题和修复方案：

1. 【致命漏洞】ring_buffer_dec_ref 函数中的内存访问问题
   问题：在 munmap 之前访问 rb->buffer_size，但互斥锁已解锁
   
   修复方案：
   ```c
   int ring_buffer_dec_ref(ring_buffer_t* rb) {
       if (!rb || rb->magic != RING_BUFFER_MAGIC) {
           return -1;
       }
       
       // 先保存需要的值
       uint32_t total_size = sizeof(ring_buffer_t) + rb->buffer_size;
       char shm_name[256];
       snprintf(shm_name, sizeof(shm_name), "/sage_ringbuf_%s", rb->name);
       
       pthread_mutex_lock(&rb->ref_mutex);
       uint32_t new_count = --rb->ref_count;
       
       if (new_count == 0) {
           // 销毁互斥锁
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
   ```

2. 【资源泄漏】互斥锁未正确销毁
   问题：创建的互斥锁没有销毁
   修复：在销毁共享内存前调用 pthread_mutex_destroy

3. 【潜在问题】批量读取中的内存管理不明确
   问题：malloc 的内存需要调用者释放
   修复：在文档中明确说明，或提供释放函数

4. 【竞态条件】原子操作不完整
   问题：某些操作应该是原子的但没有适当保护
   修复：使用适当的内存屏障和原子操作

5. 【错误处理】错误处理不够健壮
   问题：某些错误情况下可能导致资源泄漏
   修复：添加更完善的错误处理和清理逻辑
