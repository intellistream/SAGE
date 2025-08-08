`ray start --head --temp-dir=...` 和 `ray.init(_temp_dir=...)` 中的 `temp_dir` 虽然听起来一样，但它们的**时机、作用范围和使用语境**都不同，下面是全方位对比解析：

---

## 🌱 总览比较表

| 项目               | `ray start --head --temp-dir=...`       | `ray.init(_temp_dir=...)`          |
| ---------------- | --------------------------------------- | ---------------------------------- |
| **使用场景**         | 启动一个 **独立 Ray 进程服务**（常用于集群/CLI）         | 启动一个 **嵌入式 Ray 实例**（Python 内部）     |
| **生效时机**         | 在 shell 启动 `ray` 守护进程时生效                | 在 Python 中启动 `ray` 客户端时生效          |
| **影响对象**         | 所有 `ray start` 生成的 session/log/plasma 等 | 当前 Python 进程启动的 `ray` 实例相关资源       |
| **session 目录位置** | 放在你指定的 `--temp-dir` 里                   | 放在你指定的 `_temp_dir` 里               |
| **socket 路径**    | 位于该目录内的 `sockets/` 文件夹                  | 同样位于 `_temp_dir` 下的 `sockets/` 文件夹 |
| **常用于**          | 手动起集群节点（head/node）                      | Python 脚本中嵌入式调用（如 notebook）        |

---

## 🍥 举个直观例子：

### 方式一：你用 CLI 起一个 Ray head node：

```bash
ray start --head \
  --temp-dir=/home/alice/tmp/ray_a
```

这个 Ray 实例会：

* 在 `/home/alice/tmp/ray_a/session_.../` 建立 Plasma Store、GCS socket、dashboard log 等；
* 等待别人连接（通过 socket 或 IP + port）。

然后别人可以用：

```python
ray.init(address="auto", _temp_dir="/home/alice/tmp/ray_a")
```

连接这个实例。

---

### 方式二：你直接在 Python 中运行：

```python
ray.init(_temp_dir="/home/alice/tmp/ray_b")
```

此时 Python 会自己启动一个独立的 Ray 实例，**不依赖 `ray start`**，并把 session 放在 `/home/alice/tmp/ray_b` 中。和 CLI 无关。

---

## ☂️ 重要区别点

| 差异点  | CLI (`ray start`)    | Python (`ray.init`)  |
| ---- | -------------------- | -------------------- |
| 运行方式 | 常驻进程                 | 嵌入式                  |
| 可连入性 | 外部程序可连（如多 Python 进程） | 默认只服务当前 Python       |
| 典型用途 | 多机集群、守护式服务           | 脚本内调度、debug、notebook |

---

## 🎯推荐使用方式（你当前场景）

> 💡**在多用户共享机器上，每个用户**：
>
> * 用 `ray.init(_temp_dir="...")` 启动属于自己的 Python 内嵌实例；
> * 或者先 `ray start --head --temp-dir="..."` 再 `ray.init(address="auto", _temp_dir="...")` 连接。

关键是：

* `--temp-dir` 和 `_temp_dir` 指向一致路径就好（这样不会找错 socket）；
* 但两者不是互相替代关系，而是配合使用。

---

## 🧃彩蛋：session\_latest 的作用？

Ray 会在 temp dir 下创建：

```bash
session_latest -> session_2025-07-22_11-30-00_12345/
```

* 它是个 **软链接**，总是指向当前活跃 session。
* 多用户若都写 `/tmp/ray`，会因为写这个链接而冲突！
* 所以必须 temp\_dir 各用各的地盘！

