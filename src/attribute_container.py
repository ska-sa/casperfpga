__author__ = 'paulp'
import threading


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
        return (getattr(self, n) for n in self._items)

    def remove_attribute(self, attribute):
        """
        Remove an attribute from this container by name.
        :param attribute: the name of the attribute to remove
        :return:
        """
        self._items.pop(self._items.index(attribute))
        self.__delattr__(attribute)

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
