# Python 装饰器学习资料总览

本目录包含关于 Python 装饰器的完整学习资料，涵盖函数装饰器和类装饰器的详细对比。

## 📚 文件列表

### 1. `decorator_examples.py` - 完整示例代码
**内容：** 13 个实用装饰器示例的完整实现
- ✅ 基础函数装饰器
- ✅ 带参数的装饰器
- ✅ 类装饰器实现
- ✅ 装饰类的装饰器
- ✅ 高级装饰器模式
- ✅ 所有示例都有详细注释和演示

**运行方式：**
```bash
python3 decorator_examples.py
```

**包含的装饰器：**
1. `simple_decorator` - 简单装饰器
2. `repeat` - 重复执行
3. `timer` - 计时器
4. `debug` - 调试装饰器
5. `validate_types` - 类型验证
6. `cache` - 简单缓存
7. `retry` - 重试机制
8. `CountCalls` - 调用计数（类装饰器）
9. `RateLimiter` - 限流（类装饰器）
10. `Memoize` - 高级缓存（类装饰器）
11. `singleton` - 单例模式
12. `deprecated` - 废弃标记
13. `synchronized` - 线程同步

---

### 2. `decorator_comparison.md` - 详细对比文档
**内容：** 完整的装饰器指南（13KB，746行）
- 📖 装饰器基础概念
- 📖 函数装饰器详解
- 📖 类装饰器详解
- 📖 详细对比表格
- 📖 高级应用场景
- 📖 最佳实践
- 📖 实用装饰器模式

**适合：** 深入学习和参考

---

### 3. `decorator_comparison_demo.py` - 对比演示
**内容：** 5 个直观的对比示例
- 🎯 计数器装饰器对比
- 🎯 带参数装饰器对比
- 🎯 复杂状态管理对比
- 🎯 缓存装饰器对比
- 🎯 性能测试对比

**运行方式：**
```bash
python3 decorator_comparison_demo.py
```

**输出：** 逐个展示函数装饰器和类装饰器在相同场景下的实现差异

---

### 4. `decorator_cheatsheet.txt` - 快速参考卡
**内容：** 装饰器速查手册
- 📋 基本模板（复制即用）
- 📋 对比决策树
- 📋 常用装饰器代码片段
- 📋 最佳实践清单
- 📋 常见陷阱和解决方案
- 📋 实用技巧

**适合：** 快速查阅和复制模板

---

## 🎯 学习路径建议

### 初学者路径
1. **先看** `decorator_cheatsheet.txt` 了解基本概念
2. **运行** `decorator_comparison_demo.py` 直观感受差异
3. **学习** `decorator_comparison.md` 深入理解
4. **研究** `decorator_examples.py` 学习实际应用

### 快速复习路径
1. **查看** `decorator_cheatsheet.txt` 快速回顾
2. **运行** `decorator_examples.py` 看效果
3. **参考** `decorator_comparison.md` 解决具体问题

### 实战应用路径
1. **参考** `decorator_cheatsheet.txt` 选择合适的模板
2. **查看** `decorator_examples.py` 找类似的实现
3. **复制修改** 代码用于自己的项目

---

## 🔑 核心要点总结

### 函数装饰器
```python
from functools import wraps

def my_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 装饰逻辑
        return func(*args, **kwargs)
    return wrapper
```

**特点：**
- ✅ 简洁直观
- ✅ 使用闭包保存状态
- ✅ 性能略优
- ❌ 状态管理受限
- ❌ 难以提供额外方法

**适用：** 简单的功能增强（日志、计时、调试）

---

### 类装饰器
```python
from functools import wraps

class MyDecorator:
    def __init__(self, func):
        wraps(func)(self)
        self.func = func
        # 初始化状态
    
    def __call__(self, *args, **kwargs):
        # 装饰逻辑
        return self.func(*args, **kwargs)
    
    def extra_method(self):
        # 可以提供额外方法
        pass
```

**特点：**
- ✅ 状态管理清晰
- ✅ 可以添加方法
- ✅ 适合复杂逻辑
- ✅ 面向对象风格
- ❌ 代码略多
- ❌ 性能略差

**适用：** 复杂装饰器（缓存、限流、监控）

---

## 📊 选择决策表

| 需求 | 推荐方案 |
|------|---------|
| 简单日志记录 | 函数装饰器 |
| 简单计时 | 函数装饰器 |
| 基础缓存 | 函数装饰器 |
| 需要清空缓存 | 类装饰器 |
| 需要查看统计信息 | 类装饰器 |
| 限流功能 | 类装饰器 |
| 复杂状态管理 | 类装饰器 |
| 单例模式 | 函数装饰器（装饰类） |
| 需要继承扩展 | 类装饰器 |

---

## 💡 最佳实践

### ✅ DO's
1. **总是使用 `@wraps`** 保留函数元数据
2. **使用 `*args, **kwargs`** 支持任意参数
3. **保持透明性** 不改变函数行为
4. **添加文档** 说明装饰器的用途
5. **简单优先** 从函数装饰器开始

### ❌ DON'Ts
1. **不要忘记 `@wraps`**
2. **不要改变函数签名**
3. **不要过度堆叠** 装饰器
4. **不要引入副作用**
5. **不要在不需要时使用类装饰器**

---

## 🔍 常见问题

### Q1: 何时使用函数装饰器？
**A:** 当你只需要简单的功能增强，不需要保存复杂状态或提供额外方法时。

### Q2: 何时使用类装饰器？
**A:** 当你需要管理复杂状态、提供额外方法（如 reset、get_stats）或装饰器逻辑复杂时。

### Q3: 为什么要使用 @wraps？
**A:** 保留原函数的元数据（`__name__`、`__doc__` 等），否则装饰后的函数会丢失这些信息。

### Q4: 装饰器的执行顺序是什么？
**A:** 堆叠的装饰器**从下到上装饰，从上到下执行**。
```python
@decorator1  # 最后装饰，最先执行
@decorator2  # 第二装饰，第二执行
@decorator3  # 最先装饰，最后执行
def func():
    pass
```

### Q5: 类装饰器的性能差距大吗？
**A:** 差距很小（通常 < 5%），对于大多数应用可以忽略。应根据需求选择，不要过早优化。

### Q6: 如何调试装饰器？
**A:** 
- 使用 `print` 或 `logging` 输出中间状态
- 检查装饰后的函数：`print(func.__wrapped__)`（如果使用了 `@wraps`）
- 使用 IDE 的断点调试

---

## 🚀 快速开始

### 运行所有示例
```bash
# 1. 完整示例演示
python3 decorator_examples.py

# 2. 对比演示
python3 decorator_comparison_demo.py
```

### 查看文档
```bash
# 1. 快速参考
cat decorator_cheatsheet.txt

# 2. 详细指南（Markdown）
# 使用 Markdown 阅读器打开 decorator_comparison.md
```

---

## 📝 代码模板快速复制

### 简单函数装饰器
```python
from functools import wraps

def my_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Before {func.__name__}")
        result = func(*args, **kwargs)
        print(f"After {func.__name__}")
        return result
    return wrapper
```

### 带参数的函数装饰器
```python
from functools import wraps

def repeat(times):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for _ in range(times):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator
```

### 简单类装饰器
```python
from functools import wraps

class CountCalls:
    def __init__(self, func):
        wraps(func)(self)
        self.func = func
        self.count = 0
    
    def __call__(self, *args, **kwargs):
        self.count += 1
        print(f"Call #{self.count}")
        return self.func(*args, **kwargs)
```

### 带参数的类装饰器
```python
from functools import wraps

class Repeat:
    def __init__(self, times):
        self.times = times
    
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for _ in range(self.times):
                result = func(*args, **kwargs)
            return result
        return wrapper
```

---

## 🎓 学习成果检验

完成学习后，你应该能够：

- [ ] 理解装饰器的本质（高阶函数）
- [ ] 编写简单的函数装饰器
- [ ] 编写带参数的函数装饰器
- [ ] 理解闭包和 `nonlocal` 关键字
- [ ] 编写类装饰器
- [ ] 理解 `__call__` 魔法方法
- [ ] 正确使用 `@wraps` 保留元数据
- [ ] 知道何时使用函数装饰器，何时使用类装饰器
- [ ] 理解装饰器的执行顺序
- [ ] 能够装饰函数和类
- [ ] 避免常见陷阱
- [ ] 应用装饰器到实际项目

---

**祝学习顺利！🎉**

*Python 装饰器完整学习资料*
