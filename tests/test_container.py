import abc
import sys
from collections import namedtuple

from typing import (
    Callable,
    IO,
    List,
    Type,
    TypeVar,
    NamedTuple,
)

import pytest

from py_ioc.container import (
    Container,
    SINGLETON,
)
from py_ioc.exceptions import (
    ResolutionError,
    BindingError,
)


class TestContainer:
    def test_make_simple_autowiring_with_concrete_annotations(self):
        class X:
            pass

        class Y:
            def __init__(self, x: X):
                self.x = x

        container = Container()
        y = container.make(Y)
        assert isinstance(y, Y)
        assert isinstance(y.x, X)

    def test_make_simple_autowiring_with_abstract_annotations(self):
        class X:
            pass

        class XX(X):
            pass

        class Y:
            def __init__(self, x: X):
                self.x = x

        container = Container()
        container.bind(X, XX)
        y = container.make(Y)
        assert isinstance(y, Y)
        assert isinstance(y.x, X)
        assert isinstance(y.x, XX)

    def test_make_simple_autowiring_with_factory_method_annotations(self):
        class X:
            pass

        class Y:
            def __init__(self, x: X):
                self.x = x

        def make_x():
            x = X()
            x.foo = 'bar'
            return x

        container = Container()
        container.bind(X, make_x)
        y = container.make(Y)
        assert isinstance(y, Y)
        assert isinstance(y.x, X)
        assert y.x.foo == 'bar'

    def test_make_raises_if_not_concrete(self):
        class X(abc.ABC):
            @abc.abstractmethod
            def foo(self):
                pass

        container = Container()
        with pytest.raises(ResolutionError):
            container.make(X)

    def test_make_string_argument_works(self):
        def make_n():
            return 5

        container = Container()
        container.bind('n', make_n)
        assert container.make('n') == 5

    def test_make_string_argument_in_subrequirement(self):
        class X:
            def __init__(self, arg: 'n'):  # type: ignore  # noqa: F821
                self.arg = arg

        def make_n():
            return 5

        container = Container()
        container.bind('n', make_n)
        assert container.make(X).arg == 5

    def test_make_is_not_caching_instances(self):
        class X:
            pass

        container = Container()
        x1 = container.make(X)
        x2 = container.make(X)
        assert x1 is not x2

    def test_make_passes_kwargs(self):
        class X:
            def __init__(self, foo):
                self.foo = foo

        container = Container()
        x = container.make(X, {'foo': 'bar'})
        assert x.foo == 'bar'

    def test_make_with_singletons(self):
        class X:
            pass

        container = Container()
        container.bind(X, X, lifetime_strategy=SINGLETON)
        x1 = container.make(X)
        x2 = container.make(X)
        assert x1 is x2

    def test_make_will_inject_container(self):
        def returns_arg(c: Container):
            return c

        container = Container()
        arg = container.make(returns_arg)
        assert arg is container

    # requires python >= 3.6
    # def test_make_injects_class_annotations(self):
    #     class X:
    # pass
    #
    #     class Y:
    #         foo: X
    #
    #     container = Container()
    #     y = container.make(Y)
    #     assert isinstance(y.foo, X)

    def test_make_supports_contextual_binding(self):
        class X:
            def __init__(self, foo):
                self.foo = foo

        class Y1:
            def __init__(self, x: X):
                self.x = x

        class Y2:
            def __init__(self, x: X):
                self.x = x

        container = Container()
        container.bind_contextual(when=Y1, wants=X, give=lambda: X('bar1'))
        container.bind_contextual(when=Y2, wants=X, give=lambda: X('bar2'))

        y1 = container.make(Y1)
        y2 = container.make(Y2)
        assert y1.x.foo == 'bar1'
        assert y2.x.foo == 'bar2'

    def test_make_supports_contextual_binding_with_varname(self):
        class X:
            def __init__(self, foo):
                self.foo = foo

        class Y:
            def __init__(self, x1: X, x2: X):
                self.x1 = x1
                self.x2 = x2

        container = Container()
        container.bind_contextual(when=Y, wants=X, called='x1', give=lambda: X('bar1'))
        container.bind_contextual(when=Y, wants=X, called='x2', give=lambda: X('bar2'))

        y = container.make(Y)
        assert y.x1.foo == 'bar1'
        assert y.x2.foo == 'bar2'

    def test_make_supports_contextual_binding_with_only_varname(self):
        class X:
            def __init__(self, foo):
                self.foo = foo

        class Y:
            def __init__(self, x1, x2):
                self.x1 = x1
                self.x2 = x2

        container = Container()
        container.bind_contextual(when=Y, called='x1', give=lambda: X('bar1'))
        container.bind_contextual(when=Y, called='x2', give=lambda: X('bar2'))

        y = container.make(Y)
        assert y.x1.foo == 'bar1'
        assert y.x2.foo == 'bar2'

    @pytest.mark.parametrize('typ', [str, bytes, int, bool, bytearray, float, complex, dict, tuple, list, set,
                                     frozenset, property, range, slice, object])
    def test_make_does_not_create_builtin_types(self, typ):
        container = Container()
        with pytest.raises(ResolutionError):
            container.make(typ)

    @pytest.mark.parametrize('typ', [List[object], Type[int], TypeVar('T', int, float), Callable, IO, NamedTuple])
    def test_make_does_not_create_typing_hints(self, typ):
        container = Container()
        with pytest.raises(ResolutionError):
            container.make(typ)

    def test_make_contextual_with_builtin_type(self):
        class X:
            def __init__(self, foo: str):
                self.foo = foo

        container = Container()
        container.bind_contextual(when=X, wants=str, called='foo', give=lambda: 'bar')
        x = container.make(X)
        assert x.foo == 'bar'

    def test_make_does_not_support_varname_only_binding_if_annotations_used(self):
        class X:
            def __init__(self, foo: str):
                self.foo = foo

        class Y:
            def __init__(self, x1: X, x2: X):
                self.x1 = x1
                self.x2 = x2

        container = Container()
        container.bind_contextual(when=Y, called='x1', give=lambda: X('foo'))
        container.bind_contextual(when=Y, called='x2', give=lambda: X('bar'))

        with pytest.raises(ResolutionError):
            container.make(Y)

    def test_bind_contextual_needs_either_varname_or_needs_arg(self):
        container = Container()
        with pytest.raises(BindingError):
            container.bind_contextual(when=object, give=object)

    def test_contextual_bindings_does_not_override_global_singleton(self):
        class X:
            pass

        class Y:
            def __init__(self, x: X):
                self.x = x

        container = Container()
        container.bind(X, X, SINGLETON)
        container.bind_contextual(when=Y, wants=X, give=X)

        x1 = container.make(X)
        x2 = container.make(X)
        assert x1 is x2

        y = container.make(Y)
        assert y.x is not x1
        assert isinstance(y.x, X)

    def test_contextual_bindings_singleton(self):
        class X:
            pass

        class Y:
            def __init__(self, x: X):
                self.x = x

        container = Container()
        container.bind_contextual(when=Y, wants=X, give=X, lifetime_strategy=SINGLETON)

        x1 = container.make(X)
        x2 = container.make(X)
        assert x1 is not x2

        y1 = container.make(Y)
        y2 = container.make(Y)
        assert y1.x is not x1
        assert y1.x is y2.x

    @pytest.mark.skipif(sys.version_info < (3, 7), reason="requires dataclasses, added in python3.7")
    def test_make_supports_dataclasses(self):
        from dataclasses import dataclass

        class X:
            pass

        @dataclass
        class Y:
            x: X

        @dataclass
        class Z:
            y: Y

        container = Container()
        y = container.make(Y)
        z = container.make(Z)

        assert isinstance(y.x, X)
        assert isinstance(z.y, Y)

    def test_make_does_not_auto_create_namedtuple(self):
        class X:
            pass

        Y = namedtuple('Y', ['x'])

        container = Container()
        with pytest.raises(ResolutionError):
            container.make(Y)

    def test_make_raises_if_no_annotation(self):
        class X:
            def __init__(self, foo): pass

        container = Container()
        with pytest.raises(ResolutionError):
            container.make(X)

    def test_make_handles_None_annotation(self):
        class X:
            def __init__(self, foo: None):
                self.foo = foo

        container = Container()
        x = container.make(X)
        assert x.foo is None

    def test_make_does_support_namedtuple_contextual_binding(self):
        class X:
            pass

        Y = namedtuple('Y', ['x'])

        container = Container()
        container.bind_contextual(when=Y, called='x', give=X)
        y = container.make(Y)
        assert isinstance(y.x, X)

    def test_make_does_not_save_singleton_if_explicit_init_kwargs_set(self):
        class X:
            def __init__(self, foo: str):
                self.foo = foo

        container = Container()
        container.bind(X, lambda: X('foo'), SINGLETON)
        x1 = container.make(X)
        x2 = container.make(X, {'foo': 'bar'})
        x3 = container.make(X)

        assert x1.foo == 'foo'
        assert x3 is x1
        assert x2.foo == 'bar'
        assert x2 is not x1

    def test_make_caching_fibonacci(self):
        """A more complete quasi-real-life test"""
        class KeyValueDatabase(abc.ABC):
            @abc.abstractmethod
            def get(self, key): pass

            @abc.abstractmethod
            def has(self, key): pass

            @abc.abstractmethod
            def set(self, key, value): pass

        class MemoryStore(KeyValueDatabase):
            def __init__(self, initial_data: dict):
                self.data = initial_data

            def set(self, key, value):
                self.data[key] = value

            def has(self, key):
                return key in self.data

            def get(self, key):
                return self.data[key]

        class CachingFibonacci:
            def __init__(self, cache: KeyValueDatabase):
                self.cache = cache

            def calculate(self, n: int):
                if n in {0, 1}:
                    return n
                if self.cache.has(n):
                    return self.cache.get(n)
                return self.calculate(n-1) + self.calculate(n-2)

        container = Container()
        with pytest.raises(ResolutionError, match=str(KeyValueDatabase)):
            container.make(CachingFibonacci)

        container.bind(KeyValueDatabase, MemoryStore)
        with pytest.raises(ResolutionError):
            container.make(CachingFibonacci)

        container.bind_contextual(when=MemoryStore, wants=dict, called='initial_data', give=lambda: {})
        fib = container.make(CachingFibonacci)
        assert fib.calculate(6) == 8
