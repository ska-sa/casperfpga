import logging

LOGGER = logging.getLogger(__name__)


class AttributeContainer(object):
    """
    An iterable class to make registers, snapshots, etc more accessible.
    """
    def __init__(self):
        self._items = None
        self.clear()

    def __getitem__(self, item_to_get):
        """
        This means we can access the attributes of this class like a dictionary.

        :param item_to_get: the name of the attribute we want to get
        :return: the attribute value
        """
        # TODO - add regex support to allow wildcards
        # import re
        # # add regex support
        # try:
        #     regex = re.compile(item_to_get)
        # except re.error:
        return self.__getattribute__(item_to_get)

    def __setattr__(self, name, value):
        """

        :param name:
        :param value:
        :return:
        """
        if not hasattr(self, '_items') and (name != '_items'):
            raise ValueError('Cannot add attribute %s until _item has '
                             'been created.' % name)
        if name == '_items':
            super(AttributeContainer, self).__setattr__(name, value)
            return
        # special case for items that have a write_single method. so ugly. :/
        # this enables a shortcut to write single-value registers
        if name in self._items:
            attr = getattr(self, name)
            if hasattr(attr, 'write_single'):
                getattr(attr, 'write_single')(value)
                LOGGER.debug('To reassign this attribute, you\'re going to '
                             'need to call remove_attribute first.')
                return
            # you need to remove an attribute first to reassign it
            raise AttributeError('Cannot reassign an attribute without'
                                 'calling remove_attribute first.')
        # add it to the _items list and to our __dict__
        self._items.append(name)
        super(AttributeContainer, self).__setattr__(name, value)

    def __iter__(self):
        return (getattr(self, n) for n in self._items)

    def remove_attribute(self, attribute):
        """
        Remove an attribute from this container by name.

        :param attribute: the name of the attribute to remove
        """
        self._items.pop(self._items.index(attribute))
        self.__delattr__(attribute)

    def clear(self):
        self.__dict__.clear()
        self._items = []

    def names(self):
        return self._items

    def keys(self):
        return self._items

    def __len__(self):
        return len(self._items)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        keys = self.__dict__.keys()
        keys.pop(keys.index('_items'))
        return str(keys)
