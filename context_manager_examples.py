#!/usr/bin/env python3
"""
Python 上下文管理器完整示例
包含：基础用法、__enter__ 和 __exit__ 详解、实用场景
"""

import os
import sys
import time
from contextlib import ExitStack, closing, contextmanager, redirect_stdout, suppress

# ========================================
# 1. 基础上下文管理器
# ========================================

print("=" * 70)
print("1. 基础上下文管理器")
print("=" * 70)


class SimpleContextManager:
    """最简单的上下文管理器"""

    def __enter__(self):
        """进入上下文时调用"""
        print("  [__enter__] 进入上下文")
        return self  # 返回值会赋给 as 后的变量

    def __exit__(self, exc_type, exc_value, traceback):
        """退出上下文时调用

        参数：
            exc_type: 异常类型（如果发生异常）
            exc_value: 异常值（如果发生异常）
            traceback: 异常追踪信息（如果发生异常）

        返回值：
            True: 抑制异常（不会向外传播）
            False/None: 不抑制异常（异常会继续传播）
        """
        print("  [__exit__] 退出上下文")
        if exc_type is not None:
            print(f"  [__exit__] 捕获到异常: {exc_type.__name__}: {exc_value}")
        return False  # 不抑制异常


print("\n【正常情况】")
with SimpleContextManager() as cm:
    print("  [with block] 在上下文中执行代码")

print("\n【异常情况】")
try:
    with SimpleContextManager() as cm:
        print("  [with block] 抛出异常")
        raise ValueError("测试异常")
except ValueError as e:
    print(f"  [外部] 捕获异常: {e}")


# ========================================
# 2. 文件操作上下文管理器
# ========================================

print("\n" + "=" * 70)
print("2. 文件操作上下文管理器")
print("=" * 70)


class FileManager:
    """文件操作的上下文管理器"""

    def __init__(self, filename, mode="r"):
        self.filename = filename
        self.mode = mode
        self.file = None

    def __enter__(self):
        """打开文件"""
        print(f"  [__enter__] 打开文件: {self.filename}")
        self.file = open(self.filename, self.mode)
        return self.file  # 返回文件对象

    def __exit__(self, exc_type, exc_value, traceback):
        """关闭文件"""
        if self.file:
            print(f"  [__exit__] 关闭文件: {self.filename}")
            self.file.close()
        return False


# 创建测试文件
test_file = "/tmp/test_context.txt"
with open(test_file, "w") as f:
    f.write("Hello, Context Manager!\n")

print("\n【使用自定义文件管理器】")
with FileManager(test_file, "r") as f:
    content = f.read()
    print(f"  [with block] 文件内容: {content.strip()}")

print("\n💡 对比内置 open():")
print("  内置的 open() 也是上下文管理器，会自动关闭文件")


# ========================================
# 3. 数据库连接管理器
# ========================================

print("\n" + "=" * 70)
print("3. 数据库连接管理器（模拟）")
print("=" * 70)


class DatabaseConnection:
    """数据库连接的上下文管理器"""

    def __init__(self, host, port, database):
        self.host = host
        self.port = port
        self.database = database
        self.connection = None

    def __enter__(self):
        """建立数据库连接"""
        print(f"  [__enter__] 连接数据库: {self.database}@{self.host}:{self.port}")
        # 模拟建立连接
        self.connection = {"host": self.host, "connected": True, "database": self.database}
        return self.connection

    def __exit__(self, exc_type, exc_value, traceback):
        """关闭数据库连接"""
        if self.connection:
            print("  [__exit__] 关闭数据库连接")
            self.connection["connected"] = False

        # 如果发生异常，回滚事务
        if exc_type is not None:
            print("  [__exit__] 发生异常，回滚事务")

        return False


print("\n【使用数据库连接管理器】")
with DatabaseConnection("localhost", 3306, "testdb") as conn:
    print(f"  [with block] 执行数据库操作，连接状态: {conn['connected']}")
    print(f"  [with block] 数据库: {conn['database']}")


# ========================================
# 4. 计时器上下文管理器
# ========================================

print("\n" + "=" * 70)
print("4. 计时器上下文管理器")
print("=" * 70)


class Timer:
    """计时器上下文管理器"""

    def __init__(self, name="操作"):
        self.name = name
        self.start_time = None
        self.elapsed = None

    def __enter__(self):
        """开始计时"""
        print(f"  [__enter__] 开始计时: {self.name}")
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """结束计时"""
        self.elapsed = time.time() - self.start_time
        print(f"  [__exit__] {self.name} 耗时: {self.elapsed:.4f}秒")
        return False


print("\n【使用计时器】")
with Timer("数据处理") as timer:
    print("  [with block] 执行耗时操作...")
    time.sleep(0.1)
    sum([i**2 for i in range(1000)])

print(f"  可以在外部访问耗时: {timer.elapsed:.4f}秒")


# ========================================
# 5. 临时改变状态的上下文管理器
# ========================================

print("\n" + "=" * 70)
print("5. 临时改变状态的上下文管理器")
print("=" * 70)


class TemporaryDirectory:
    """临时改变工作目录"""

    def __init__(self, new_dir):
        self.new_dir = new_dir
        self.old_dir = None

    def __enter__(self):
        """保存当前目录，切换到新目录"""
        self.old_dir = os.getcwd()
        print(f"  [__enter__] 当前目录: {self.old_dir}")
        print(f"  [__enter__] 切换到: {self.new_dir}")
        if os.path.exists(self.new_dir):
            os.chdir(self.new_dir)
        return self.new_dir

    def __exit__(self, exc_type, exc_value, traceback):
        """恢复原来的目录"""
        print(f"  [__exit__] 恢复目录: {self.old_dir}")
        os.chdir(self.old_dir)
        return False


print("\n【临时切换目录】")
print(f"原始目录: {os.getcwd()}")
with TemporaryDirectory("/tmp"):
    print(f"  [with block] 当前目录: {os.getcwd()}")
print(f"恢复后目录: {os.getcwd()}")


# ========================================
# 6. 异常处理和抑制
# ========================================

print("\n" + "=" * 70)
print("6. 异常处理和抑制")
print("=" * 70)


class SuppressException:
    """抑制特定异常的上下文管理器"""

    def __init__(self, *exception_types):
        self.exception_types = exception_types

    def __enter__(self):
        print(f"  [__enter__] 将抑制异常: {[e.__name__ for e in self.exception_types]}")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """抑制指定类型的异常"""
        if exc_type is not None:
            print(f"  [__exit__] 捕获到异常: {exc_type.__name__}")

            if issubclass(exc_type, self.exception_types):
                print(f"  [__exit__] 抑制异常: {exc_type.__name__}")
                return True  # 返回 True 抑制异常

        return False  # 不抑制其他异常


print("\n【抑制 ValueError】")
with SuppressException(ValueError, TypeError):
    print("  [with block] 抛出 ValueError")
    raise ValueError("这个异常会被抑制")
print("  [外部] 继续执行，异常已被抑制")

print("\n【不抑制 RuntimeError】")
try:
    with SuppressException(ValueError, TypeError):
        print("  [with block] 抛出 RuntimeError")
        raise RuntimeError("这个异常不会被抑制")
except RuntimeError as e:
    print(f"  [外部] 捕获到: {e}")


# ========================================
# 7. 资源锁管理器
# ========================================

print("\n" + "=" * 70)
print("7. 资源锁管理器")
print("=" * 70)


class Lock:
    """简单的锁管理器"""

    def __init__(self, name):
        self.name = name
        self.locked = False

    def __enter__(self):
        """获取锁"""
        print(f"  [__enter__] 获取锁: {self.name}")
        self.locked = True
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """释放锁"""
        print(f"  [__exit__] 释放锁: {self.name}")
        self.locked = False
        return False


print("\n【使用锁】")
with Lock("数据库锁") as lock:
    print(f"  [with block] 锁状态: {lock.locked}")
    print("  [with block] 执行临界区代码")
print(f"  [外部] 锁状态: {lock.locked}")


# ========================================
# 8. 使用 @contextmanager 装饰器
# ========================================

print("\n" + "=" * 70)
print("8. 使用 @contextmanager 装饰器")
print("=" * 70)


@contextmanager
def simple_context_manager():
    """使用装饰器创建上下文管理器"""
    print("  [yield before] 进入上下文（相当于 __enter__）")

    try:
        yield "返回值"  # yield 的值会赋给 as 后的变量
    finally:
        print("  [yield after] 退出上下文（相当于 __exit__）")


print("\n【使用 @contextmanager】")
with simple_context_manager() as value:
    print(f"  [with block] 接收到的值: {value}")


@contextmanager
def timer_context(name):
    """计时器的装饰器版本"""
    print(f"  [yield before] 开始计时: {name}")
    start = time.time()

    try:
        yield
    finally:
        elapsed = time.time() - start
        print(f"  [yield after] {name} 耗时: {elapsed:.4f}秒")


print("\n【使用装饰器版本的计时器】")
with timer_context("快速操作"):
    time.sleep(0.05)


# ========================================
# 9. 嵌套上下文管理器
# ========================================

print("\n" + "=" * 70)
print("9. 嵌套上下文管理器")
print("=" * 70)

print("\n【方式1: 嵌套 with 语句】")
with Timer("外层操作"):
    with Timer("内层操作"):
        print("  [with block] 执行代码")
        time.sleep(0.05)

print("\n【方式2: 使用逗号分隔（推荐）】")
with Timer("操作1"), Timer("操作2"):
    print("  [with block] 同时使用多个上下文管理器")
    time.sleep(0.05)


# ========================================
# 10. ExitStack：动态管理上下文
# ========================================

print("\n" + "=" * 70)
print("10. ExitStack：动态管理上下文")
print("=" * 70)


@contextmanager
def managed_resource(name):
    """模拟资源管理"""
    print(f"  [enter] 获取资源: {name}")
    try:
        yield name
    finally:
        print(f"  [exit] 释放资源: {name}")


print("\n【使用 ExitStack 动态管理多个上下文】")
with ExitStack() as stack:
    resources = []

    # 动态添加上下文管理器
    for i in range(3):
        resource = stack.enter_context(managed_resource(f"资源{i}"))
        resources.append(resource)

    print(f"  [with block] 已获取的资源: {resources}")
    print("  [with block] 执行操作...")

print("  [外部] 所有资源已自动释放")


# ========================================
# 11. 实用场景：临时修改对象属性
# ========================================

print("\n" + "=" * 70)
print("11. 实用场景：临时修改对象属性")
print("=" * 70)


class TemporaryAttribute:
    """临时修改对象属性"""

    def __init__(self, obj, attr, value):
        self.obj = obj
        self.attr = attr
        self.new_value = value
        self.old_value = None

    def __enter__(self):
        """保存旧值，设置新值"""
        self.old_value = getattr(self.obj, self.attr)
        print(f"  [__enter__] 保存属性 {self.attr}: {self.old_value}")
        print(f"  [__enter__] 设置新值: {self.new_value}")
        setattr(self.obj, self.attr, self.new_value)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """恢复旧值"""
        print(f"  [__exit__] 恢复属性 {self.attr}: {self.old_value}")
        setattr(self.obj, self.attr, self.old_value)
        return False


class Config:
    debug = False
    timeout = 30


config = Config()
print(f"\n原始配置: debug={config.debug}, timeout={config.timeout}")

with TemporaryAttribute(config, "debug", True):
    print(f"  [with block] 临时配置: debug={config.debug}")

print(f"恢复配置: debug={config.debug}, timeout={config.timeout}")


# ========================================
# 12. 实用场景：重定向输出
# ========================================

print("\n" + "=" * 70)
print("12. 实用场景：重定向输出")
print("=" * 70)


class RedirectOutput:
    """重定向标准输出到文件"""

    def __init__(self, filename):
        self.filename = filename
        self.file = None
        self.old_stdout = None

    def __enter__(self):
        """保存旧的 stdout，打开文件并重定向"""
        print(f"  [__enter__] 重定向输出到: {self.filename}")
        self.file = open(self.filename, "w")
        self.old_stdout = sys.stdout
        sys.stdout = self.file
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """恢复 stdout，关闭文件"""
        sys.stdout = self.old_stdout
        if self.file:
            self.file.close()
        print("  [__exit__] 恢复标准输出")
        return False


output_file = "/tmp/redirected_output.txt"
print("\n【重定向输出】")

with RedirectOutput(output_file):
    # 这些输出会写入文件
    print("这行会写入文件")
    print("这行也会写入文件")

print("这行会输出到控制台")

# 读取文件内容
with open(output_file) as f:
    print(f"文件内容:\n{f.read()}")


# ========================================
# 13. contextlib 标准库工具
# ========================================

print("\n" + "=" * 70)
print("13. contextlib 标准库工具")
print("=" * 70)

print("\n【suppress - 抑制异常】")

# 抑制 FileNotFoundError
with suppress(FileNotFoundError):
    os.remove("/tmp/不存在的文件.txt")
    print("  这行不会执行")
print("  异常被抑制，继续执行")

print("\n【redirect_stdout - 重定向标准输出】")
from io import StringIO

output = StringIO()
with redirect_stdout(output):
    print("重定向的内容")
    print("第二行")

print(f"捕获的输出: {output.getvalue()}")

print("\n【closing - 确保对象关闭】")


# closing 确保对象的 close() 方法被调用
class Resource:
    def close(self):
        print("  资源已关闭")


with closing(Resource()) as r:
    print("  使用资源")


# ========================================
# 14. __exit__ 返回值详解
# ========================================

print("\n" + "=" * 70)
print("14. __exit__ 返回值详解")
print("=" * 70)


class ExitReturnTrue:
    """__exit__ 返回 True：抑制异常"""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        print(f"  [__exit__] 捕获异常: {exc_type}")
        return True  # 抑制异常


class ExitReturnFalse:
    """__exit__ 返回 False：不抑制异常"""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        print(f"  [__exit__] 捕获异常: {exc_type}")
        return False  # 不抑制异常


print("\n【返回 True - 抑制异常】")
with ExitReturnTrue():
    print("  抛出异常")
    raise ValueError("测试")
print("  异常被抑制，继续执行")

print("\n【返回 False - 不抑制异常】")
try:
    with ExitReturnFalse():
        print("  抛出异常")
        raise ValueError("测试")
except ValueError as e:
    print(f"  外部捕获异常: {e}")


# ========================================
# 15. 高级示例：事务管理器
# ========================================

print("\n" + "=" * 70)
print("15. 高级示例：事务管理器")
print("=" * 70)


class Transaction:
    """事务管理器：支持提交和回滚"""

    def __init__(self, name):
        self.name = name
        self.operations = []

    def __enter__(self):
        """开始事务"""
        print(f"  [__enter__] 开始事务: {self.name}")
        return self

    def add_operation(self, operation):
        """添加操作"""
        self.operations.append(operation)
        print(f"    添加操作: {operation}")

    def __exit__(self, exc_type, exc_value, traceback):
        """结束事务：提交或回滚"""
        if exc_type is None:
            # 没有异常，提交事务
            print(f"  [__exit__] 提交事务: {self.name}")
            print(f"    执行 {len(self.operations)} 个操作")
        else:
            # 发生异常，回滚事务
            print(f"  [__exit__] 回滚事务: {self.name}")
            print(f"    撤销 {len(self.operations)} 个操作")

        return False  # 不抑制异常


print("\n【成功的事务】")
with Transaction("用户注册") as tx:
    tx.add_operation("创建用户记录")
    tx.add_operation("发送欢迎邮件")
    tx.add_operation("初始化用户配置")

print("\n【失败的事务】")
try:
    with Transaction("订单处理") as tx:
        tx.add_operation("扣减库存")
        tx.add_operation("创建订单")
        raise ValueError("支付失败")
        tx.add_operation("发送确认邮件")  # 不会执行
except ValueError as e:
    print(f"  [外部] 处理异常: {e}")


# ========================================
# 总结
# ========================================

print("\n" + "=" * 70)
print("总结")
print("=" * 70)

print("""
【上下文管理器的核心概念】
1. __enter__: 进入上下文时调用，返回值赋给 as 后的变量
2. __exit__: 退出上下文时调用，接收异常信息，返回 True 抑制异常

【__exit__ 参数】
- exc_type: 异常类型（无异常时为 None）
- exc_value: 异常实例（无异常时为 None）
- traceback: 异常追踪（无异常时为 None）

【__exit__ 返回值】
- True: 抑制异常，不向外传播
- False/None: 不抑制异常，继续传播

【常见使用场景】
1. 资源管理（文件、数据库连接、网络连接）
2. 状态临时修改（配置、环境变量、工作目录）
3. 异常处理和抑制
4. 性能监控（计时、分析）
5. 事务管理（数据库、分布式系统）

【创建上下文管理器的两种方式】
1. 类方式：实现 __enter__ 和 __exit__ 方法
2. 装饰器方式：使用 @contextmanager 装饰生成器函数

【最佳实践】
✅ 总是在 __exit__ 中释放资源
✅ 使用 try-finally 确保清理代码执行
✅ 谨慎使用返回 True 抑制异常
✅ 优先使用 contextlib 标准库工具
""")

print("=" * 70)
print("所有示例演示完成！")
print("=" * 70)
