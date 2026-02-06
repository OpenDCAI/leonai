#!/usr/bin/env python3
"""
Python 装饰器完整示例
包含：函数装饰器、类装饰器、各种实用场景
"""

import functools
import time
from collections.abc import Callable

# ========================================
# 1. 基础函数装饰器
# ========================================


def simple_decorator(func: Callable) -> Callable:
    """最简单的装饰器示例"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"[简单装饰器] 调用函数: {func.__name__}")
        result = func(*args, **kwargs)
        print("[简单装饰器] 函数执行完毕")
        return result

    return wrapper


# ========================================
# 2. 带参数的函数装饰器
# ========================================


def repeat(times: int = 1):
    """重复执行函数指定次数"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = None
            for i in range(times):
                print(f"[重复装饰器] 第 {i + 1}/{times} 次执行")
                result = func(*args, **kwargs)
            return result

        return wrapper

    return decorator


def timer(func: Callable) -> Callable:
    """计时装饰器：测量函数执行时间"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"[计时器] {func.__name__} 执行耗时: {end_time - start_time:.4f}秒")
        return result

    return wrapper


def debug(func: Callable) -> Callable:
    """调试装饰器：打印函数调用信息"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        args_repr = [repr(a) for a in args]
        kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
        signature = ", ".join(args_repr + kwargs_repr)
        print(f"[调试] 调用 {func.__name__}({signature})")
        result = func(*args, **kwargs)
        print(f"[调试] {func.__name__} 返回 {result!r}")
        return result

    return wrapper


def validate_types(**type_hints):
    """类型验证装饰器"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 验证参数类型
            for arg_name, expected_type in type_hints.items():
                if arg_name in kwargs:
                    value = kwargs[arg_name]
                    if not isinstance(value, expected_type):
                        raise TypeError(
                            f"参数 {arg_name} 应该是 {expected_type.__name__}, 但得到了 {type(value).__name__}"
                        )
            return func(*args, **kwargs)

        return wrapper

    return decorator


def cache(func: Callable) -> Callable:
    """缓存装饰器：缓存函数结果（简单版）"""
    cached_results = {}

    @functools.wraps(func)
    def wrapper(*args):
        if args in cached_results:
            print("[缓存] 从缓存中获取结果")
            return cached_results[args]
        result = func(*args)
        cached_results[args] = result
        return result

    return wrapper


def retry(max_attempts: int = 3, delay: float = 1.0):
    """重试装饰器：失败时自动重试"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        print(f"[重试] 已达到最大重试次数 {max_attempts}")
                        raise
                    print(f"[重试] 第 {attempt + 1} 次失败: {e}, {delay}秒后重试...")
                    time.sleep(delay)

        return wrapper

    return decorator


# ========================================
# 3. 类装饰器（用类实现装饰器）
# ========================================


class CountCalls:
    """统计函数调用次数的类装饰器"""

    def __init__(self, func: Callable):
        functools.update_wrapper(self, func)
        self.func = func
        self.count = 0

    def __call__(self, *args, **kwargs):
        self.count += 1
        print(f"[计数器] {self.func.__name__} 已被调用 {self.count} 次")
        return self.func(*args, **kwargs)

    def reset(self):
        """重置计数器"""
        self.count = 0


class RateLimiter:
    """限流装饰器：限制函数调用频率"""

    def __init__(self, max_calls: int, time_window: float):
        """
        :param max_calls: 时间窗口内最大调用次数
        :param time_window: 时间窗口（秒）
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            # 移除过期的调用记录
            self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]

            if len(self.calls) >= self.max_calls:
                raise RuntimeError(f"[限流] 超过速率限制：{self.max_calls}次/{self.time_window}秒")

            self.calls.append(now)
            return func(*args, **kwargs)

        return wrapper


class Memoize:
    """记忆化装饰器：高级缓存实现"""

    def __init__(self, func: Callable):
        functools.update_wrapper(self, func)
        self.func = func
        self.cache = {}
        self.hits = 0
        self.misses = 0

    def __call__(self, *args, **kwargs):
        # 创建缓存键
        key = str(args) + str(kwargs)

        if key in self.cache:
            self.hits += 1
            print(f"[记忆化] 缓存命中 (命中率: {self.hit_rate:.2%})")
            return self.cache[key]

        self.misses += 1
        result = self.func(*args, **kwargs)
        self.cache[key] = result
        return result

    @property
    def hit_rate(self) -> float:
        """计算缓存命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0

    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0


# ========================================
# 4. 装饰类的装饰器
# ========================================


def singleton(cls):
    """单例模式装饰器：确保类只有一个实例"""
    instances = {}

    @functools.wraps(cls)
    def get_instance(*args, **kwargs):
        if cls not in instances:
            print(f"[单例] 创建 {cls.__name__} 的新实例")
            instances[cls] = cls(*args, **kwargs)
        else:
            print(f"[单例] 返回 {cls.__name__} 的现有实例")
        return instances[cls]

    return get_instance


def add_methods(**methods):
    """为类添加方法的装饰器"""

    def decorator(cls):
        for name, method in methods.items():
            setattr(cls, name, method)
        return cls

    return decorator


def log_methods(cls):
    """为类的所有方法添加日志的装饰器"""
    for name, method in cls.__dict__.items():
        if callable(method) and not name.startswith("_"):
            setattr(cls, name, debug(method))
    return cls


# ========================================
# 5. 高级装饰器模式
# ========================================


def property_decorator(func: Callable) -> property:
    """将函数转换为属性装饰器"""
    return property(func)


def synchronized(lock=None):
    """线程同步装饰器"""
    import threading

    if lock is None:
        lock = threading.Lock()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                return func(*args, **kwargs)

        return wrapper

    return decorator


def deprecated(reason: str = ""):
    """标记函数为已废弃"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import warnings

            msg = f"{func.__name__} 已废弃"
            if reason:
                msg += f": {reason}"
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        return wrapper

    return decorator


# ========================================
# 6. 使用示例
# ========================================


def demo_basic_decorators():
    """基础装饰器示例"""
    print("\n" + "=" * 50)
    print("1. 基础装饰器示例")
    print("=" * 50)

    @simple_decorator
    def greet(name: str):
        print(f"Hello, {name}!")

    greet("Alice")


def demo_parameterized_decorators():
    """带参数的装饰器示例"""
    print("\n" + "=" * 50)
    print("2. 带参数的装饰器示例")
    print("=" * 50)

    @repeat(times=3)
    def say_hello():
        print("Hello!")

    say_hello()


def demo_timer_decorator():
    """计时装饰器示例"""
    print("\n" + "=" * 50)
    print("3. 计时装饰器示例")
    print("=" * 50)

    @timer
    def slow_function():
        time.sleep(0.1)
        return "完成"

    result = slow_function()
    print(f"结果: {result}")


def demo_debug_decorator():
    """调试装饰器示例"""
    print("\n" + "=" * 50)
    print("4. 调试装饰器示例")
    print("=" * 50)

    @debug
    def add(a: int, b: int) -> int:
        return a + b

    add(3, 5)
    add(10, b=20)


def demo_cache_decorator():
    """缓存装饰器示例"""
    print("\n" + "=" * 50)
    print("5. 缓存装饰器示例")
    print("=" * 50)

    @cache
    def fibonacci(n: int) -> int:
        print(f"  计算 fibonacci({n})")
        if n < 2:
            return n
        return fibonacci(n - 1) + fibonacci(n - 2)

    print(f"fibonacci(5) = {fibonacci(5)}")
    print(f"fibonacci(5) = {fibonacci(5)}")  # 第二次调用会使用缓存


def demo_class_decorator():
    """类装饰器示例"""
    print("\n" + "=" * 50)
    print("6. 类装饰器示例")
    print("=" * 50)

    @CountCalls
    def process_data(data):
        return f"处理数据: {data}"

    process_data("A")
    process_data("B")
    process_data("C")
    print(f"总调用次数: {process_data.count}")


def demo_memoize_decorator():
    """记忆化装饰器示例"""
    print("\n" + "=" * 50)
    print("7. 记忆化装饰器示例")
    print("=" * 50)

    @Memoize
    def expensive_calculation(x: int, y: int) -> int:
        print(f"  执行复杂计算: {x} * {y}")
        time.sleep(0.05)  # 模拟耗时操作
        return x * y

    expensive_calculation(3, 4)
    expensive_calculation(5, 6)
    expensive_calculation(3, 4)  # 缓存命中
    expensive_calculation(5, 6)  # 缓存命中
    print(f"最终命中率: {expensive_calculation.hit_rate:.2%}")


def demo_singleton_decorator():
    """单例装饰器示例"""
    print("\n" + "=" * 50)
    print("8. 单例装饰器示例")
    print("=" * 50)

    @singleton
    class DatabaseConnection:
        def __init__(self, host: str):
            self.host = host
            print(f"连接到数据库: {host}")

    db1 = DatabaseConnection("localhost")
    db2 = DatabaseConnection("localhost")
    print(f"db1 和 db2 是同一个实例: {db1 is db2}")


def demo_stacked_decorators():
    """堆叠装饰器示例"""
    print("\n" + "=" * 50)
    print("9. 堆叠装饰器示例")
    print("=" * 50)

    @timer
    @debug
    @CountCalls
    def complex_function(x: int, y: int) -> int:
        """多个装饰器组合使用"""
        time.sleep(0.05)
        return x**y

    complex_function(2, 3)
    complex_function(3, 2)


def demo_retry_decorator():
    """重试装饰器示例"""
    print("\n" + "=" * 50)
    print("10. 重试装饰器示例")
    print("=" * 50)

    attempt_count = 0

    @retry(max_attempts=3, delay=0.1)
    def unstable_function():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ValueError(f"模拟失败 (尝试 {attempt_count})")
        return "成功!"

    try:
        result = unstable_function()
        print(f"结果: {result}")
    except Exception as e:
        print(f"最终失败: {e}")


def demo_validate_types_decorator():
    """类型验证装饰器示例"""
    print("\n" + "=" * 50)
    print("11. 类型验证装饰器示例")
    print("=" * 50)

    @validate_types(name=str, age=int)
    def create_user(name, age):
        return f"用户: {name}, 年龄: {age}"

    try:
        print(create_user(name="Alice", age=25))
        print(create_user(name="Bob", age="30"))  # 这会抛出类型错误
    except TypeError as e:
        print(f"类型错误: {e}")


def demo_deprecated_decorator():
    """废弃标记装饰器示例"""
    print("\n" + "=" * 50)
    print("12. 废弃标记装饰器示例")
    print("=" * 50)

    @deprecated(reason="请使用 new_function() 代替")
    def old_function():
        return "这是旧函数"

    import warnings

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = old_function()
        if w:
            print(f"警告: {w[0].message}")


def demo_class_decoration():
    """装饰类的示例"""
    print("\n" + "=" * 50)
    print("13. 装饰类的示例")
    print("=" * 50)

    @log_methods
    class Calculator:
        def add(self, a, b):
            return a + b

        def multiply(self, a, b):
            return a * b

    calc = Calculator()
    calc.add(3, 5)
    calc.multiply(4, 6)


# ========================================
# 7. 主函数
# ========================================


def main():
    """运行所有示例"""
    print("\n" + "=" * 50)
    print("Python 装饰器完整示例")
    print("=" * 50)

    demo_basic_decorators()
    demo_parameterized_decorators()
    demo_timer_decorator()
    demo_debug_decorator()
    demo_cache_decorator()
    demo_class_decorator()
    demo_memoize_decorator()
    demo_singleton_decorator()
    demo_stacked_decorators()
    demo_retry_decorator()
    demo_validate_types_decorator()
    demo_deprecated_decorator()
    demo_class_decoration()

    print("\n" + "=" * 50)
    print("所有示例演示完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
