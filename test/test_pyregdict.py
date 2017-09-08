#!/usr/bin/python3
# coding: utf-8

import os.path
import subprocess

import pytest

import pyregdict


# TODO: add cases expecting exception

def test_connexion():
    pyregdict.Registry()
    pyregdict.Registry(subkey='SOFTWARE')
    pyregdict.Registry(subkey=r'HARDWARE\DESCRIPTION')


def test_access(request):
    """
    Test registry access modes.

    Access modes apply only to values, not keys.
    """

    def _cleanup():
        regcleanfile = os.path.join(
            os.path.dirname(__file__),
            'cleanup_test_access.reg'
        )
        subprocess.run(['reg', 'import', regcleanfile], check=True)
    request.addfinalizer(_cleanup)

    software = pyregdict.Registry(subkey='SOFTWARE')
    software['egg'] = None
    with pytest.raises(PermissionError):
        software['.spam'] = 'bacon'  # fails because access mode is read-only

    egg = pyregdict.Registry(subkey=r'SOFTWARE\egg', access='w')
    egg['.spam'] = 'bacon'
    with pytest.raises(PermissionError):
        egg['.spam']  # fails because access mode is write-only

    egg = pyregdict.Registry(subkey=r'SOFTWARE\egg', access='r')
    assert egg['.spam'] == 'bacon'
    with pytest.raises(PermissionError):
        del egg['.spam']  # fails because access mode is read-only

    egg = pyregdict.Registry(subkey=r'SOFTWARE\egg', access='rw')
    assert egg['.spam'] == 'bacon'
    del egg['.spam']
    egg['.spam'] = 'bacon'
    assert egg['.spam'] == 'bacon'


class TestPixarMoviesWithCleanup:

    @pytest.fixture(scope='function', autouse=True)
    def cleanup_pixarmovies(self):
        yield
        regcleanfile = os.path.join(
            os.path.dirname(__file__),
            'cleanup_pixarmovies.reg'
        )
        subprocess.run(['reg', 'import', regcleanfile], check=True)

    def test_api_regpath(self):
        """
        Various manipulation on registry, accessing data as regpaths.
        """

        software = pyregdict.Registry(subkey='SOFTWARE', access='rw')

        software['PixarMovies'] = None

        software[r'PixarMovies\.count'] = 1
        software[r'PixarMovies\Ratatouille'] = None
        software[r'PixarMovies\Ratatouille\.year'] = b'2007'
        software[r'PixarMovies\Ratatouille\.director'] = 'Brad Bird'
        software[r'PixarMovies\Ratatouille\.characters'] = ['Remy', 'Alfredo Linguini', 'Anton Ego']

        assert software[r'PixarMovies\.count'] == 1
        assert software[r'PixarMovies\Ratatouille\.year'] == b'2007'
        assert software[r'PixarMovies\Ratatouille\.director'] == 'Brad Bird'
        assert software[r'PixarMovies\Ratatouille\.characters'] == [
            'Remy', 'Alfredo Linguini', 'Anton Ego'
        ]

        del software[r'PixarMovies\Ratatouille\.year']
        assert 'year' not in software[r'PixarMovies\Ratatouille'].values()
        del software[r'PixarMovies\Ratatouille\.director']
        del software[r'PixarMovies\Ratatouille\.characters']

        del software[r'PixarMovies\Ratatouille']
        assert 'Ratatouille' not in software['PixarMovies'].keys()

        del software[r'PixarMovies\.count']
        assert 'count' not in software['PixarMovies'].values()

        del software['PixarMovies']
        assert 'PixarMovies' not in software.keys()

    def test_api_walking(self, request):
        """
        Various Manipulations on the registry, walking through the dictionary.
        """
        software = pyregdict.Registry(subkey='SOFTWARE', access='rw')

        software['PixarMovies'] = None

        pixarmovies = software['PixarMovies']
        pixarmovies['.count'] = 1
        pixarmovies['Ratatouille'] = None
        ratatouille = pixarmovies['Ratatouille']
        ratatouille['.year'] = b'2007'
        ratatouille['.director'] = 'Brad Bird'
        ratatouille['.characters'] = ['Remy', 'Alfredo Linguini', 'Anton Ego']

        assert pixarmovies[r'.count'] == 1
        assert ratatouille[r'.year'] == b'2007'
        assert ratatouille['.director'] == 'Brad Bird'
        assert ratatouille['.characters'] == ['Remy', 'Alfredo Linguini', 'Anton Ego']

        del ratatouille['.year']
        assert 'year' not in ratatouille.values()
        del ratatouille['.director']
        del ratatouille['.characters']

        del pixarmovies['Ratatouille']
        assert 'Ratatouille' not in pixarmovies.keys()

        del pixarmovies['.count']
        assert 'count' not in pixarmovies.values()

        del software['PixarMovies']
        assert 'PixarMovies' not in software.keys()

    def test_load(self):
        """
        Set a whole registry structure in one shot.
        """
        software = pyregdict.Registry(subkey='SOFTWARE', access='rw')
        software['PixarMovies'] = {
            '.count': 1,
            'Ratatouille': {
                '.year': b'2007',
                '.director': 'Brad Bird',
                '.characters': ['Remy', 'Alfredo Linguini', 'Anton Ego']
            }
        }
        assert 'PixarMovies' in list(software.keys())
        assert software['PixarMovies'].dump() == {
                '.count': 1,
                'Ratatouille': {
                    '.characters': ['Remy', 'Alfredo Linguini', 'Anton Ego'],
                    '.director': 'Brad Bird',
                    '.year': b'2007'
                }
        }

    class TestPixarMoviesWithSetup:

        @pytest.fixture(scope='function', autouse=True)
        def setup_pixarmovies(self):
            regcleanfile = os.path.join(
                os.path.dirname(__file__),
                'setup_pixarmovies.reg'
            )
            subprocess.run(['reg', 'import', regcleanfile], check=True)

        def test_recursive_del(self):
            """
            Test the deletion of a while registry structure in one shot.
            """

            software = pyregdict.Registry(subkey='SOFTWARE', access='rw')
            del software['PixarMovies']
            assert 'PixarMovies' not in list(software.keys())

        def test_enumerate(self):
            pixarmovies = pyregdict.Registry(subkey=r'SOFTWARE\PixarMovies')

            assert list(sorted(pixarmovies.keys())) == list(sorted(['Ratatouille', 'Up']))
            assert list(sorted(pixarmovies.values())) == list(sorted([('count', 2)]))

            ratatouille = pixarmovies['Ratatouille']
            assert list(sorted(ratatouille.keys())) == list()
            assert list(sorted(ratatouille.values())) == list(sorted([
                ('year', b'2007'),
                ('director', 'Brad Bird'),
                ('characters', ['Remy', 'Alfredo Linguini', 'Anton Ego'])
            ]))

        def test_dump(self):

            pixarmovies = pyregdict.Registry(subkey=r'SOFTWARE\PixarMovies')

            regdump = pixarmovies.dump()
            assert regdump == {
                '.count': 2,
                'Ratatouille': {
                    '.characters': ['Remy', 'Alfredo Linguini', 'Anton Ego'],
                    '.director': 'Brad Bird',
                    '.year': b'2007'
                },
                'Up': {
                    '.director': 'Pete Docter'
                }
            }

        def test_from_root(self, request):

            def _restore_subkey_root():
                pyregdict.Registry.SUBKEY_ROOT = ''
            request.addfinalizer(_restore_subkey_root)

            pyregdict.Registry.SUBKEY_ROOT = r'SOFTWARE\PixarMovies'
            assert pyregdict.get_from_root('.count') == 2
            pyregdict.del_from_root('Ratatouille')
            assert pyregdict.get_from_root('Ratatouille') is None
            pyregdict.set_from_root('.count', 1)
            assert pyregdict.get_from_root('.count') == 1
            pyregdict.del_from_root('.count')
            assert pyregdict.get_from_root('.count') is None

        def test_registry_bubble(self):
            content = {
                '.count': 3,  # editing existing value
                'Ratatouille': {  # editing existing key
                    '.year': None,  # deleting existing value
                    '.director': 'Bird Bard',  # editing existing value
                    '.rank': 10  # add new value
                },
                'Up': None,  # deleting existing key
                'Wall-E': {  # add a new key
                    '.director': 'Andrew Stanton',
                    'comments': {
                        '.Yakafokon': 'The future or the present?'
                    }
                }
            }
            pixarmovies = pyregdict.Registry(subkey=r'SOFTWARE\PixarMovies')
            with pyregdict.registry_bubble(r'SOFTWARE\PixarMovies', content):
                assert pixarmovies.dump() == {
                    '.count': 3,
                    'Ratatouille': {
                        '.characters': ['Remy', 'Alfredo Linguini', 'Anton Ego'],
                        '.director': 'Bird Bard',
                        '.rank': 10
                    },
                    'Wall-E': {
                        '.director': 'Andrew Stanton',
                        'comments': {
                            '.Yakafokon': 'The future or the present?'
                        }
                    }
                }
            assert pixarmovies.dump() == {
                '.count': 2,
                'Ratatouille': {
                    '.characters': ['Remy', 'Alfredo Linguini', 'Anton Ego'],
                    '.director': 'Brad Bird',
                    '.year': b'2007'
                },
                'Up': {
                    '.director': 'Pete Docter'
                }
            }
