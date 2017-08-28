#!/usr/bin/python3
# coding: utf-8

"""
Access to Windows Registry data as if a Unix file path.

As a reminder, Windows Registry as organized as follow:
    - keys store values, they're like folders
    - values stores data, they're like files
    - data is like the content of the file

Access is based upon standard winreg module:
        https://docs.python.org/3/library/winreg.html
"""

import contextlib
import os.path

import winreg

KEY_ROOT = winreg.HKEY_LOCAL_MACHINE


class Registry(object):
    """
    Access to Windows registry as a dict-like object.

    Args:
        key: open predefined key
        subkey (str): subkey to open
        access (str): access mode ('r'|'w'|'rw')
        create (bool): create requested key if missing

    Dict-like access implies a convention on how to access key and value, because a subkey and a
    subvalue can share same name.

    We choose to have values prefixed with a heading dot. As so, "egg" key is referenced by "egg",
    while "egg" value is referenced by ".egg". It's like visible and hidden files on Unix systems.

    Keys can be created recursively (ex: 'egg\spam' can be created without creating egg first), but
    keys can't be deleted if subkeys still exist.
    Value can't be created if key missing (ex: 'spam\.rabbit' will fail if spam missing).

    The registry type of the data is deduced from its Python type. The following mapping occurs:
        - bytes: winreg.REG_BINARY,
        - int: winreg.REG_DWORD,
        - str: winreg.REG_SZ,
        - list: winreg.REG_MULTI_SZ

    The following types are not handled:
        - tuple, because it's not either in the winreg module, use list instead
        - float, because it's not either in the Windows Registry

    For list data, all items in the list must be strings.

    Raises:
        FileNotFoundError: key or subkey does not refer to an existing path in registry
    """

    SUBKEY_ROOT = r''

    ACCESS_MAPPING = {
        'r': winreg.KEY_READ,
        'w': winreg.KEY_WRITE,
        'rw': winreg.KEY_ALL_ACCESS
    }

    TYPE_MAPPING = {
        bytes: winreg.REG_BINARY,
        int: winreg.REG_DWORD,
        str: winreg.REG_SZ,
        list: winreg.REG_MULTI_SZ
    }

    # def __init__(self, computer=None, key=winreg.HKEY_LOCAL_MACHINE):
    def __init__(self, key=KEY_ROOT, subkey='', access='r', _noneisdel=False):
        # self.key = winreg.ConnectRegistry(computer, key)
        self.access = access
        self.winreg_access = __class__.ACCESS_MAPPING[access]

        if isinstance(key, int):
            subkey = os.path.join(__class__.SUBKEY_ROOT, subkey)

        self.registry_handle = winreg.OpenKeyEx(key, subkey, 0, self.winreg_access)

        self._noneisdel = _noneisdel  # internal use only, special use of __setitem__ for deletion

    def keys(self):
        i = 0
        try:
            while True:
                key = winreg.EnumKey(self.registry_handle, i)
                yield key
                i += 1
        except OSError:
            pass

    def values(self):
        i = 0
        try:
            while True:
                value = winreg.EnumValue(self.registry_handle, i)
                yield value[:2]  # we don't need extra info?
                i += 1
        except OSError:
            pass

    @staticmethod
    def _parse_keyval(regpath):
        """
        Split key in (key, value) or (value, data), depending on what is provided.

        Exemple::

            'egg'           =>  ('egg', '')
            '.spam'         =>  ('', 'spam')
            r'egg\.spam'    =>  ('egg', 'spam')
        """
        regpath = regpath.replace(r'\.', '.')  # format to take advantage of os.path.splitext
        subkey, value = os.path.splitext(regpath)
        if subkey.startswith('.'):
            # only value was provided as path,
            # so value is in subkey here: we invert subkey and value
            subkey, value = value, subkey
        return subkey, value

    def __getitem__(self, regpath):
        subkey, value = self._parse_keyval(regpath)
        if not subkey:  # value is fetched in current key
            data, _ = winreg.QueryValueEx(self.registry_handle, value[1:])
            return data
        else:
            registry = self.__class__(self.registry_handle, subkey, self.access, self._noneisdel)
            if value:  # value is fetched in subkey
                data = registry[value]
                return data
            else:  # subkey is fetched
                return registry

    def __setitem__(self, regpath, content):
        if (content is None) and (self._noneisdel):
            del self[regpath]
        else:
            subkey, value = self._parse_keyval(regpath)
            if not subkey:  # data is set in current value
                winreg.SetValueEx(
                    self.registry_handle,
                    value[1:],
                    0,
                    __class__.TYPE_MAPPING[type(content)],
                    content
                )
            elif value:  # data is set in subkey
                registry = self.__class__(
                    self.registry_handle,
                    subkey,
                    self.access,
                    self._noneisdel
                )
                registry[value] = content
            else:
                if (content is None) or (content == {}):  # key is created
                    winreg.CreateKeyEx(self.registry_handle, subkey, 0, self.winreg_access)
                else:  # key structure is loaded
                    self[subkey] = {}
                    self[subkey].load(content)

    def get(self, regpath, default=None):
        try:
            item = self.__getitem__(regpath)
        except FileNotFoundError:
            return default
        return item

    def __delitem__(self, regpath):
        subkey, value = self._parse_keyval(regpath)
        if not subkey:
            winreg.DeleteValue(self.registry_handle, value[1:])
        elif not value:
            registry = self.__class__(self.registry_handle, subkey, self.access, self._noneisdel)
            for innerkey in list(registry.keys()):  # fill list first as keys are edited in the loop
                del registry[innerkey]  # delete keys recursively
            winreg.DeleteKeyEx(self.registry_handle, subkey)  # FIXME? access 64bits?
        else:
            registry = self.__class__(self.registry_handle, subkey, self.access, self._noneisdel)
            del registry[value]

    def close(self):  # TODO: integrate automatically (context manager?)
        winreg.CloseKey(self.registry_handle)

    def dump(self, _result=None):
            """
            Recursively dump the content of the registry key into a dictionary.
            """
            result = _result if _result else {}
            # dump values
            values = {
                f'.{value}': data for value, data in self.values()
            }
            # dump subkeys
            keys = {
                key: self[key].dump() for key in self.keys()
            }

            result.update(values)
            result.update(keys)

            return result

    def load(self, content):
        if not isinstance(content, dict):
            raise ValueError(f"Content must be a dict, received '{content}'")
        for key, value in content.items():
            if isinstance(value, dict):
                self[key] = {}
                self[key].load(value)
            else:
                self[key] = value


def get_from_root(regpath, default=None):
    registry = Registry()
    return registry.get(regpath, default)


def set_from_root(regpath, data):
    registry = Registry(access='w')
    registry[regpath] = data


def del_from_root(regpath):
    registry = Registry(access='rw')  # del needs read access too for recursive deletion
    del registry[regpath]

@contextlib.contextmanager
def registry_bubble(subkey, content, key=KEY_ROOT):
    """
    Edit registry values within the scope of the context manager, and restore them afterwards.

    DISCLAIMER: if you edit backup values in your code without knowing what you do, you'll may
    prevent the bubble to properly restore registry values.

    Usage example::

        content = {
            TODO
        }
        with registry_bubble(content):
            pass  # do whatever you want here, keys are the one you specified
        # here, keys are restored to their original state
    """

    def _add_to_backup(content, backup):
        """
        Add to backup keys to delete because they were created withing the bubble.
        """
        for key, value in content.items():
            if backup.get(key) is None:
                backup[key] = None
            elif isinstance(value, dict):
                _add_to_backup(content[key], backup[key])

    root = Registry(key, subkey, access='rw', _noneisdel=True)
    backup = root.dump()
    _add_to_backup(content, backup)

    root.load(content)
    yield
    root.load(backup)
