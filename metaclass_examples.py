"""
Python 元类编程完整示例
======================

本文件包含元类编程的所有核心概念和实战示例：
1. __new__ vs __init__ 详细对比
2. 元类基础
3. 元类的实际应用
4. 高级元类技巧
"""

import time

print("=" * 80)
print("示例 1: __new__ 和 __init__ 的根本区别")
print("=" * 80)


class NewInitDemo:
    """
    __new__  : 负责创建实例（构造器）- 类方法
    __init__ : 负责初始化实例（初始化器）- 实例方法

    调用顺序：__new__ 先于 __init__
    """

    def __new__(cls, name: str):
        """
        __new__ 是真正的构造器
        - 第一个参数是 cls（类本身）
        - 必须返回一个实例
        - 在实例创建之前被调用
        """
        print(f"1. __new__ 被调用: cls={cls}")
        print("   - 此时还没有 self，我们正在创建实例")

        # 调用父类的 __new__ 创建实例
        instance = super().__new__(cls)
        print(f"   - 实例已创建: {instance}")

        # 可以在这里给实例添加属性（但通常不这么做）
        instance._created_at = time.time()

        return instance  # 必须返回实例

    def __init__(self, name: str):
        """
        __init__ 是初始化器
        - 第一个参数是 self（已经创建好的实例）
        - 不需要返回值（返回 None）
        - 在实例创建之后被调用
        """
        print(f"2. __init__ 被调用: self={self}")
        print("   - 实例已经存在，现在初始化它")

        self.name = name
        self._initialized_at = time.time()

        print(f"   - 初始化完成: name={self.name}")


print("\n创建 NewInitDemo 实例：")
obj = NewInitDemo("测试对象")
print(f"\n最终对象: {obj}")
print(f"对象属性: name={obj.name}")
print(f"创建时间戳: {obj._created_at}")
print(f"初始化时间戳: {obj._initialized_at}")


print("\n" + "=" * 80)
print("示例 2: __new__ 的实际用途 - 单例模式")
print("=" * 80)


class Singleton:
    """
    使用 __new__ 实现单例模式
    确保一个类只有一个实例
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        print("__new__ 被调用")

        if cls._instance is None:
            print("  - 首次创建实例")
            cls._instance = super().__new__(cls)
        else:
            print("  - 返回已存在的实例")

        return cls._instance

    def __init__(self, value: str):
        print(f"__init__ 被调用: value={value}")
        # 注意：每次调用都会重新初始化
        self.value = value


print("\n第一次创建 Singleton：")
s1 = Singleton("第一个值")
print(f"s1.value = {s1.value}, id = {id(s1)}")

print("\n第二次创建 Singleton：")
s2 = Singleton("第二个值")
print(f"s2.value = {s2.value}, id = {id(s2)}")

print(f"\ns1 is s2: {s1 is s2}")
print(f"注意：s1.value 也变成了 '{s1.value}'（因为 __init__ 每次都会被调用）")


print("\n" + "=" * 80)
print("示例 3: __new__ 的实际用途 - 不可变类型的子类化")
print("=" * 80)


class PositiveInteger(int):
    """
    继承 int 并确保值始终为正数
    必须使用 __new__，因为 int 是不可变类型
    """

    def __new__(cls, value):
        if value < 0:
            value = abs(value)
            print(f"  - 负数已转换为正数: {value}")

        # 对于不可变类型，必须在 __new__ 中设置值
        instance = super().__new__(cls, value)
        return instance


print("\n创建正整数：")
p1 = PositiveInteger(42)
print(f"p1 = {p1}, type = {type(p1)}")

p2 = PositiveInteger(-10)
print(f"p2 = {p2}, type = {type(p2)}")


print("\n" + "=" * 80)
print("示例 4: 元类基础 - 类也是对象")
print("=" * 80)

print("\n在 Python 中，一切皆对象，包括类本身：")


class MyClass:
    pass


obj = MyClass()

print(f"obj 是 MyClass 的实例: {isinstance(obj, MyClass)}")
print(f"MyClass 是 type 的实例: {isinstance(MyClass, type)}")
print(f"obj 的类型是: {type(obj)}")
print(f"MyClass 的类型是: {type(MyClass)}")

print("\n类的创建过程：")
print("  MyClass = type(name, bases, attrs)")
print("  相当于：")

# 使用 type() 动态创建类
MyClass2 = type(
    "MyClass2",  # 类名
    (),  # 父类元组
    {"x": 42, "greet": lambda self: f"Hello from {self}"},  # 类属性
)

obj2 = MyClass2()
print(f"  obj2.x = {obj2.x}")
print(f"  obj2.greet() = {obj2.greet()}")


print("\n" + "=" * 80)
print("示例 5: 第一个元类 - 基础元类")
print("=" * 80)


class FirstMeta(type):
    """
    元类继承自 type
    元类的 __new__ 方法用于创建类（不是实例）
    """

    def __new__(mcs, name, bases, attrs):
        """
        mcs: 元类本身（metaclass）
        name: 要创建的类的名字
        bases: 要创建的类的父类元组
        attrs: 要创建的类的属性字典
        """
        print("\n元类 __new__ 被调用：")
        print(f"  - 正在创建类: {name}")
        print(f"  - 父类: {bases}")
        print(f"  - 属性: {list(attrs.keys())}")

        # 修改类的属性
        attrs["created_by"] = "FirstMeta"
        attrs["creation_time"] = time.time()

        # 调用 type 的 __new__ 创建类
        new_class = super().__new__(mcs, name, bases, attrs)

        print(f"  - 类创建完成: {new_class}")
        return new_class


# 使用元类创建类
print("\n使用 FirstMeta 创建类：")


class MyModel(metaclass=FirstMeta):
    """使用 FirstMeta 作为元类"""

    x = 10

    def method(self):
        return "Hello"


print(f"\nMyModel 的类型: {type(MyModel)}")
print(f"MyModel.created_by: {MyModel.created_by}")
print(f"MyModel.creation_time: {MyModel.creation_time}")

print("\n创建 MyModel 的实例：")
obj = MyModel()
print(f"obj.x = {obj.x}")
print(f"obj.created_by = {obj.created_by}")


print("\n" + "=" * 80)
print("示例 6: 元类的 __init__ 方法")
print("=" * 80)


class MetaWithInit(type):
    """
    元类也有 __init__ 方法
    用于在类创建后进行额外的初始化
    """

    def __new__(mcs, name, bases, attrs):
        print(f"元类 __new__: 创建类 {name}")
        return super().__new__(mcs, name, bases, attrs)

    def __init__(cls, name, bases, attrs):
        """
        cls: 新创建的类
        在类创建完成后被调用
        """
        print(f"元类 __init__: 初始化类 {name}")
        super().__init__(name, bases, attrs)

        # 可以在这里做一些初始化工作
        cls._registry = []
        cls._initialized = True

        print(f"  - 为类 {name} 添加了 _registry 和 _initialized 属性")


print("\n使用 MetaWithInit 创建类：")


class Product(metaclass=MetaWithInit):
    pass


print(f"\nProduct._initialized: {Product._initialized}")
print(f"Product._registry: {Product._registry}")


print("\n" + "=" * 80)
print("示例 7: 实战 - 自动注册子类")
print("=" * 80)


class PluginMeta(type):
    """
    自动注册所有插件子类的元类
    """

    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)

        # 在基类上创建注册表
        if not hasattr(cls, "registry"):
            cls.registry = {}
        else:
            # 自动注册子类
            plugin_name = attrs.get("name", name)
            cls.registry[plugin_name] = cls
            print(f"  - 已注册插件: {plugin_name} -> {cls}")


class Plugin(metaclass=PluginMeta):
    """插件基类"""

    @classmethod
    def get_plugin(cls, name: str):
        """根据名字获取插件类"""
        return cls.registry.get(name)

    @classmethod
    def list_plugins(cls):
        """列出所有插件"""
        return list(cls.registry.keys())


print("\n创建插件子类：")


class EmailPlugin(Plugin):
    name = "email"

    def send(self, message):
        return f"通过邮件发送: {message}"


class SMSPlugin(Plugin):
    name = "sms"

    def send(self, message):
        return f"通过短信发送: {message}"


class WeChatPlugin(Plugin):
    name = "wechat"

    def send(self, message):
        return f"通过微信发送: {message}"


print(f"\n所有已注册的插件: {Plugin.list_plugins()}")

print("\n使用插件：")
email = Plugin.get_plugin("email")()
print(email.send("Hello"))

sms = Plugin.get_plugin("sms")()
print(sms.send("Hello"))


print("\n" + "=" * 80)
print("示例 8: 实战 - 自动添加属性验证")
print("=" * 80)


class ValidatedMeta(type):
    """
    自动为所有属性添加类型验证的元类
    """

    def __new__(mcs, name, bases, attrs):
        # 查找所有带类型注解的属性
        annotations = attrs.get("__annotations__", {})

        for attr_name, attr_type in annotations.items():
            # 创建验证属性
            storage_name = f"_{attr_name}"

            # 创建 property
            def make_property(name, typ):
                def getter(self):
                    return getattr(self, f"_{name}")

                def setter(self, value):
                    if not isinstance(value, typ):
                        raise TypeError(f"{name} 必须是 {typ.__name__} 类型，但得到了 {type(value).__name__}")
                    setattr(self, f"_{name}", value)

                return property(getter, setter)

            attrs[attr_name] = make_property(attr_name, attr_type)

        return super().__new__(mcs, name, bases, attrs)


class Person(metaclass=ValidatedMeta):
    """使用类型验证的 Person 类"""

    name: str
    age: int

    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age

    def __repr__(self):
        return f"Person(name={self.name!r}, age={self.age})"


print("\n创建有效的 Person 对象：")
p1 = Person("张三", 25)
print(p1)

print("\n尝试设置错误类型：")
try:
    p1.age = "30"  # 应该是 int，不是 str
except TypeError as e:
    print(f"捕获到类型错误: {e}")

print("\n尝试创建时传入错误类型：")
try:
    p2 = Person("李四", "25")
except TypeError as e:
    print(f"捕获到类型错误: {e}")


print("\n" + "=" * 80)
print("示例 9: 实战 - ORM 风格的模型类")
print("=" * 80)


class Field:
    """字段描述符"""

    def __init__(self, field_type, default=None):
        self.field_type = field_type
        self.default = default
        self.name = None  # 将在元类中设置

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.__dict__.get(self.name, self.default)

    def __set__(self, instance, value):
        if not isinstance(value, self.field_type):
            raise TypeError(f"{self.name} 必须是 {self.field_type.__name__} 类型")
        instance.__dict__[self.name] = value

    def __repr__(self):
        return f"Field({self.field_type.__name__})"


class ModelMeta(type):
    """ORM 模型的元类"""

    def __new__(mcs, name, bases, attrs):
        # 收集所有字段
        fields = {}

        for key, value in list(attrs.items()):
            if isinstance(value, Field):
                fields[key] = value
                value.name = key  # 设置字段名

        # 添加字段字典到类
        attrs["_fields"] = fields

        # 创建类
        cls = super().__new__(mcs, name, bases, attrs)

        print(f"创建模型类 {name}，字段: {list(fields.keys())}")

        return cls


class Model(metaclass=ModelMeta):
    """ORM 模型基类"""

    def __init__(self, **kwargs):
        for name, field in self._fields.items():
            value = kwargs.get(name, field.default)
            setattr(self, name, value)

    def to_dict(self):
        """转换为字典"""
        return {name: getattr(self, name) for name in self._fields.keys()}

    def __repr__(self):
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.to_dict().items())
        return f"{self.__class__.__name__}({attrs})"


print("\n定义 User 模型：")


class User(Model):
    name = Field(str, default="")
    age = Field(int, default=0)
    email = Field(str, default="")


print("\n创建 User 实例：")
user1 = User(name="张三", age=25, email="zhangsan@example.com")
print(user1)
print(f"转换为字典: {user1.to_dict()}")

user2 = User(name="李四")
print(user2)


print("\n" + "=" * 80)
print("示例 10: __call__ 方法 - 控制实例创建")
print("=" * 80)


class SingletonMeta(type):
    """
    更好的单例元类实现
    使用 __call__ 方法控制实例创建
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        """
        当调用类创建实例时，__call__ 会被调用
        即：MyClass() 会调用 type.__call__()
        """
        print(f"\n元类 __call__ 被调用: 创建 {cls.__name__} 的实例")

        if cls not in cls._instances:
            print("  - 首次创建，调用 __new__ 和 __init__")
            # 调用 type 的 __call__，这会依次调用 __new__ 和 __init__
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        else:
            print("  - 返回缓存的实例")

        return cls._instances[cls]


class Database(metaclass=SingletonMeta):
    """数据库连接类（单例）"""

    def __init__(self, host: str):
        print(f"  Database.__init__ 被调用: host={host}")
        self.host = host
        self.connections = []

    def connect(self):
        self.connections.append(f"连接到 {self.host}")
        return f"已连接到 {self.host}"


print("\n第一次创建 Database：")
db1 = Database("localhost")
print(f"db1.host = {db1.host}")

print("\n第二次创建 Database（使用不同参数）：")
db2 = Database("192.168.1.1")
print(f"db2.host = {db2.host}")
print("注意：__init__ 不会被调用第二次")

print(f"\ndb1 is db2: {db1 is db2}")


print("\n" + "=" * 80)
print("示例 11: 元类的继承")
print("=" * 80)


class BaseMeta(type):
    """基础元类"""

    def __new__(mcs, name, bases, attrs):
        print(f"BaseMeta.__new__: 创建 {name}")
        attrs["from_base_meta"] = True
        return super().__new__(mcs, name, bases, attrs)


class ExtendedMeta(BaseMeta):
    """扩展元类"""

    def __new__(mcs, name, bases, attrs):
        print(f"ExtendedMeta.__new__: 创建 {name}")
        attrs["from_extended_meta"] = True
        # 调用父元类的 __new__
        return super().__new__(mcs, name, bases, attrs)


print("\n使用 ExtendedMeta：")


class MyClass(metaclass=ExtendedMeta):
    pass


print(f"\nMyClass.from_base_meta: {MyClass.from_base_meta}")
print(f"MyClass.from_extended_meta: {MyClass.from_extended_meta}")


print("\n" + "=" * 80)
print("示例 12: 实战 - 自动添加方法")
print("=" * 80)


class AutoMethodMeta(type):
    """
    自动为类添加常用方法的元类
    """

    def __new__(mcs, name, bases, attrs):
        # 如果类中没有定义 __repr__，自动添加
        if "__repr__" not in attrs:

            def auto_repr(self):
                class_name = self.__class__.__name__
                attrs_str = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items() if not k.startswith("_"))
                return f"{class_name}({attrs_str})"

            attrs["__repr__"] = auto_repr
            print(f"为 {name} 自动添加了 __repr__ 方法")

        # 如果类中没有定义 __eq__，自动添加
        if "__eq__" not in attrs:

            def auto_eq(self, other):
                if not isinstance(other, self.__class__):
                    return False
                return self.__dict__ == other.__dict__

            attrs["__eq__"] = auto_eq
            print(f"为 {name} 自动添加了 __eq__ 方法")

        return super().__new__(mcs, name, bases, attrs)


print("\n创建使用 AutoMethodMeta 的类：")


class Point(metaclass=AutoMethodMeta):
    def __init__(self, x, y):
        self.x = x
        self.y = y


print("\n测试自动添加的方法：")
p1 = Point(3, 4)
p2 = Point(3, 4)
p3 = Point(5, 6)

print(f"p1 = {p1}")  # 使用自动添加的 __repr__
print(f"p1 == p2: {p1 == p2}")  # 使用自动添加的 __eq__
print(f"p1 == p3: {p1 == p3}")


print("\n" + "=" * 80)
print("示例 13: __prepare__ 方法 - 自定义命名空间")
print("=" * 80)

from collections import OrderedDict


class OrderedMeta(type):
    """
    保持类属性定义顺序的元类
    """

    @classmethod
    def __prepare__(mcs, name, bases):
        """
        __prepare__ 在 __new__ 之前被调用
        返回一个用于存储类属性的字典
        """
        print(f"__prepare__ 被调用: 为类 {name} 准备命名空间")
        # 返回 OrderedDict 而不是普通 dict
        return OrderedDict()

    def __new__(mcs, name, bases, attrs):
        print(f"__new__ 被调用: attrs 类型为 {type(attrs)}")
        print(f"属性顺序: {list(attrs.keys())}")

        # 保存属性顺序
        attrs["_field_order"] = [k for k in attrs.keys() if not k.startswith("_") and not callable(attrs[k])]

        return super().__new__(mcs, name, bases, dict(attrs))


print("\n使用 OrderedMeta：")


class Student(metaclass=OrderedMeta):
    name = None
    age = None
    grade = None
    email = None

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


print(f"\nStudent._field_order: {Student._field_order}")


print("\n" + "=" * 80)
print("示例 14: 元类 vs 类装饰器")
print("=" * 80)

print("\n使用元类：")


class MetaApproach(type):
    def __new__(mcs, name, bases, attrs):
        attrs["approach"] = "metaclass"
        return super().__new__(mcs, name, bases, attrs)


class ClassA(metaclass=MetaApproach):
    pass


print(f"ClassA.approach = {ClassA.approach}")


print("\n使用类装饰器：")


def decorator_approach(cls):
    cls.approach = "decorator"
    return cls


@decorator_approach
class ClassB:
    pass


print(f"ClassB.approach = {ClassB.approach}")


print("\n区别：")
print("1. 元类会影响所有子类，装饰器只影响被装饰的类")
print("2. 元类在类创建时执行，装饰器在类定义完成后执行")
print("3. 元类可以控制类的创建过程，装饰器只能修改已创建的类")


print("\n" + "=" * 80)
print("示例 15: 完整示例 - 声明式 API 框架")
print("=" * 80)


class APIEndpoint:
    """API 端点描述符"""

    def __init__(self, method: str, path: str):
        self.method = method
        self.path = path
        self.handler = None

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return self.handler

    def __call__(self, handler):
        """作为装饰器使用"""
        self.handler = handler
        return self


class APIMeta(type):
    """API 类的元类"""

    def __new__(mcs, name, bases, attrs):
        # 收集所有端点
        endpoints = {}

        for key, value in attrs.items():
            if isinstance(value, APIEndpoint):
                endpoints[key] = value

        attrs["_endpoints"] = endpoints

        cls = super().__new__(mcs, name, bases, attrs)

        print(f"\n创建 API 类: {name}")
        for ep_name, ep in endpoints.items():
            print(f"  - {ep.method} {ep.path} -> {ep_name}")

        return cls


class API(metaclass=APIMeta):
    """API 基类"""

    @classmethod
    def route_info(cls):
        """获取所有路由信息"""
        return [f"{ep.method} {ep.path} -> {name}" for name, ep in cls._endpoints.items()]


print("\n定义 UserAPI：")


class UserAPI(API):
    # 声明式定义 API 端点
    get_users = APIEndpoint("GET", "/users")
    create_user = APIEndpoint("POST", "/users")
    get_user = APIEndpoint("GET", "/users/<id>")
    update_user = APIEndpoint("PUT", "/users/<id>")
    delete_user = APIEndpoint("DELETE", "/users/<id>")


print("\n路由信息：")
for route in UserAPI.route_info():
    print(f"  {route}")


print("\n" + "=" * 80)
print("总结：元类编程的关键点")
print("=" * 80)

summary = """
1. __new__ vs __init__:
   - __new__: 构造器，创建实例，返回实例对象
   - __init__: 初始化器，初始化已创建的实例，无返回值
   - 调用顺序: __new__ → __init__

2. 元类基础:
   - 元类是类的类，type 是所有类的默认元类
   - 元类继承自 type
   - 使用 metaclass=MyMeta 指定元类

3. 元类方法:
   - __new__(mcs, name, bases, attrs): 创建类
   - __init__(cls, name, bases, attrs): 初始化类
   - __call__(cls, *args, **kwargs): 控制实例创建
   - __prepare__(mcs, name, bases): 准备类的命名空间（Python 3.0+）

4. 元类的应用场景:
   - 自动注册子类
   - 添加属性验证
   - 实现 ORM 框架
   - 单例模式
   - 自动添加方法
   - 声明式 API

5. 元类 vs 其他方案:
   - 类装饰器: 更简单，但不影响子类
   - 基类 __init_subclass__: Python 3.6+ 的简化方案
   - 描述符: 用于属性级别的控制

6. 最佳实践:
   - 除非必要，否则不要使用元类（"Metaclasses are deeper magic than 99% of users should ever worry about"）
   - 优先考虑装饰器、__init_subclass__ 等更简单的方案
   - 元类适用于框架开发，不适合业务代码
   - 保持元类简单，避免过度复杂
"""

print(summary)

print("\n所有示例运行完成！")
