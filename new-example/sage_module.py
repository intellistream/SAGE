

class Module:
    def __init__(self):
        sub_module = Module()
    
    # 这个方法会形成一个dag
    # 其中的submodule是一个可复用的actor，然后dag流经一个actor instance
    # 声明时向母module登记lazy module和lazy对象，然后运行时才创建这个资源。
    @pipeline
    def forward(self, x):
        temp_module = Module()
        return x.map(temp_module.forward).filter(lambda x:x>0)
        # temp_module = SomeModule.options(remote = "some machine tag")(some_args)
        # 其中sub_module.forward也是一个分布式dataflow dag，然后这样就嵌套了
    # 每一个pipeline调用，在运行时编译为独立dag。
    # 分配一个编译线程，在它的栈里控制临时资源的生命周期
    # 栈在线程内引用计数归零时，释放它的资源和下游的节点
    # 于是它既是dsl，又是运行时实际被执行的真实代码
    # 虽然dag是运行时编译的，但是可以对它做hash，结构和资源相同的dag，持有相同的hash值。然后在节点里，根据这个dag hash做routing
    # 我知道了，@pipeline的修饰会做一个dag builder，然后dag builder会带着里边使用的，临时资源的引用，走到外面的一个栈里边去，等着dag引用结束再删除。
    # temp_module.forward可以把self给解出来。
    # 还有一个问题，那就是中间节点挂了，已经消费的中间数据会对下游产生影响。上游节点只能整体重放，然后下游节点也要有幂等性。