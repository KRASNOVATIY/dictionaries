import re
import typing
from collections import Mapping


class Map(dict):
    """
    Класс для хранения атрибутов в стиле Java. Имеет ссылочный тип, но не ссылочный конструктор
    не генерирует исключения при обращении к несуществующему ключу, при удалении несуществующено ключа
    """
    __re__ = re.compile("^__.+__$")
    __protected__ = list()

    def __new__(cls, seq=None, **kwargs):
        instance = super(Map, cls).__new__(typing.cast(typing.Type[Map], cls))  # cast to avoid mypy error
        if not cls.__protected__:
            cls.__protected__ = dir(instance)
        return instance

    def __init__(self, seq=None, **kwargs):
        """
        :param seq: (Mapping) object
        :param kwargs: like a=b
        >>> boris = Map()
        >>> boris.name = "Boris"
        >>> boris.age = 5
        >>> julia = Map({"name": "Julia", "age": 4})
        >>> arman = Map(name="Petr", age=7, sections=["swimming", ["english", "german"]])
        >>> pavel = Map({"name": "Pavel", "age": 1}, info={"eat": {"name": "milk", "volume": 0.25}})
        >>> laura = Map(julia)
        >>> laura.name = "Laura"
        >>> group = Map(users=[boris, julia, arman, pavel, laura], place="White House")
        >>> print(group.users[3].info.eat.name)
        milk
        >>> arman.sections[0] = "running"  # modification saved
        >>> print(group.users[2].sections, group.users[2].sections == arman.sections)
        ['running', ['english', 'german']] True
        >>> print(group.users[2].sections[1][1])
        german
        >>> print(group.none)
        None
        >>> group = Map(boris=boris, julia=julia)
        >>> julia.age += 1 # modification discard
        >>> group.julia.age += 2
        >>> print(julia.age, julia.age == group.julia.age)
        5 False
        >>> print(group)
        {'boris': {'name': 'Boris', 'age': 5}, 'julia': {'name': 'Julia', 'age': 6}}
        """
        if seq is None:
            seq = dict()
        super(Map, self).__init__(seq, **kwargs)
        for k, v in list(seq.items()) + list(kwargs.items()):
            self.check_protected(k)
            if isinstance(v, Mapping):
                self[k] = Map(v)
            else:
                self[k] = v

    def check_protected(self, key):
        """
        :param key: (any immutable) key
        :return:
        >>> example = Map()
        >>> example.item = 4
        >>> example.__doc__ = "Doc"
        Traceback (most recent call last):
            ...
        KeyError: '__doc__ attribute is protected'
        >>> example.__some_other__ = 1
        Traceback (most recent call last):
            ...
        KeyError: '__some_other__ attribute is protected'
        """
        if key in self.__protected__ or self.__re__.match(str(key)):
            raise KeyError("{} attribute is protected".format(key))

    def __getattr__(self, attr):
        return self.get(attr)

    def __setattr__(self, key, value):
        self.check_protected(key)
        self.__setitem__(key, value)

    def __setitem__(self, key, value):
        super(Map, self).__setitem__(key, value)
        self.check_protected(key)
        self.__dict__.update({key: value})

    def __delattr__(self, item):
        self.check_protected(item)
        self.__delitem__(item)

    def __delitem__(self, key):
        self.check_protected(key)
        try:
            super(Map, self).__delitem__(key)
            del self.__dict__[key]
        except KeyError:
            pass

    def _uncover(self, map_object, result, _way=None):
        """
        Метод раскрывает Map дерево в список путей к листьям дерева (рекурсивно)
        Корректно работает со списками списков, но корнем должен быть Мар
        :param map_object: исходый Map объект
        :param result: список путей к листьям, пути оформлены как списки
        :param _way: скрытый атрибут с текущим путём
        :return:
        >>> m = Map({
        ...    1: Map({10: "v10"}),
        ...    2: Map({21: "v21",
        ...            22: "v22",
        ...            23:[Map({231: "v231", 232: "v232"}),
        ...                Map({231: "v231", 232: "v232"}),
        ...                "v230"]}),
        ...    3: "v3",
        ...    4: ["v40", "v41", ["v420", "v421", Map({422: "v422"})], "v43", "v44"]}
        ... )
        >>>
        >>> unc = m.uncover()
        >>> length = len(unc)
        >>> print(unc[:length//2])  # first part
        [[1, 10], [2, 21], [2, 22], [2, 23, 0, 231], [2, 23, 0, 232], [2, 23, 1, 231], [2, 23, 1, 232], [2, 23, 2]]
        >>> print(unc[length//2:])  # second part
        [[3], [4, 0], [4, 1], [4, 2, 0], [4, 2, 1], [4, 2, 2, 422], [4, 3], [4, 4]]
        """
        if not _way:
            _way = list()

        if isinstance(map_object, Map):
            for key in map_object.keys():
                _way.append(key)
                self._uncover(map_object[key], result, _way)
            if _way:
                _way.pop()
        elif isinstance(map_object, list):
            for i, item in enumerate(map_object):
                _way.append(i)
                self._uncover(item, result, _way)
            else:
                _way.pop()
        else:
            result.append(_way[:])
            _way.pop()

    def uncover(self):
        """
        Метод возвращает раскрытое дерево Map
        :return: список путей к листьям
        """
        uncovered = list()
        self._uncover(self, uncovered)
        return uncovered

    def find_key(self, key, at_end_only=False):
        """
        Находит полные пути в дереве с вхождениями ключа
        (служит для поиска путей, содержащих ключ, к листьям)
        :param key: искомый ключ
        :param at_end_only: искать только среди листьев
        :return: итератор с путями
        >>> m = Map({
        ...    10: Map({11: "v11", 12: "v12"}),
        ...    20: Map({
        ...            21: "v21",
        ...            22: "v22",
        ...            23:[Map({231: "v231", 232: "v232"}), Map({231: "v231", 232: ["v2322", "v2323"]}), "v230"]}),
        ...    30: "v3",
        ...    40: ["v41", "v42", ["v431", "v432", Map({433: "v433"})], "v44", "v45"]}
        ... )
        >>> print(list(m.find_key(5)))
        []
        >>> print(list(m.find_key(232)))
        [[20, 23, 0, 232], [20, 23, 1, 232, 0], [20, 23, 1, 232, 1]]
        >>> print(list(m.find_key(433)))
        [[40, 2, 2, 433]]
        >>> print(list(m.find_key(10)))
        [[10, 11], [10, 12]]
        >>> print(list(m.find_key(1)))  # second element of each list inside root Map and its sub-elements
        [[20, 23, 1, 231], [20, 23, 1, 232, 0], [20, 23, 1, 232, 1], [40, 1], [40, 2, 1]]
        >>> print(list(m.find_key(1, True)))  # second element of each list inside root Map
        [[20, 23, 1, 232, 1], [40, 1], [40, 2, 1]]
        """
        # TODO подумать, может стоит добавить параметр для возвращения первого вхождения
        for item in self.uncover():
            if not at_end_only:
                if key in item:
                    yield item
            else:
                if key == item[-1]:
                    yield item

    def get_value(self, way):
        """
        Возвращает значение ключа, имеющего путь way
        :param way: путь к листу дерева
        :return: значение листа
        >>> m = Map({
        ...    10: Map({11: "v11"}),
        ...    20: Map({
        ...            21: "v21",
        ...            22: "v22",
        ...            23:[Map({231: "v231", 232: "v232"}), Map({231: "v231", 232: ["v2322", "v2323"]}), "v230"]}),
        ...    30: "v3",
        ...    40: ["v41", "v42", ["v430", "v431", Map({432: "v432"})], "v44", "v45"]}
        ... )
        >>> print([m.get_value(way) for way in [[20, 23, 0, 232], [20, 23, 1, 232, 0], [20, 23, 1, 232, 1]]])
        ['v232', 'v2322', 'v2323']
        >>> print(m.get_value([40, 2, 2, 432]))
        v432
        >>> print([m.get_value(way) for way in
        ...           [[20, 23, 1, 231], [20, 23, 1, 232, 0], [20, 23, 1, 232, 1], [40, 1], [40, 2, 1]]
        ...        ])
        ['v231', 'v2322', 'v2323', 'v42', 'v431']
        >>> print([m.get_value(way) for way in [[20, 23, 1, 232, 1], [40, 1], [40, 2, 1]]])
        ['v2323', 'v42', 'v431']
        >>> print(m.get_value([0,1,2]))
        Traceback (most recent call last):
            ...
        KeyError: 0
        """
        value = self
        for i in way:
            value = value[i]
        else:
            return value


class IMDict(dict):
    """
    Класс неизменяемого словаря,
    ключи постоянны их нельзя добавлять и удалять
    значения изменяемы
    """
    def __init__(self, *args, **kwargs):
        """
        :param args:
        :param kwargs:
        >>> imd = IMDict(first="First", second="Second")
        >>> imd["second"] = "Last"
        >>> del imd["first"]
        >>> print(imd)
        {'first': None, 'second': 'Last'}
        >>> imd["third"] = "Third"
        Traceback (most recent call last):
            ...
        KeyError: "Unexpected key third, expect ['first', 'second']"
        >>> setattr(imd, "fourth", 4)
        Traceback (most recent call last):
            ...
        AttributeError: 'IMDict' object has no attribute 'fourth'
        >>> setattr(imd, "first", 1)
        Traceback (most recent call last):
            ...
        AttributeError: 'IMDict' object has no attribute 'first'
        >>> print(imd["first"])
        Traceback (most recent call last):
            ...
        ValueError: target value is None
        """
        super(IMDict, self).__init__(*args, **kwargs)
        for k, v in kwargs.items():
            self[k] = v
        self.dict = dict(self)
        self._hash = None

    def __hash__(self):
        if self._hash is None:
            self._hash = hash(frozenset(self.dict.items()))
        return self._hash

    def __setattr__(self, key, value):
        if key == '_hash' or key == 'dict':
            self.__dict__.update({key: value})
        else:
            raise AttributeError("'IMDict' object has no attribute '{}'"
                                 .format(key))

    def __setitem__(self, key, value):
        if key in self:
            super(IMDict, self).__setitem__(key, value)
        elif key == '_hash' or key == 'dict':
            self.__dict__.update({key: value})
        else:
            raise KeyError("Unexpected key {}, expect {}"
                           .format(key, [x for x in self.keys()]))

    def __delitem__(self, key):
        self.__setitem__(key, None)
        pass

    def __delattr__(self, item):
        pass

    def __getitem__(self, item):
        value = super(IMDict, self).__getitem__(item)
        if value is None:
            raise ValueError("target value is None")
        return value

    def update(self, __m, **kwargs):
        """
        update overwritten
        :param __m:
        :param kwargs:
        :return:
        >>> imd = IMDict(first="First", second="Second", fourth="4")
        >>> imd.update({"second": "Last", "third": "Third"}, fourth=4, fifth=5)
        >>> print(imd)
        {'first': 'First', 'second': 'Last', 'fourth': 4}
        """
        updater = __m
        updater.update(kwargs)
        for key in updater:
            if key not in self:
                continue
            else:
                self[key] = updater[key]

    def clear(self):
        """
        :return:
        >>> imd = IMDict(first="First", second="Second", fourth="4")
        >>> imd.clear()
        >>> print(imd)
        {'first': None, 'second': None, 'fourth': None}
        """
        for item in self.dict:
            del self[item]

    def popitem(self):
        """
        :return:
        >>> imd = IMDict(first="First", second="Second", fourth="4")
        >>> imd.popitem()
        ('fourth', '4')
        >>> print(imd)
        {'first': 'First', 'second': 'Second', 'fourth': None}
        >>> imd.popitem()
        ('second', 'Second')
        >>> print(imd)
        {'first': 'First', 'second': None, 'fourth': None}
        >>> imd.popitem()
        ('first', 'First')
        >>> imd.popitem()
        Traceback (most recent call last):
            ...
        ValueError: popitem(): dictionary values are all None
        """
        for i in range(len(self)):
            pop_index = -i-1
            pop_key = list(self.keys())[pop_index]
            pop_value = list(self.values())[pop_index]
            if pop_value is not None:
                pair = pop_key, self[pop_key]
                self[pop_key] = None
                return pair
        raise ValueError('popitem(): dictionary values are all None')

    def is_empty(self):
        """
        :return:
        >>> imd = IMDict(first="First", second="Second")
        >>> print(imd.is_empty())
        False
        >>> imd["second"] = None
        >>> imd.popitem()
        ('first', 'First')
        >>> print(imd.is_empty())
        True
        """
        for value in self.values():
            if value is not None:
                return False
        return True

    def pop(self, k, d=None):
        """
        :param k:
        :param d:
        :return:
        >>> imd = IMDict(first="First", second="Second", fourth="4")
        >>> imd.pop("second")
        ('second', 'Second')
        >>> print(imd)
        {'first': 'First', 'second': None, 'fourth': '4'}
        >>> imd.pop("second")
        Traceback (most recent call last):
            ...
        ValueError: target value is None
        >>> print(imd['first'])
        First
        >>> print(getattr(imd, "first"))
        Traceback (most recent call last):
            ...
        AttributeError: 'IMDict' object has no attribute 'first'
        >>> print(imd['second'])
        Traceback (most recent call last):
            ...
        ValueError: target value is None
        >>> print("first" in imd)
        True
        """
        if k in self:
            pair = k, self[k]
            self[k] = None
            return pair
        elif d:
            return k, d
        else:
            raise KeyError("Unexpected key {}, expect {}".format(k, self.keys()))
