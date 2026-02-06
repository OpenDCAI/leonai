# Python 元类编程快速参考手册

## 📋 快速查找索引

- [__new__ vs __init__](#new-vs-init)
- [元类基础语法](#元类基础语法)
- [元类方法速查](#元类方法速查)
- [常见模式](#常见模式)
- [陷阱和解决方案](#陷阱和解决方案)
- [备忘单](#备忘单)

---

## __new__ vs __init__

### 对比表

```
┌─────────────┬──────────────────────────────┬──────────────────────────────┐
│   特性      │          __new__             │          __init__            │
├─────────────┼──────────────────────────────┼──────────────────────────────┤
│ 类型        │ 静态方法/类方法               │ 实例方法                      │
│ 第一个参数  │ cls (类)                     │ self (实例)                   │
│ 调用时机    │ 实例创建之前                  │ 实例创建之后                  │
│ 职责        │ 创建并返回实例                │ 初始化实例                    │
│ 返回值      │ 必须返回实例对象              │ None                         │
│ 调用顺序    │ 第1步                        │ 第2步                        │
│ 使用频率    │ 少                           │ 非常常见                      │
└─────────────┴──────────────────────────────┴──────────────────────────────┘
```

### 代码模板

```python
# 完整的对象创建过程
class MyClass:
    def __new__(cls, *args, **kwargs):
        print("1. __new__: 创建实例")
        instance = super().__new__(cls)
        return instance  # 必须返回
    
    def __init__(self, value):
        print("2. __init__: 初始化实例")
        self.value = value  # 不需要返回值

# 调用
obj = MyClass(42)
# 输出:
# 1. __new__: 创建实例
# 2. __init__: 初始化实例
```

### __new__ 的典型用途

#### 1. 单例模式
```python
class Singleton:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

#### 2. 不可变类型子类化
```python
class PositiveInt(int):
    def __new__(cls, value):
        return super().__new__(cls, abs(value))

n = PositiveInt(-10)  # 结果是 10
```

#### 3. 工厂模式
```python
class Shape:
    def __new__(cls, shape_type):
        if shape_type == 'circle':
            return Circle()
        elif shape_type == 'square':
            return Square()
```

#### 4. 对象池
```python
class Pooled:
    _pool = []
    
    def __new__(cls):
        if cls._pool:
            return cls._pool.pop()
        return super().__new__(cls)
    
    def release(self):
        self._pool.append(self)
```

---

## 元类基础语法

### 创建元类的三种方式

#### 方式1：继承 type（推荐）
```python
class MyMeta(type):
    def __new__(mcs, name, bases, attrs):
        # 修改类
        attrs['added_by_meta'] = True
        return super().__new__(mcs, name, bases, attrs)

class MyClass(metaclass=MyMeta):
    pass
```

#### 方式2：使用 type() 动态创建
```python
def meta_new(mcs, name, bases, attrs):
    attrs['added'] = True
    return type.__new__(mcs, name, bases, attrs)

MyMeta = type('MyMeta', (type,), {'__new__': meta_new})
```

#### 方式3：使用 __init_subclass__（Python 3.6+，推荐用于简单场景）
```python
class Base:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.added = True

class MyClass(Base):
    pass  # 自动获得 added 属性
```

### 类创建的等价形式

```python
# 这两种写法完全等价：

# 方式1: class 关键字
class MyClass:
    x = 10
    def method(self):
        return "hello"

# 方式2: 使用 type()
MyClass = type(
    'MyClass',                           # name
    (),                                  # bases
    {                                    # attrs
        'x': 10,
        'method': lambda self: "hello"
    }
)
```

---

## 元类方法速查

### 方法签名和调用时机

```python
class CompleteMeta(type):
    
    # ======== 类创建阶段 ========
    
    @classmethod
    def __prepare__(mcs, name, bases, **kwargs):
        """
        调用时机: 最先被调用，在类体执行之前
        作用: 返回用于存储类属性的字典
        参数:
            mcs: 元类
            name: 类名 (str)
            bases: 父类元组 (tuple)
            **kwargs: 元类的关键字参数
        返回: dict 或类似 dict 的对象
        """
        print("1. __prepare__")
        return {}
    
    def __new__(mcs, name, bases, attrs):
        """
        调用时机: 在类体执行后，创建类对象
        作用: 创建类
        参数:
            mcs: 元类 (metaclass)
            name: 类名 (str)
            bases: 父类元组 (tuple)
            attrs: 类属性字典 (dict)
        返回: 类对象
        """
        print("2. __new__")
        return super().__new__(mcs, name, bases, attrs)
    
    def __init__(cls, name, bases, attrs):
        """
        调用时机: 在类创建后
        作用: 初始化类
        参数:
            cls: 新创建的类
            name: 类名 (str)
            bases: 父类元组 (tuple)
            attrs: 类属性字典 (dict)
        返回: None
        """
        print("3. __init__")
        super().__init__(name, bases, attrs)
    
    # ======== 实例创建阶段 ========
    
    def __call__(cls, *args, **kwargs):
        """
        调用时机: 创建类的实例时 (MyClass())
        作用: 控制实例的创建
        参数:
            cls: 类
            *args, **kwargs: 传递给构造函数的参数
        返回: 实例对象
        """
        print("4. __call__")
        return super().__call__(*args, **kwargs)
```

### 调用顺序演示

```python
# 定义类时
class MyClass(metaclass=CompleteMeta):
    pass

# 输出:
# 1. __prepare__
# 2. __new__
# 3. __init__

# 创建实例时
obj = MyClass()

# 输出:
# 4. __call__
```

### 方法选择决策树

```
需要自定义命名空间（如保持顺序）？
│
├─ 是 → 使用 __prepare__
│
└─ 否 → 需要修改类的创建？
         │
         ├─ 是 → 使用 __new__
         │
         └─ 否 → 需要在类创建后初始化？
                  │
                  ├─ 是 → 使用 __init__
                  │
                  └─ 否 → 需要控制实例创建？
                           │
                           ├─ 是 → 使用 __call__
                           │
                           └─ 否 → 不需要元类！
```

---

## 常见模式

### 模式1: 自动注册

```python
# 完整代码
class AutoRegisterMeta(type):
    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        if not hasattr(cls, 'registry'):
            cls.registry = {}
        else:
            cls.registry[name] = cls

class Plugin(metaclass=AutoRegisterMeta):
    @classmethod
    def get(cls, name):
        return cls.registry[name]

class EmailPlugin(Plugin): pass
class SMSPlugin(Plugin): pass

# 使用
EmailPlugin = Plugin.get('EmailPlugin')
```

### 模式2: 单例模式

```python
# 完整代码
class SingletonMeta(type):
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class Database(metaclass=SingletonMeta):
    def __init__(self, host):
        self.host = host

# 使用
db1 = Database("localhost")
db2 = Database("192.168.1.1")
assert db1 is db2  # True
```

### 模式3: 属性验证

```python
# 完整代码
class ValidatedMeta(type):
    def __new__(mcs, name, bases, attrs):
        annotations = attrs.get('__annotations__', {})
        
        for attr_name, attr_type in annotations.items():
            def make_property(name, typ):
                storage = f'_{name}'
                
                def getter(self):
                    return getattr(self, storage)
                
                def setter(self, value):
                    if not isinstance(value, typ):
                        raise TypeError(f'{name} 必须是 {typ.__name__}')
                    setattr(self, storage, value)
                
                return property(getter, setter)
            
            attrs[attr_name] = make_property(attr_name, attr_type)
        
        return super().__new__(mcs, name, bases, attrs)

class Person(metaclass=ValidatedMeta):
    name: str
    age: int
    
    def __init__(self, name, age):
        self.name = name
        self.age = age

# 使用
p = Person("张三", 25)  # OK
p.age = "30"  # TypeError
```

### 模式4: ORM 字段

```python
# 完整代码
class Field:
    def __init__(self, field_type):
        self.field_type = field_type
        self.name = None
    
    def __set_name__(self, owner, name):
        self.name = name
    
    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.__dict__.get(self.name)
    
    def __set__(self, instance, value):
        if not isinstance(value, self.field_type):
            raise TypeError(f'{self.name} 必须是 {self.field_type.__name__}')
        instance.__dict__[self.name] = value

class ModelMeta(type):
    def __new__(mcs, name, bases, attrs):
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

class User(Model):
    name = Field(str)
    age = Field(int)

# 使用
user = User(name="张三", age=25)
```

### 模式5: 接口强制实现

```python
# 完整代码
class InterfaceMeta(type):
    def __new__(mcs, name, bases, attrs):
        for base in bases:
            if hasattr(base, '_required_methods'):
                for method in base._required_methods:
                    if method not in attrs:
                        raise TypeError(
                            f'{name} 必须实现 {method} 方法'
                        )
        return super().__new__(mcs, name, bases, attrs)

class Interface(metaclass=InterfaceMeta):
    _required_methods = ['connect', 'disconnect']

class Database(Interface):
    def connect(self): pass
    def disconnect(self): pass  # OK

# class Bad(Interface):
#     def connect(self): pass
#     # 缺少 disconnect - TypeError!
```

### 模式6: 保持属性顺序

```python
# 完整代码
from collections import OrderedDict

class OrderedMeta(type):
    @classmethod
    def __prepare__(mcs, name, bases):
        return OrderedDict()
    
    def __new__(mcs, name, bases, attrs):
        cls = super().__new__(mcs, name, bases, dict(attrs))
        cls._field_order = [
            k for k in attrs.keys()
            if not k.startswith('_')
        ]
        return cls

class Form(metaclass=OrderedMeta):
    name = None
    email = None
    age = None

# 使用
print(Form._field_order)  # ['name', 'email', 'age']
```

---

## 陷阱和解决方案

### 陷阱1: 忘记返回值

```python
# ❌ 错误
class BadMeta(type):
    def __new__(mcs, name, bases, attrs):
        instance = super().__new__(mcs, name, bases, attrs)
        # 忘记 return！

# ✅ 正确
class GoodMeta(type):
    def __new__(mcs, name, bases, attrs):
        instance = super().__new__(mcs, name, bases, attrs)
        return instance  # 必须返回
```

### 陷阱2: 单例的 __init__ 重复调用

```python
# ❌ 问题：每次都会重新初始化
class BadSingleton:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.value = 0  # 每次调用都重置！

s1 = BadSingleton()
s1.value = 10
s2 = BadSingleton()
print(s2.value)  # 0，不是 10！

# ✅ 解决方案1: 使用标志
class GoodSingleton:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not GoodSingleton._initialized:
            self.value = 0
            GoodSingleton._initialized = True

# ✅ 解决方案2: 使用元类的 __call__
class SingletonMeta(type):
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
```

### 陷阱3: 元类冲突

```python
# ❌ 错误：元类冲突
class Meta1(type): pass
class Meta2(type): pass

class A(metaclass=Meta1): pass
class B(metaclass=Meta2): pass

class C(A, B):  # TypeError: metaclass conflict
    pass

# ✅ 解决：创建组合元类
class CombinedMeta(Meta1, Meta2):
    pass

class C(A, B, metaclass=CombinedMeta):
    pass
```

### 陷阱4: 无限递归

```python
# ❌ 错误：无限递归
class BadMeta(type):
    def __call__(cls, *args, **kwargs):
        return cls(*args, **kwargs)  # 再次调用自己！

# ✅ 正确：调用 super()
class GoodMeta(type):
    def __call__(cls, *args, **kwargs):
        return super().__call__(*args, **kwargs)
```

### 陷阱5: 忘记调用 super()

```python
# ❌ 不好
class BadMeta(type):
    def __init__(cls, name, bases, attrs):
        # 忘记调用 super().__init__()
        cls.custom = True

# ✅ 好
class GoodMeta(type):
    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        cls.custom = True
```

---

## 备忘单

### 一页纸总结

```python
# ============================================================
# 元类快速参考
# ============================================================

# 1. 基本结构
class MyMeta(type):
    def __new__(mcs, name, bases, attrs):
        return super().__new__(mcs, name, bases, attrs)

class MyClass(metaclass=MyMeta):
    pass

# 2. 元类方法（按调用顺序）
__prepare__(mcs, name, bases)      # 准备命名空间
__new__(mcs, name, bases, attrs)   # 创建类
__init__(cls, name, bases, attrs)  # 初始化类
__call__(cls, *args, **kwargs)     # 创建实例

# 3. 常用模式

# 单例
class SingletonMeta(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

# 注册
class RegisterMeta(type):
    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        if not hasattr(cls, 'registry'):
            cls.registry = {}
        else:
            cls.registry[name] = cls

# 验证
class ValidateMeta(type):
    def __new__(mcs, name, bases, attrs):
        if 'required_method' not in attrs:
            raise TypeError(f'{name} 缺少 required_method')
        return super().__new__(mcs, name, bases, attrs)

# 4. __new__ vs __init__（对象级别）

class MyClass:
    def __new__(cls):          # 创建实例
        return super().__new__(cls)
    
    def __init__(self):        # 初始化实例
        self.x = 10

# 5. 替代方案

# __init_subclass__ (Python 3.6+)
class Base:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.registered = True

# 类装饰器
def register(cls):
    cls.registered = True
    return cls

@register
class MyClass:
    pass

# 6. 检查和调试
type(obj)           # 对象的类型
type(MyClass)       # 类的类型（元类）
MyClass.__mro__     # 方法解析顺序
MyClass.__dict__    # 类的属性字典

# 7. 记住
# - 元类是类的类
# - type 是默认元类
# - 元类在类创建时执行
# - 如果不确定，就不要用元类！
```

### 决策树

```
我需要修改类的行为
│
├─ 只修改一个类？
│  └─ 是 → 使用类装饰器
│
├─ 需要影响所有子类？
│  │
│  ├─ 只需要在子类定义时做些事？
│  │  └─ 是 → 使用 __init_subclass__ (Python 3.6+)
│  │
│  └─ 需要完全控制类的创建？
│     └─ 是 → 使用元类
│
├─ 需要修改实例的创建？
│  │
│  ├─ 单例、对象池等？
│  │  └─ 是 → 使用元类的 __call__
│  │
│  └─ 只是初始化？
│     └─ 是 → 使用 __init__
│
└─ 需要修改属性访问？
   └─ 是 → 使用描述符或 property
```

### 性能提示

```python
# 元类在类创建时执行，对运行时性能影响极小
import timeit

# 有元类
class Meta(type):
    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)

class WithMeta(metaclass=Meta):
    pass

# 无元类
class WithoutMeta:
    pass

# 测试实例创建（基本没有差异）
t1 = timeit.timeit('WithMeta()', globals=globals(), number=1000000)
t2 = timeit.timeit('WithoutMeta()', globals=globals(), number=1000000)
print(f"差异: {abs(t1-t2)} 秒")  # 可忽略不计
```

### 常见错误代码

```python
# 1. 忘记 return
def __new__(mcs, name, bases, attrs):
    super().__new__(mcs, name, bases, attrs)
    # 缺少 return！

# 2. 无限递归
def __call__(cls, *args, **kwargs):
    return cls(*args, **kwargs)  # 错误！

# 3. 类型检查错误
if not isinstance(value, int):  # OK
if type(value) != int:          # 不好，不支持子类

# 4. 忘记 super()
def __init__(cls, name, bases, attrs):
    cls.x = 10  # 缺少 super().__init__()

# 5. 元类参数错误
class MyClass(metaclass=MyMeta()):  # 错误！
class MyClass(metaclass=MyMeta):    # 正确
```

### 测试检查清单

```
□ 元类正确继承 type
□ __new__ 返回了类对象
□ 调用了 super().__new__() 或 super().__init__()
□ 没有无限递归
□ 元类冲突已解决
□ 单例模式不会重复初始化
□ 属性验证正确工作
□ 文档清晰说明用法
□ 考虑过更简单的替代方案
□ 性能测试通过
```

---

## 实用代码片段

### 片段1: 调试元类

```python
class DebugMeta(type):
    """添加详细日志的元类"""
    
    @classmethod
    def __prepare__(mcs, name, bases):
        print(f"[PREPARE] {name}")
        return {}
    
    def __new__(mcs, name, bases, attrs):
        print(f"[NEW] {name}")
        print(f"  Bases: {bases}")
        print(f"  Attrs: {list(attrs.keys())}")
        return super().__new__(mcs, name, bases, attrs)
    
    def __init__(cls, name, bases, attrs):
        print(f"[INIT] {name}")
        super().__init__(name, bases, attrs)
    
    def __call__(cls, *args, **kwargs):
        print(f"[CALL] Creating {cls.__name__} instance")
        return super().__call__(*args, **kwargs)
```

### 片段2: 线程安全单例

```python
import threading

class ThreadSafeSingletonMeta(type):
    """线程安全的单例元类"""
    _instances = {}
    _lock = threading.Lock()
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
```

### 片段3: 方法拦截

```python
class InterceptMeta(type):
    """拦截所有方法调用"""
    
    def __new__(mcs, name, bases, attrs):
        for key, value in attrs.items():
            if callable(value) and not key.startswith('_'):
                attrs[key] = mcs._wrap_method(value, key)
        return super().__new__(mcs, name, bases, attrs)
    
    @staticmethod
    def _wrap_method(method, name):
        def wrapper(*args, **kwargs):
            print(f"调用 {name}")
            result = method(*args, **kwargs)
            print(f"{name} 完成")
            return result
        return wrapper
```

### 片段4: 属性冻结

```python
class FrozenMeta(type):
    """创建不可修改的类"""
    
    def __new__(mcs, name, bases, attrs):
        cls = super().__new__(mcs, name, bases, attrs)
        
        def frozen_setattr(self, key, value):
            if hasattr(self, '_frozen') and self._frozen:
                raise AttributeError(f"Cannot modify frozen object")
            object.__setattr__(self, key, value)
        
        cls.__setattr__ = frozen_setattr
        return cls
```

---

## 学习检查清单

### 初级（必须掌握）
- [ ] 理解 `__new__` 和 `__init__` 的区别
- [ ] 知道 `type` 是默认元类
- [ ] 能够创建简单的元类
- [ ] 理解元类的基本执行顺序

### 中级（应该掌握）
- [ ] 使用元类实现单例模式
- [ ] 使用元类实现自动注册
- [ ] 理解 `__call__` 方法的作用
- [ ] 能够选择元类 vs 装饰器

### 高级（深入理解）
- [ ] 使用 `__prepare__` 自定义命名空间
- [ ] 解决元类冲突
- [ ] 实现 ORM 风格的模型类
- [ ] 理解 `__init_subclass__` 替代方案

### 专家级（可选）
- [ ] 元类与描述符结合
- [ ] 元类的性能优化
- [ ] 阅读 Django/SQLAlchemy 源码
- [ ] 设计自己的元类框架

---

## 快速命令

```bash
# 查看对象类型
python -c "class M(type): pass; class C(metaclass=M): pass; print(type(C()))"

# 查看元类
python -c "class M(type): pass; class C(metaclass=M): pass; print(type(C))"

# 查看 MRO
python -c "class A: pass; class B(A): pass; print(B.__mro__)"

# 动态创建类
python -c "C = type('C', (), {'x': 10}); print(C, C.x)"
```

---

## 推荐资源

### 文档
- Python 官方文档: Data Model
- PEP 3115: Metaclasses in Python 3000

### 文章
- "A Primer on Python Metaclasses" by Jake VanderPlas
- "Understanding Python metaclasses" by Ionel Cristian Mărieș

### 源码阅读
- Django ORM (`django/db/models/base.py`)
- SQLAlchemy (`sqlalchemy/orm/decl_api.py`)
- attrs library

### 书籍
- "Python Cookbook" 第9章
- "Fluent Python" 第21章

---

**记住：如果你不确定是否需要元类，那你就不需要！**
