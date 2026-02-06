# Python 装饰器完整指南

## 目录
1. [装饰器基础](#装饰器基础)
2. [函数装饰器详解](#函数装饰器详解)
3. [类装饰器详解](#类装饰器详解)
4. [函数装饰器 vs 类装饰器](#函数装饰器-vs-类装饰器)
5. [高级应用场景](#高级应用场景)
6. [最佳实践](#最佳实践)

---

## 装饰器基础

### 什么是装饰器？

装饰器是 Python 中一种强大的设计模式，它允许你在**不修改原函数代码**的情况下，为函数添加额外的功能。

**核心概念：**
- 装饰器是一个返回函数的**高阶函数**
- 使用 `@decorator_name` 语法糖简化调用
- 本质上是闭包和函数式编程的应用

**基本语法：**
```python
@decorator
def function():
    pass

# 等价于
function = decorator(function)
```

---

## 函数装饰器详解

### 1. 简单函数装饰器

```python
def simple_decorator(func):
    def wrapper(*args, **kwargs):
        print("Before function call")
        result = func(*args, **kwargs)
        print("After function call")
        return result
    return wrapper

@simple_decorator
def greet(name):
    print(f"Hello, {name}!")
```

**特点：**
- ✅ 简洁直观
- ✅ 使用闭包保存状态
- ✅ 适合简单逻辑
- ❌ 不保留原函数元数据（需要 `@wraps`）

### 2. 保留元数据

```python
from functools import wraps

def better_decorator(func):
    @wraps(func)  # 保留 __name__, __doc__ 等
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
```

**为什么需要 `@wraps`？**
```python
def without_wraps(func):
    def wrapper():
        return func()
    return wrapper

def with_wraps(func):
    @wraps(func)
    def wrapper():
        return func()
    return wrapper

@without_wraps
def func1():
    """文档"""
    pass

@with_wraps
def func2():
    """文档"""
    pass

print(func1.__name__)  # wrapper (丢失了原函数名)
print(func2.__name__)  # func2 (保留了原函数名)
```

### 3. 带参数的函数装饰器

```python
def repeat(times):
    """外层函数接收装饰器参数"""
    def decorator(func):
        """中层函数接收被装饰的函数"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            """内层函数执行实际逻辑"""
            for _ in range(times):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator

@repeat(times=3)
def say_hello():
    print("Hello!")
```

**三层嵌套结构：**
1. **外层**：接收装饰器参数
2. **中层**：接收被装饰的函数
3. **内层**：执行实际包装逻辑

### 4. 函数装饰器的优势

| 优势 | 说明 |
|------|------|
| **简洁性** | 代码简单，易于理解 |
| **闭包特性** | 自然地通过闭包保存状态 |
| **性能** | 执行效率略高（无需实例化） |
| **函数式风格** | 符合函数式编程范式 |

### 5. 函数装饰器的局限

```python
def counter_decorator(func):
    count = 0  # 闭包变量
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal count
        count += 1
        print(f"Call count: {count}")
        return func(*args, **kwargs)
    
    # 问题：无法直接访问或重置 count
    return wrapper
```

**局限：**
- ❌ 状态管理不够直观
- ❌ 难以提供公共接口（如 reset 方法）
- ❌ 复杂逻辑时代码可读性下降

---

## 类装饰器详解

### 1. 使用类实现装饰器

```python
from functools import wraps

class CountCalls:
    """使用类作为装饰器"""
    
    def __init__(self, func):
        wraps(func)(self)  # 保留元数据
        self.func = func
        self.count = 0
    
    def __call__(self, *args, **kwargs):
        """使对象可调用"""
        self.count += 1
        print(f"Call count: {self.count}")
        return self.func(*args, **kwargs)
    
    def reset(self):
        """提供公共接口"""
        self.count = 0

@CountCalls
def my_function():
    print("Function called")

# 使用
my_function()  # Call count: 1
my_function()  # Call count: 2
my_function.reset()  # 重置计数
```

**关键点：**
- `__init__`：初始化时接收被装饰的函数
- `__call__`：使实例对象可以像函数一样被调用
- 可以添加额外的方法（如 `reset`）

### 2. 带参数的类装饰器

```python
class Repeat:
    """带参数的类装饰器"""
    
    def __init__(self, times):
        """接收装饰器参数"""
        self.times = times
    
    def __call__(self, func):
        """接收被装饰的函数"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            for _ in range(self.times):
                result = func(*args, **kwargs)
            return result
        return wrapper

@Repeat(times=3)
def greet():
    print("Hello!")
```

**注意：**
- `__init__` 接收装饰器参数
- `__call__` 接收被装饰的函数，返回包装器

### 3. 类装饰器的优势

| 优势 | 说明 |
|------|------|
| **面向对象** | 符合 OOP 设计原则 |
| **状态管理** | 通过实例属性管理状态更清晰 |
| **可扩展性** | 易于添加方法和属性 |
| **复杂逻辑** | 适合实现复杂的装饰器逻辑 |
| **代码组织** | 相关逻辑封装在类中 |

### 4. 高级类装饰器示例

```python
class RateLimiter:
    """限流装饰器：限制函数调用频率"""
    
    def __init__(self, max_calls, time_window):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
    
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            now = time.time()
            
            # 清理过期记录
            self.calls = [t for t in self.calls 
                         if now - t < self.time_window]
            
            # 检查是否超限
            if len(self.calls) >= self.max_calls:
                raise RuntimeError("Rate limit exceeded")
            
            self.calls.append(now)
            return func(*args, **kwargs)
        return wrapper

@RateLimiter(max_calls=5, time_window=60)
def api_call():
    print("API called")
```

---

## 函数装饰器 vs 类装饰器

### 详细对比表

| 特性 | 函数装饰器 | 类装饰器 |
|------|-----------|----------|
| **实现方式** | 函数 + 闭包 | 类 + `__call__` |
| **代码结构** | 嵌套函数 | 类方法 |
| **状态管理** | 闭包变量（`nonlocal`） | 实例属性（`self.xxx`） |
| **可读性** | 简单场景更直观 | 复杂逻辑更清晰 |
| **可扩展性** | 难以添加方法 | 易于添加方法和属性 |
| **性能** | 略快（无实例化开销） | 略慢（需要实例化） |
| **调试** | 闭包变量不易查看 | 实例属性易于检查 |
| **适用场景** | 简单装饰器 | 复杂装饰器 |
| **学习曲线** | 需理解闭包 | 需理解 `__call__` |

### 何时使用函数装饰器？

✅ **推荐使用场景：**
- 简单的功能增强（日志、计时）
- 无需保存复杂状态
- 不需要提供额外的方法
- 追求极致性能

```python
# 适合函数装饰器的例子
@timer
def calculate():
    pass

@debug
def process():
    pass
```

### 何时使用类装饰器？

✅ **推荐使用场景：**
- 需要保存和管理复杂状态
- 需要提供额外的方法或接口
- 装饰器逻辑复杂
- 需要良好的代码组织

```python
# 适合类装饰器的例子
@RateLimiter(max_calls=10, time_window=60)
def api_call():
    pass

@Memoize  # 需要 clear_cache() 等方法
def expensive_function():
    pass
```

---

## 装饰类的装饰器

### 1. 单例模式

```python
def singleton(cls):
    """装饰类，使其成为单例"""
    instances = {}
    
    @wraps(cls)
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    
    return get_instance

@singleton
class Database:
    def __init__(self):
        print("Connecting to database...")

db1 = Database()
db2 = Database()
print(db1 is db2)  # True
```

### 2. 为类添加方法

```python
def add_str_method(cls):
    """为类添加 __str__ 方法"""
    def __str__(self):
        attrs = ', '.join(f"{k}={v}" for k, v in self.__dict__.items())
        return f"{cls.__name__}({attrs})"
    
    cls.__str__ = __str__
    return cls

@add_str_method
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

person = Person("Alice", 30)
print(person)  # Person(name=Alice, age=30)
```

### 3. 日志记录所有方法

```python
def log_all_methods(cls):
    """为类的所有方法添加日志"""
    for name, method in cls.__dict__.items():
        if callable(method) and not name.startswith('_'):
            setattr(cls, name, debug(method))
    return cls

@log_all_methods
class Calculator:
    def add(self, a, b):
        return a + b
    
    def multiply(self, a, b):
        return a * b
```

---

## 高级应用场景

### 1. 堆叠装饰器

装饰器可以堆叠使用，**执行顺序从下到上**：

```python
@decorator1
@decorator2
@decorator3
def func():
    pass

# 等价于
func = decorator1(decorator2(decorator3(func)))
```

**示例：**
```python
@timer          # 3. 最外层：计时
@debug          # 2. 中间层：调试
@cache          # 1. 最内层：缓存
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

### 2. 条件装饰器

```python
def conditional_decorator(condition):
    """根据条件决定是否应用装饰器"""
    def decorator(func):
        if condition:
            @wraps(func)
            def wrapper(*args, **kwargs):
                print("Decorator applied")
                return func(*args, **kwargs)
            return wrapper
        return func  # 条件不满足，返回原函数
    return decorator

DEBUG = True

@conditional_decorator(DEBUG)
def my_function():
    print("Function called")
```

### 3. 装饰器工厂

```python
def decorator_factory(decorator_type):
    """根据类型创建不同的装饰器"""
    decorators = {
        'timer': timer,
        'debug': debug,
        'cache': cache,
    }
    return decorators.get(decorator_type, lambda x: x)

# 动态选择装饰器
decorator = decorator_factory('timer')

@decorator
def my_function():
    pass
```

---

## 实用装饰器模式

### 1. 权限检查

```python
def require_permission(permission):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 假设第一个参数是 user 对象
            user = args[0] if args else None
            if not user or not hasattr(user, 'has_permission'):
                raise ValueError("Invalid user")
            
            if not user.has_permission(permission):
                raise PermissionError(f"需要权限: {permission}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

@require_permission('admin')
def delete_user(user, user_id):
    print(f"删除用户 {user_id}")
```

### 2. 异常处理

```python
def handle_exceptions(*exception_types):
    """捕获并处理指定类型的异常"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exception_types as e:
                print(f"捕获异常: {type(e).__name__}: {e}")
                return None
        return wrapper
    return decorator

@handle_exceptions(ValueError, TypeError)
def parse_int(value):
    return int(value)
```

### 3. 输入验证

```python
def validate_input(**validators):
    """验证函数参数"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for param_name, validator in validators.items():
                if param_name in kwargs:
                    value = kwargs[param_name]
                    if not validator(value):
                        raise ValueError(f"参数 {param_name} 验证失败")
            return func(*args, **kwargs)
        return wrapper
    return decorator

@validate_input(
    age=lambda x: 0 <= x <= 150,
    email=lambda x: '@' in x
)
def create_user(name, age, email):
    print(f"创建用户: {name}, {age}, {email}")
```

### 4. 性能监控

```python
import time
from collections import defaultdict

class PerformanceMonitor:
    """性能监控装饰器"""
    
    def __init__(self):
        self.stats = defaultdict(lambda: {'count': 0, 'total_time': 0})
    
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            
            stats = self.stats[func.__name__]
            stats['count'] += 1
            stats['total_time'] += elapsed
            
            return result
        return wrapper
    
    def report(self):
        """生成性能报告"""
        print("\n性能报告:")
        print("-" * 50)
        for func_name, stats in self.stats.items():
            avg_time = stats['total_time'] / stats['count']
            print(f"{func_name}:")
            print(f"  调用次数: {stats['count']}")
            print(f"  总耗时: {stats['total_time']:.4f}s")
            print(f"  平均耗时: {avg_time:.4f}s")

monitor = PerformanceMonitor()

@monitor
def task1():
    time.sleep(0.1)

@monitor
def task2():
    time.sleep(0.2)

# 使用
task1()
task2()
task1()
monitor.report()
```

---

## 最佳实践

### 1. 始终使用 `@wraps`

```python
from functools import wraps

def my_decorator(func):
    @wraps(func)  # ✅ 正确
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
```

### 2. 保持装饰器的透明性

装饰器应该**不改变**函数的签名和返回值类型：

```python
# ❌ 错误：改变了返回值类型
def bad_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        return str(result)  # 强制转换为字符串
    return wrapper

# ✅ 正确：保持原有返回值
def good_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print("Before call")
        result = func(*args, **kwargs)
        print("After call")
        return result  # 返回原始结果
    return wrapper
```

### 3. 使用 `*args` 和 `**kwargs`

让装饰器支持任意参数：

```python
def flexible_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):  # ✅ 支持任意参数
        return func(*args, **kwargs)
    return wrapper
```

### 4. 类装饰器要保留元数据

```python
from functools import wraps

class MyDecorator:
    def __init__(self, func):
        wraps(func)(self)  # ✅ 保留元数据
        self.func = func
    
    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)
```

### 5. 文档字符串

为装饰器添加清晰的文档：

```python
def my_decorator(func):
    """
    这个装饰器的功能说明。
    
    Args:
        func: 被装饰的函数
    
    Returns:
        装饰后的函数
    
    Example:
        @my_decorator
        def my_func():
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
```

### 6. 避免过度使用

```python
# ❌ 避免：装饰器堆叠过多
@decorator1
@decorator2
@decorator3
@decorator4
@decorator5
def func():
    pass

# ✅ 推荐：合并装饰器逻辑
@combined_decorator
def func():
    pass
```

---

## 总结

### 装饰器选择指南

```
简单功能增强？
  └─ 是 → 使用函数装饰器
  └─ 否 → 需要保存复杂状态？
           └─ 是 → 使用类装饰器
           └─ 否 → 需要提供额外方法？
                    └─ 是 → 使用类装饰器
                    └─ 否 → 使用函数装饰器
```

### 核心要点

1. **函数装饰器**：简洁、高效，适合简单场景
2. **类装饰器**：强大、灵活，适合复杂场景
3. **始终使用** `@wraps` 保留元数据
4. **保持透明性**：不改变函数签名和行为
5. **适度使用**：避免过度装饰

### 学习路径

1. 掌握基本函数装饰器
2. 理解闭包和作用域
3. 学习带参数的装饰器
4. 掌握类装饰器
5. 理解 `__call__` 方法
6. 实践高级模式（堆叠、条件等）

---

## 参考资料

- [PEP 318 - Decorators for Functions and Methods](https://www.python.org/dev/peps/pep-0318/)
- [functools.wraps 文档](https://docs.python.org/3/library/functools.html#functools.wraps)
- Python Cookbook (Chapter 9: Metaprogramming)
