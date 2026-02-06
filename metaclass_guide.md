# Python 元类编程完全指南

## 📚 目录

1. [__new__ 和 __init__ 的深入理解](#1-new-和-init-的深入理解)
2. [元类基础概念](#2-元类基础概念)
3. [元类的创建方式](#3-元类的创建方式)
4. [元类的方法详解](#4-元类的方法详解)
5. [元类的实战应用](#5-元类的实战应用)
6. [元类 vs 其他方案](#6-元类-vs-其他方案)
7. [最佳实践和注意事项](#7-最佳实践和注意事项)

---

## 1. __new__ 和 __init__ 的深入理解

### 1.1 基本概念对比

| 特性 | `__new__` | `__init__` |
|------|-----------|------------|
| **性质** | 静态方法（类方法） | 实例方法 |
| **第一个参数** | `cls`（类） | `self`（实例） |
| **调用时机** | 实例创建之前 | 实例创建之后 |
| **主要职责** | 创建并返回实例对象 | 初始化已创建的实例 |
| **返回值** | **必须**返回实例对象 | 不需要返回值（隐式返回 None） |
| **调用顺序** | 先执行 | 后执行 |
| **是否必需** | 通常不需要重写 | 常用于自定义初始化 |

### 1.2 调用过程详解

```python
# 当你执行这行代码时：
obj = MyClass(arg1, arg2)

# Python 内部执行的过程：
# 步骤1: 调用 __new__ 创建实例
instance = MyClass.__new__(MyClass, arg1, arg2)

# 步骤2: 如果 __new__ 返回了 MyClass 的实例，调用 __init__
if isinstance(instance, MyClass):
    MyClass.__init__(instance, arg1, arg2)

# 步骤3: 返回实例
return instance
```

### 1.3 __new__ 的使用场景

#### 场景1：不可变类型的子类化

```python
class UpperStr(str):
    """总是大写的字符串"""
    
    def __new__(cls, value):
        # 必须在 __new__ 中处理，因为 str 是不可变的
        instance = super().__new__(cls, value.upper())
        return instance

s = UpperStr("hello")
print(s)  # "HELLO"
```

**为什么必须用 __new__？**
- `str`、`int`、`tuple` 等不可变类型在创建后不能修改
- `__init__` 被调用时，实例已经创建完成
- 必须在 `__new__` 中设置值

#### 场景2：单例模式

```python
class Singleton:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance  # 总是返回同一个实例
    
    def __init__(self, value):
        # 注意：每次调用都会执行 __init__
        self.value = value
```

#### 场景3：工厂模式

```python
class Shape:
    def __new__(cls, shape_type, *args, **kwargs):
        if shape_type == 'circle':
            return super().__new__(Circle)
        elif shape_type == 'square':
            return super().__new__(Square)
        else:
            return super().__new__(cls)
```

#### 场景4：对象池

```python
class PooledObject:
    _pool = []
    
    def __new__(cls):
        if cls._pool:
            # 从池中获取已有对象
            return cls._pool.pop()
        else:
            # 创建新对象
            return super().__new__(cls)
    
    def release(self):
        # 归还到池中
        self._pool.append(self)
```

### 1.4 __init__ 的使用场景

`__init__` 是最常用的初始化方法，用于设置实例属性：

```python
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age
        self._created_at = time.time()
        self._validate()
    
    def _validate(self):
        if self.age < 0:
            raise ValueError("年龄不能为负数")
```

### 1.5 同时使用 __new__ 和 __init__

```python
class TrackedObject:
    _all_instances = []
    
    def __new__(cls, *args, **kwargs):
        print(f"__new__: 创建实例")
        instance = super().__new__(cls)
        # 在 __new__ 中可以设置实例属性
        instance._id = id(instance)
        cls._all_instances.append(instance)
        return instance
    
    def __init__(self, name):
        print(f"__init__: 初始化实例 {self._id}")
        self.name = name
    
    @classmethod
    def count(cls):
        return len(cls._all_instances)
```

### 1.6 常见陷阱

#### 陷阱1：__new__ 不返回实例

```python
class Bad:
    def __new__(cls):
        # 忘记返回实例
        instance = super().__new__(cls)
        # 缺少 return 语句

obj = Bad()  # obj 将是 None！
```

#### 陷阱2：单例模式的 __init__ 重复调用

```python
class Singleton:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.count = 0  # 每次都会重置！

s1 = Singleton()
s1.count = 10
s2 = Singleton()  # __init__ 再次调用，count 被重置为 0
print(s2.count)  # 0，不是 10！
```

**解决方案：**
```python
class Singleton:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not Singleton._initialized:
            self.count = 0
            Singleton._initialized = True
```

---

## 2. 元类基础概念

### 2.1 一切皆对象

在 Python 中：

```python
# 普通对象
obj = MyClass()
print(type(obj))  # <class '__main__.MyClass'>

# 类也是对象
print(type(MyClass))  # <class 'type'>

# type 本身也是对象
print(type(type))  # <class 'type'>
```

**关系图：**
```
obj ──instance_of──> MyClass ──instance_of──> type ──instance_of──> type
 ↑                      ↑                        ↑
 |                      |                        |
对象                   类                      元类
```

### 2.2 元类的定义

> **元类就是用来创建类的"东西"**

- 类是实例的模板
- 元类是类的模板
- `type` 是 Python 的默认元类

### 2.3 类的创建过程

#### 方式1：使用 class 关键字（常规方式）

```python
class MyClass:
    x = 10
    
    def method(self):
        return "hello"
```

#### 方式2：使用 type() 动态创建（等价方式）

```python
# type(name, bases, attrs) -> 新类
MyClass = type(
    'MyClass',                                    # 类名
    (),                                           # 父类元组
    {                                             # 属性字典
        'x': 10,
        'method': lambda self: "hello"
    }
)
```

这两种方式完全等价！

### 2.4 元类的作用时机

```python
# 当 Python 解释器执行到这里时
class MyClass(metaclass=MyMeta):
    x = 10
    
    def method(self):
        pass

# 实际发生的事情：
MyClass = MyMeta(
    'MyClass',              # name
    (),                     # bases
    {                       # attrs
        'x': 10,
        'method': <function>,
        '__module__': '__main__',
        '__qualname__': 'MyClass'
    }
)
```

---

## 3. 元类的创建方式

### 3.1 方式1：继承 type

```python
class MyMeta(type):
    """自定义元类"""
    
    def __new__(mcs, name, bases, attrs):
        print(f"创建类: {name}")
        # 修改类的属性
        attrs['created_by_meta'] = True
        return super().__new__(mcs, name, bases, attrs)

# 使用元类
class MyClass(metaclass=MyMeta):
    pass

# 输出: 创建类: MyClass
print(MyClass.created_by_meta)  # True
```

### 3.2 方式2：使用 type() 动态创建元类

```python
def meta_new(mcs, name, bases, attrs):
    attrs['created_by_meta'] = True
    return type.__new__(mcs, name, bases, attrs)

# 创建元类
MyMeta = type('MyMeta', (type,), {'__new__': meta_new})

# 使用元类
class MyClass(metaclass=MyMeta):
    pass
```

### 3.3 元类的继承

```python
class BaseMeta(type):
    def __new__(mcs, name, bases, attrs):
        attrs['from_base'] = True
        return super().__new__(mcs, name, bases, attrs)

class ExtendedMeta(BaseMeta):
    def __new__(mcs, name, bases, attrs):
        attrs['from_extended'] = True
        return super().__new__(mcs, name, bases, attrs)

class MyClass(metaclass=ExtendedMeta):
    pass

print(MyClass.from_base)      # True
print(MyClass.from_extended)  # True
```

---

## 4. 元类的方法详解

### 4.1 __new__ 方法

**签名：**
```python
def __new__(mcs, name, bases, attrs):
    """
    mcs: metaclass 的缩写，元类本身
    name: 要创建的类的名字（字符串）
    bases: 要创建的类的父类元组
    attrs: 要创建的类的属性字典
    
    返回: 新创建的类对象
    """
    return super().__new__(mcs, name, bases, attrs)
```

**用途：**
- 修改类的属性
- 添加新的类属性或方法
- 阻止类的创建（抛出异常）
- 返回不同的类

**示例：**
```python
class ValidateMeta(type):
    def __new__(mcs, name, bases, attrs):
        # 检查类名必须以大写字母开头
        if not name[0].isupper():
            raise TypeError(f"类名 {name} 必须以大写字母开头")
        
        # 检查是否定义了必需的方法
        if 'required_method' not in attrs:
            raise TypeError(f"类 {name} 必须定义 required_method")
        
        return super().__new__(mcs, name, bases, attrs)
```

### 4.2 __init__ 方法

**签名：**
```python
def __init__(cls, name, bases, attrs):
    """
    cls: 新创建的类（已经创建完成）
    name: 类的名字
    bases: 父类元组
    attrs: 属性字典
    
    返回: None（无需返回值）
    """
    super().__init__(name, bases, attrs)
```

**用途：**
- 在类创建后进行额外的初始化
- 注册类到某个注册表
- 设置类级别的配置

**示例：**
```python
class RegistryMeta(type):
    _registry = {}
    
    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        # 注册类
        RegistryMeta._registry[name] = cls
        print(f"已注册类: {name}")
```

### 4.3 __call__ 方法

**签名：**
```python
def __call__(cls, *args, **kwargs):
    """
    cls: 类本身
    *args, **kwargs: 传递给类构造函数的参数
    
    返回: 新创建的实例
    """
    # 默认行为：
    instance = cls.__new__(cls, *args, **kwargs)
    if isinstance(instance, cls):
        cls.__init__(instance, *args, **kwargs)
    return instance
```

**用途：**
- 控制实例的创建过程
- 实现单例模式
- 对象池
- 实例缓存

**示例：**
```python
class SingletonMeta(type):
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            # 首次创建
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]
```

### 4.4 __prepare__ 方法（Python 3.0+）

**签名：**
```python
@classmethod
def __prepare__(mcs, name, bases, **kwargs):
    """
    mcs: 元类
    name: 类名
    bases: 父类元组
    **kwargs: 传递给元类的额外参数
    
    返回: 用于存储类属性的映射对象（通常是字典）
    """
    return {}
```

**用途：**
- 提供自定义的命名空间（而不是普通 dict）
- 保持属性定义顺序（使用 OrderedDict）
- 实现特殊的属性存储逻辑

**示例：**
```python
from collections import OrderedDict

class OrderedMeta(type):
    @classmethod
    def __prepare__(mcs, name, bases):
        print(f"准备 {name} 的命名空间")
        return OrderedDict()  # 返回有序字典
    
    def __new__(mcs, name, bases, attrs):
        print(f"属性顺序: {list(attrs.keys())}")
        return super().__new__(mcs, name, bases, attrs)
```

### 4.5 方法调用顺序

```python
class TraceMeta(type):
    @classmethod
    def __prepare__(mcs, name, bases):
        print(f"1. __prepare__: {name}")
        return {}
    
    def __new__(mcs, name, bases, attrs):
        print(f"2. __new__: {name}")
        return super().__new__(mcs, name, bases, attrs)
    
    def __init__(cls, name, bases, attrs):
        print(f"3. __init__: {name}")
        super().__init__(name, bases, attrs)
    
    def __call__(cls, *args, **kwargs):
        print(f"4. __call__: 创建 {cls.__name__} 的实例")
        return super().__call__(*args, **kwargs)

# 定义类时
print(">>> class MyClass(metaclass=TraceMeta): ...")
class MyClass(metaclass=TraceMeta):
    pass

# 创建实例时
print("\n>>> obj = MyClass()")
obj = MyClass()

# 输出:
# >>> class MyClass(metaclass=TraceMeta): ...
# 1. __prepare__: MyClass
# 2. __new__: MyClass
# 3. __init__: MyClass
# 
# >>> obj = MyClass()
# 4. __call__: 创建 MyClass 的实例
```

---

## 5. 元类的实战应用

### 5.1 自动注册子类

**场景：** 插件系统、命令注册、URL 路由

```python
class PluginMeta(type):
    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        if not hasattr(cls, 'registry'):
            # 基类：创建注册表
            cls.registry = {}
        else:
            # 子类：自动注册
            plugin_name = attrs.get('name', name)
            cls.registry[plugin_name] = cls

class Plugin(metaclass=PluginMeta):
    @classmethod
    def get_plugin(cls, name):
        return cls.registry.get(name)

# 自动注册
class EmailPlugin(Plugin):
    name = 'email'

class SMSPlugin(Plugin):
    name = 'sms'

# 使用
PluginClass = Plugin.get_plugin('email')
plugin = PluginClass()
```

### 5.2 ORM 框架

**场景：** Django ORM、SQLAlchemy

```python
class Field:
    def __init__(self, field_type):
        self.field_type = field_type
        self.name = None
    
    def __set_name__(self, owner, name):
        self.name = name

class ModelMeta(type):
    def __new__(mcs, name, bases, attrs):
        # 收集所有字段
        fields = {}
        for key, value in list(attrs.items()):
            if isinstance(value, Field):
                fields[key] = value
        
        attrs['_fields'] = fields
        return super().__new__(mcs, name, bases, attrs)

class Model(metaclass=ModelMeta):
    def __init__(self, **kwargs):
        for name in self._fields:
            setattr(self, name, kwargs.get(name))
    
    def save(self):
        # 保存到数据库
        print(f"保存 {self.__class__.__name__}: {self._fields}")

# 使用
class User(Model):
    name = Field(str)
    age = Field(int)
    email = Field(str)

user = User(name="张三", age=25, email="zhang@example.com")
user.save()
```

### 5.3 单例模式

```python
class SingletonMeta(type):
    _instances = {}
    _lock = threading.Lock()
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class Database(metaclass=SingletonMeta):
    def __init__(self, host):
        self.host = host

db1 = Database("localhost")
db2 = Database("192.168.1.1")
assert db1 is db2  # True
```

### 5.4 接口强制实现

```python
class InterfaceMeta(type):
    def __new__(mcs, name, bases, attrs):
        # 检查基类中定义的抽象方法
        for base in bases:
            if hasattr(base, '_required_methods'):
                for method in base._required_methods:
                    if method not in attrs:
                        raise TypeError(
                            f"类 {name} 必须实现方法 {method}"
                        )
        
        return super().__new__(mcs, name, bases, attrs)

class Interface(metaclass=InterfaceMeta):
    _required_methods = ['connect', 'disconnect']

class Database(Interface):
    def connect(self):
        pass
    
    def disconnect(self):
        pass  # OK

class BadDatabase(Interface):
    def connect(self):
        pass
    # 缺少 disconnect - 会抛出 TypeError
```

### 5.5 属性自动验证

```python
class ValidatedMeta(type):
    def __new__(mcs, name, bases, attrs):
        # 为所有类型注解创建验证属性
        annotations = attrs.get('__annotations__', {})
        
        for attr_name, attr_type in annotations.items():
            storage_name = f'_{attr_name}'
            
            def make_property(name, typ):
                def getter(self):
                    return getattr(self, f'_{name}')
                
                def setter(self, value):
                    if not isinstance(value, typ):
                        raise TypeError(
                            f'{name} 必须是 {typ.__name__} 类型'
                        )
                    setattr(self, f'_{name}', value)
                
                return property(getter, setter)
            
            attrs[attr_name] = make_property(attr_name, attr_type)
        
        return super().__new__(mcs, name, bases, attrs)

class Person(metaclass=ValidatedMeta):
    name: str
    age: int
    
    def __init__(self, name, age):
        self.name = name
        self.age = age

p = Person("张三", 25)  # OK
p.age = "30"  # TypeError: age 必须是 int 类型
```

### 5.6 自动添加方法

```python
class AutoMethodMeta(type):
    def __new__(mcs, name, bases, attrs):
        # 自动添加 __repr__
        if '__repr__' not in attrs:
            def auto_repr(self):
                attrs_str = ', '.join(
                    f'{k}={v!r}'
                    for k, v in self.__dict__.items()
                    if not k.startswith('_')
                )
                return f"{self.__class__.__name__}({attrs_str})"
            attrs['__repr__'] = auto_repr
        
        # 自动添加 __eq__
        if '__eq__' not in attrs:
            def auto_eq(self, other):
                if not isinstance(other, self.__class__):
                    return False
                return self.__dict__ == other.__dict__
            attrs['__eq__'] = auto_eq
        
        return super().__new__(mcs, name, bases, attrs)
```

---

## 6. 元类 vs 其他方案

### 6.1 元类 vs 类装饰器

| 特性 | 元类 | 类装饰器 |
|------|------|----------|
| **作用时机** | 类定义时 | 类定义后 |
| **影响范围** | 类及所有子类 | 仅被装饰的类 |
| **复杂度** | 较高 | 较低 |
| **可读性** | 较差 | 较好 |
| **能力** | 完全控制类的创建 | 修改已创建的类 |

**示例对比：**

```python
# 元类方式
class Meta(type):
    def __new__(mcs, name, bases, attrs):
        attrs['method'] = lambda self: "from meta"
        return super().__new__(mcs, name, bases, attrs)

class MyClass(metaclass=Meta):
    pass

class SubClass(MyClass):  # 子类也会受影响
    pass

# 装饰器方式
def decorator(cls):
    cls.method = lambda self: "from decorator"
    return cls

@decorator
class MyClass:
    pass

class SubClass(MyClass):  # 子类不受影响
    pass
```

**选择建议：**
- 如果只需要修改一个类 → 使用装饰器
- 如果需要影响所有子类 → 使用元类
- 如果需要控制类的创建过程 → 使用元类

### 6.2 元类 vs __init_subclass__（Python 3.6+）

`__init_subclass__` 是 Python 3.6 引入的简化方案：

```python
# 使用元类
class Meta(type):
    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        cls.registry.setdefault(name, cls)

class Base(metaclass=Meta):
    registry = {}

# 使用 __init_subclass__ (更简单)
class Base:
    registry = {}
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.registry[cls.__name__] = cls

# 使用方式相同
class SubClass(Base):
    pass
```

**选择建议：**
- Python 3.6+ 优先使用 `__init_subclass__`
- 只有在需要 `__new__`、`__call__`、`__prepare__` 时才用元类

### 6.3 元类 vs 描述符

| 特性 | 元类 | 描述符 |
|------|------|--------|
| **作用对象** | 类 | 实例属性 |
| **控制粒度** | 类级别 | 属性级别 |
| **使用场景** | 修改类结构 | 属性访问控制 |

```python
# 描述符：控制属性
class ValidatedField:
    def __set__(self, instance, value):
        if not isinstance(value, int):
            raise TypeError("必须是整数")
        instance.__dict__[self.name] = value

# 元类：控制类
class ValidatedMeta(type):
    def __new__(mcs, name, bases, attrs):
        # 修改整个类的结构
        return super().__new__(mcs, name, bases, attrs)
```

### 6.4 对比总结表

| 方案 | 复杂度 | 能力 | 适用场景 |
|------|--------|------|----------|
| **元类** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 框架开发、深度定制 |
| **`__init_subclass__`** | ⭐⭐⭐ | ⭐⭐⭐⭐ | 子类注册、验证 |
| **类装饰器** | ⭐⭐ | ⭐⭐⭐ | 单个类的修改 |
| **描述符** | ⭐⭐⭐ | ⭐⭐⭐ | 属性访问控制 |
| **普通继承** | ⭐ | ⭐⭐ | 代码复用 |

---

## 7. 最佳实践和注意事项

### 7.1 何时使用元类

✅ **应该使用元类的场景：**

1. **框架开发**：Django ORM、Flask、SQLAlchemy
2. **自动注册**：插件系统、命令注册
3. **深度定制**：修改类的创建过程
4. **API 设计**：声明式 API

❌ **不应该使用元类的场景：**

1. **业务逻辑**：普通的业务代码
2. **简单需求**：装饰器或继承就能解决的
3. **一次性修改**：只修改一个类
4. **团队不熟悉**：增加维护成本

### 7.2 元类设计原则

#### 原则1：保持简单

```python
# ❌ 不好：过于复杂
class ComplexMeta(type):
    def __prepare__(mcs, name, bases):
        # 复杂的命名空间逻辑
        pass
    
    def __new__(mcs, name, bases, attrs):
        # 复杂的类修改逻辑
        pass
    
    def __init__(cls, name, bases, attrs):
        # 复杂的初始化逻辑
        pass
    
    def __call__(cls, *args, **kwargs):
        # 复杂的实例创建逻辑
        pass

# ✅ 好：职责单一
class SimpleMeta(type):
    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        # 只做一件事：注册类
        if not hasattr(cls, 'registry'):
            cls.registry = {}
        else:
            cls.registry[name] = cls
```

#### 原则2：提供清晰的文档

```python
class DocumentedMeta(type):
    """
    自动注册子类的元类
    
    用法:
        class Base(metaclass=DocumentedMeta):
            pass
        
        class SubClass(Base):
            pass  # 自动注册到 Base.registry
    
    注意:
        - 基类会创建 registry 属性
        - 子类会自动注册到 registry 中
        - 使用 Base.registry 访问所有子类
    """
    
    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        if not hasattr(cls, 'registry'):
            cls.registry = {}
        else:
            cls.registry[name] = cls
```

#### 原则3：考虑替代方案

```python
# 问：我需要为所有子类添加一个方法
# 答：使用基类而不是元类

# ❌ 不好：使用元类
class AddMethodMeta(type):
    def __new__(mcs, name, bases, attrs):
        attrs['common_method'] = lambda self: "common"
        return super().__new__(mcs, name, bases, attrs)

class Base(metaclass=AddMethodMeta):
    pass

# ✅ 好：使用基类
class Base:
    def common_method(self):
        return "common"
```

### 7.3 常见陷阱

#### 陷阱1：元类冲突

```python
class Meta1(type):
    pass

class Meta2(type):
    pass

class Base1(metaclass=Meta1):
    pass

class Base2(metaclass=Meta2):
    pass

# ❌ 错误：元类冲突
class Child(Base1, Base2):  # TypeError: metaclass conflict
    pass

# ✅ 解决：创建组合元类
class CombinedMeta(Meta1, Meta2):
    pass

class Child(Base1, Base2, metaclass=CombinedMeta):
    pass
```

#### 陷阱2：无限递归

```python
# ❌ 错误：无限递归
class BadMeta(type):
    def __call__(cls, *args, **kwargs):
        # 再次调用 cls() 导致无限递归
        return cls(*args, **kwargs)

# ✅ 正确：调用 super()
class GoodMeta(type):
    def __call__(cls, *args, **kwargs):
        return super().__call__(*args, **kwargs)
```

#### 陷阱3：忘记调用 super()

```python
# ❌ 不好：没有调用 super()
class BadMeta(type):
    def __init__(cls, name, bases, attrs):
        # 忘记调用 super().__init__()
        cls.custom_attr = True

# ✅ 好：调用 super()
class GoodMeta(type):
    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        cls.custom_attr = True
```

### 7.4 调试技巧

#### 技巧1：添加日志

```python
class DebugMeta(type):
    def __new__(mcs, name, bases, attrs):
        print(f"[DebugMeta] 创建类: {name}")
        print(f"  父类: {bases}")
        print(f"  属性: {list(attrs.keys())}")
        return super().__new__(mcs, name, bases, attrs)
```

#### 技巧2：使用 __mro__

```python
# 查看方法解析顺序
print(MyClass.__mro__)

# 查看元类
print(type(MyClass))
```

#### 技巧3：inspect 模块

```python
import inspect

# 查看类的源代码
print(inspect.getsource(MyClass))

# 查看元类
print(inspect.getmro(MyClass))
```

### 7.5 性能考虑

元类在类创建时执行，对运行时性能影响很小：

```python
import timeit

# 元类版本
class Meta(type):
    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        cls.x = 10

class WithMeta(metaclass=Meta):
    pass

# 普通版本
class WithoutMeta:
    x = 10

# 测试实例创建性能
print(timeit.timeit('WithMeta()', globals=globals(), number=1000000))
print(timeit.timeit('WithoutMeta()', globals=globals(), number=1000000))
# 性能差异可以忽略不计
```

### 7.6 Tim Peters 的名言

> "Metaclasses are deeper magic than 99% of users should ever worry about. If you wonder whether you need them, you don't (the people who actually need them know with certainty that they need them, and don't need an explanation about why)."
>
> "元类是比 99% 的用户需要担心的更深层次的魔法。如果你怀疑自己是否需要它们，那你就不需要（真正需要它们的人确切地知道他们需要它们，并且不需要解释为什么）。"

---

## 8. 学习路线图

```
第1阶段：理解基础
├── __new__ 和 __init__ 的区别
├── type() 函数的双重用途
└── 类也是对象的概念

第2阶段：元类入门
├── 创建第一个元类
├── 理解 __new__、__init__、__call__
└── 使用 metaclass= 语法

第3阶段：实战应用
├── 子类自动注册
├── 单例模式
├── 属性验证
└── ORM 基础

第4阶段：高级技巧
├── __prepare__ 方法
├── 元类继承
├── 元类冲突解决
└── 与描述符结合

第5阶段：替代方案
├── __init_subclass__
├── 类装饰器
├── 描述符
└── 选择合适的工具
```

---

## 9. 练习题

### 练习1：实现一个计数器元类

要求：自动统计每个类创建了多少个实例

```python
class CounterMeta(type):
    # TODO: 实现
    pass

class MyClass(metaclass=CounterMeta):
    pass

obj1 = MyClass()
obj2 = MyClass()
print(MyClass.instance_count)  # 应该输出 2
```

### 练习2：实现一个不可变类元类

要求：使用元类创建不可变类（实例创建后不能修改属性）

```python
class ImmutableMeta(type):
    # TODO: 实现
    pass

class Point(metaclass=ImmutableMeta):
    def __init__(self, x, y):
        self.x = x
        self.y = y

p = Point(1, 2)
p.x = 10  # 应该抛出 AttributeError
```

### 练习3：实现一个 API 路由元类

要求：自动收集所有标记为路由的方法

```python
# TODO: 实现 RouteMeta 和 route 装饰器

class UserAPI(metaclass=RouteMeta):
    @route('GET', '/users')
    def list_users(self):
        pass
    
    @route('POST', '/users')
    def create_user(self):
        pass

print(UserAPI.routes)  # 应该输出所有路由信息
```

---

## 10. 参考资源

### 官方文档
- [Data Model - Customizing class creation](https://docs.python.org/3/reference/datamodel.html#customizing-class-creation)
- [Built-in Functions - type](https://docs.python.org/3/library/functions.html#type)

### 经典文章
- [A Primer on Python Metaclasses](https://jakevdp.github.io/blog/2012/12/01/a-primer-on-python-metaclasses/)
- [Understanding Python metaclasses](https://blog.ionelmc.ro/2015/02/09/understanding-python-metaclasses/)

### 实际应用
- Django ORM 源码
- SQLAlchemy 源码
- Flask 插件系统

---

## 总结

### 核心要点

1. **__new__ vs __init__**
   - `__new__` 创建实例，`__init__` 初始化实例
   - `__new__` 用于不可变类型、单例、工厂模式

2. **元类基础**
   - 元类是类的类，`type` 是默认元类
   - 元类控制类的创建过程

3. **元类方法**
   - `__new__`: 创建类
   - `__init__`: 初始化类
   - `__call__`: 控制实例创建
   - `__prepare__`: 自定义命名空间

4. **使用场景**
   - 框架开发
   - 自动注册
   - 属性验证
   - ORM 实现

5. **最佳实践**
   - 尽量不用元类
   - 优先考虑 `__init_subclass__`、装饰器
   - 保持简单、提供文档
   - 注意元类冲突

### 记住这句话

> 如果你不确定是否需要元类，那你就不需要！

元类是强大的工具，但也是复杂的。在大多数情况下，普通的类继承、装饰器或 `__init_subclass__` 就足够了。
