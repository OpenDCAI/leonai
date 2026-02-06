#!/usr/bin/env python3
"""
函数装饰器 vs 类装饰器 - 直观对比示例
展示两种装饰器的实现差异和使用场景
"""

import time
from functools import wraps

print("=" * 70)
print("函数装饰器 vs 类装饰器 - 直观对比")
print("=" * 70)


# ============================================================================
# 示例 1: 简单的计数器装饰器
# ============================================================================

print("\n" + "=" * 70)
print("示例 1: 计数器装饰器")
print("=" * 70)

# 方式 1: 函数装饰器实现
print("\n【方式 1: 函数装饰器】")


def counter_function(func):
    """使用函数实现的计数器装饰器"""
    count = 0  # 闭包变量

    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal count  # 需要 nonlocal 关键字
        count += 1
        print(f"  [函数装饰器] 第 {count} 次调用 {func.__name__}")
        return func(*args, **kwargs)

    # 问题：无法直接访问 count 或提供重置方法
    return wrapper


@counter_function
def say_hello_func():
    print("  Hello from function decorator!")


say_hello_func()
say_hello_func()
say_hello_func()

# 方式 2: 类装饰器实现
print("\n【方式 2: 类装饰器】")


class CounterClass:
    """使用类实现的计数器装饰器"""

    def __init__(self, func):
        wraps(func)(self)
        self.func = func
        self.count = 0  # 实例属性，更清晰

    def __call__(self, *args, **kwargs):
        self.count += 1
        print(f"  [类装饰器] 第 {self.count} 次调用 {self.func.__name__}")
        return self.func(*args, **kwargs)

    def reset(self):
        """额外功能：重置计数"""
        self.count = 0
        print("  [类装饰器] 计数器已重置")

    def get_count(self):
        """额外功能：获取当前计数"""
        return self.count


@CounterClass
def say_hello_class():
    print("  Hello from class decorator!")


say_hello_class()
say_hello_class()
print(f"  当前调用次数: {say_hello_class.get_count()}")
say_hello_class.reset()
say_hello_class()

print("\n💡 对比总结:")
print("  函数装饰器: 简洁，但状态管理受限（需要 nonlocal）")
print("  类装饰器: 状态管理清晰，可以添加额外方法（reset, get_count）")


# ============================================================================
# 示例 2: 带参数的装饰器
# ============================================================================

print("\n" + "=" * 70)
print("示例 2: 带参数的装饰器 - 重复执行")
print("=" * 70)

# 方式 1: 函数装饰器（三层嵌套）
print("\n【方式 1: 函数装饰器 - 三层嵌套】")


def repeat_function(times):
    """外层：接收装饰器参数"""

    def decorator(func):
        """中层：接收被装饰的函数"""

        @wraps(func)
        def wrapper(*args, **kwargs):
            """内层：执行实际逻辑"""
            print(f"  [函数装饰器] 将重复执行 {times} 次")
            for i in range(times):
                print(f"    第 {i + 1} 次:", end=" ")
                result = func(*args, **kwargs)
            return result

        return wrapper

    return decorator


@repeat_function(times=3)
def print_message_func(msg):
    print(msg)


print_message_func("Hello!")

# 方式 2: 类装饰器
print("\n【方式 2: 类装饰器 - 更清晰的结构】")


class RepeatClass:
    """使用类实现的重复装饰器"""

    def __init__(self, times):
        """接收装饰器参数"""
        self.times = times

    def __call__(self, func):
        """接收被装饰的函数"""

        @wraps(func)
        def wrapper(*args, **kwargs):
            print(f"  [类装饰器] 将重复执行 {self.times} 次")
            for i in range(self.times):
                print(f"    第 {i + 1} 次:", end=" ")
                result = func(*args, **kwargs)
            return result

        return wrapper


@RepeatClass(times=3)
def print_message_class(msg):
    print(msg)


print_message_class("Hello!")

print("\n💡 对比总结:")
print("  函数装饰器: 三层嵌套，可能让人困惑")
print("  类装饰器: 结构更清晰，__init__ 接收参数，__call__ 接收函数")


# ============================================================================
# 示例 3: 复杂状态管理 - 性能监控
# ============================================================================

print("\n" + "=" * 70)
print("示例 3: 复杂状态管理 - 性能监控")
print("=" * 70)

# 方式 1: 函数装饰器（管理复杂状态较困难）
print("\n【方式 1: 函数装饰器 - 状态管理复杂】")


def timer_function(func):
    """函数装饰器：记录执行时间"""
    times = []  # 闭包变量

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        times.append(elapsed)

        print(f"  [函数装饰器] {func.__name__} 执行耗时: {elapsed:.4f}秒")
        print(f"  平均耗时: {sum(times) / len(times):.4f}秒")
        return result

    # 问题：难以提供 get_stats() 等方法
    return wrapper


@timer_function
def slow_task_func(n):
    time.sleep(n)
    return "Done"


slow_task_func(0.1)
slow_task_func(0.15)

# 方式 2: 类装饰器（状态管理更容易）
print("\n【方式 2: 类装饰器 - 状态管理清晰】")


class Timer:
    """类装饰器：记录和统计执行时间"""

    def __init__(self, func):
        wraps(func)(self)
        self.func = func
        self.times = []  # 实例属性
        self.total_calls = 0

    def __call__(self, *args, **kwargs):
        start = time.time()
        result = self.func(*args, **kwargs)
        elapsed = time.time() - start

        self.times.append(elapsed)
        self.total_calls += 1

        print(f"  [类装饰器] {self.func.__name__} 执行耗时: {elapsed:.4f}秒")
        print(f"  平均耗时: {self.avg_time:.4f}秒")
        return result

    @property
    def avg_time(self):
        """计算平均时间"""
        return sum(self.times) / len(self.times) if self.times else 0

    @property
    def min_time(self):
        """最短时间"""
        return min(self.times) if self.times else 0

    @property
    def max_time(self):
        """最长时间"""
        return max(self.times) if self.times else 0

    def get_report(self):
        """生成详细报告"""
        return {
            "function": self.func.__name__,
            "total_calls": self.total_calls,
            "avg_time": self.avg_time,
            "min_time": self.min_time,
            "max_time": self.max_time,
        }


@Timer
def slow_task_class(n):
    time.sleep(n)
    return "Done"


slow_task_class(0.1)
slow_task_class(0.15)
slow_task_class(0.12)

print("\n  详细统计报告:")
report = slow_task_class.get_report()
for key, value in report.items():
    if isinstance(value, float):
        print(f"    {key}: {value:.4f}")
    else:
        print(f"    {key}: {value}")

print("\n💡 对比总结:")
print("  函数装饰器: 管理多个状态变量困难，难以提供统计方法")
print("  类装饰器: 轻松管理状态，提供丰富的方法和属性")


# ============================================================================
# 示例 4: 缓存装饰器
# ============================================================================

print("\n" + "=" * 70)
print("示例 4: 缓存装饰器（记忆化）")
print("=" * 70)

# 方式 1: 函数装饰器
print("\n【方式 1: 函数装饰器】")


def memoize_function(func):
    """函数装饰器实现缓存"""
    cache = {}

    @wraps(func)
    def wrapper(n):
        if n in cache:
            print(f"  [函数装饰器] 从缓存获取 fibonacci({n})")
            return cache[n]

        print(f"  [函数装饰器] 计算 fibonacci({n})")
        result = func(n)
        cache[n] = result
        return result

    # 问题：无法清空缓存或查看缓存统计
    return wrapper


@memoize_function
def fibonacci_func(n):
    if n < 2:
        return n
    return fibonacci_func(n - 1) + fibonacci_func(n - 2)


print(f"结果: {fibonacci_func(5)}")
print(f"结果: {fibonacci_func(5)}")  # 第二次直接从缓存获取

# 方式 2: 类装饰器
print("\n【方式 2: 类装饰器】")


class Memoize:
    """类装饰器实现缓存"""

    def __init__(self, func):
        wraps(func)(self)
        self.func = func
        self.cache = {}
        self.hits = 0
        self.misses = 0

    def __call__(self, n):
        if n in self.cache:
            self.hits += 1
            print(f"  [类装饰器] 从缓存获取 fibonacci({n}) [命中率: {self.hit_rate:.1%}]")
            return self.cache[n]

        self.misses += 1
        print(f"  [类装饰器] 计算 fibonacci({n})")
        result = self.func(n)
        self.cache[n] = result
        return result

    @property
    def hit_rate(self):
        """计算缓存命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0

    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        print("  [类装饰器] 缓存已清空")

    def get_stats(self):
        """获取缓存统计"""
        return {
            "cache_size": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hit_rate,
        }


@Memoize
def fibonacci_class(n):
    if n < 2:
        return n
    return fibonacci_class(n - 1) + fibonacci_class(n - 2)


print(f"结果: {fibonacci_class(5)}")
print(f"结果: {fibonacci_class(5)}")  # 第二次直接从缓存获取
print(f"结果: {fibonacci_class(6)}")  # 利用已有缓存

print("\n  缓存统计:")
stats = fibonacci_class.get_stats()
for key, value in stats.items():
    if isinstance(value, float):
        print(f"    {key}: {value:.1%}")
    else:
        print(f"    {key}: {value}")

fibonacci_class.clear_cache()

print("\n💡 对比总结:")
print("  函数装饰器: 实现缓存简单，但缺少管理接口")
print("  类装饰器: 可以清空缓存、查看统计信息、计算命中率")


# ============================================================================
# 示例 5: 性能对比
# ============================================================================

print("\n" + "=" * 70)
print("示例 5: 性能对比")
print("=" * 70)

import timeit


# 函数装饰器
def simple_func_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


@simple_func_decorator
def test_func():
    return sum(range(100))


# 类装饰器
class SimpleClassDecorator:
    def __init__(self, func):
        wraps(func)(self)
        self.func = func

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


@SimpleClassDecorator
def test_class():
    return sum(range(100))


# 无装饰器
def test_plain():
    return sum(range(100))


iterations = 100000

time_func = timeit.timeit(lambda: test_func(), number=iterations)
time_class = timeit.timeit(lambda: test_class(), number=iterations)
time_plain = timeit.timeit(lambda: test_plain(), number=iterations)

print(f"\n  执行 {iterations:,} 次:")
print(f"    无装饰器:     {time_plain:.4f}秒 (基准)")
print(f"    函数装饰器:   {time_func:.4f}秒 (慢 {(time_func / time_plain - 1) * 100:.1f}%)")
print(f"    类装饰器:     {time_class:.4f}秒 (慢 {(time_class / time_plain - 1) * 100:.1f}%)")

print("\n💡 对比总结:")
print("  函数装饰器: 性能略优（无需实例化）")
print("  类装饰器: 性能略差（需要实例化和查找 __call__）")
print("  差异很小，通常可以忽略，应根据需求选择")


# ============================================================================
# 总结
# ============================================================================

print("\n" + "=" * 70)
print("总结：何时使用哪种装饰器？")
print("=" * 70)

print("""
【使用函数装饰器的场景】
  ✅ 简单的功能增强（日志、计时、调试）
  ✅ 不需要保存复杂状态
  ✅ 不需要提供额外的方法
  ✅ 追求最佳性能
  ✅ 代码简洁性优先

【使用类装饰器的场景】
  ✅ 需要管理复杂状态
  ✅ 需要提供额外的方法（reset、get_stats 等）
  ✅ 装饰器逻辑复杂
  ✅ 需要良好的代码组织
  ✅ 需要继承或扩展装饰器

【核心区别】
  函数装饰器：简洁、高效、函数式风格
  类装饰器：  强大、灵活、面向对象风格

【选择原则】
  简单任务 → 函数装饰器
  复杂任务 → 类装饰器
  不确定时 → 从函数装饰器开始，需要时重构为类装饰器
""")

print("=" * 70)
print("示例演示完毕！")
print("=" * 70)
