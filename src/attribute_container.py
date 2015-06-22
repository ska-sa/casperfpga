__author__ = 'paulp'


class AttributeContainer(object):
    """An iterable class to make registers, snapshots, etc more accessible.
    """

    def __init__(self):
        self.clear()

    def __getitem__(self, item_to_get):
        """
        This means we can access the attributes of this class like a dictionary.
        :param item_to_get: the name of the attribute we want to get
        :return: the attribute value
        """
        return self.__getattribute__(item_to_get)

    def __setattr__(self, name, value):
        try:
            if name != '_next_item':
                self._items.append(name)
        except AttributeError:
            pass
        object.__setattr__(self, name, value)

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

    def clear(self):
        self.__dict__.clear()
        self._next_item = 0
        self._items = []

    def names(self):
        return self._items

    def __len__(self):
        return len(self._items)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        keys = self.__dict__.keys()
        keys.pop(keys.index('_next_item'))
        keys.pop(keys.index('_items'))
        return str(keys)
