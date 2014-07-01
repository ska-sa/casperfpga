__author__ = 'paulp'


class AttributeContainer(object):
    """An iterable class to make registers, snapshots, etc more accessible.
    """

    def __init__(self):
        self._next_item = 0
        self._items = []

    def __setattr__(self, name, value):
        try:
            if name != '_next_item':
                self._items.append(name)
        except AttributeError:
            pass
        object.__setattr__(self, name, value)

    def __str__(self):
        return str(self.__dict__)

    def __iter__(self):
        return self

    def __next__(self):
        try:
            item_name = self._items[self._next_item]
        except:
            self._next_item = 0
            raise StopIteration
        else:
            self._next_item += 1
            return getattr(self, item_name)

    def next(self):  # Python 2 compat
        return self.__next__()

    def names(self):
        return self._items

    def __len__(self):
        return len(self._items)