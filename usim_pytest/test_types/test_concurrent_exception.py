import pytest

from usim import Concurrent


class TestConcurrent:
    """Test the semantics of ``usim.Concurrent``"""
    def test_generic(self):
        """Generic ``Concurrent`` is a catch-all"""
        with pytest.raises(Concurrent):
            raise Concurrent()
        with pytest.raises(Concurrent):
            raise Concurrent(KeyError())
        with pytest.raises(Concurrent):
            raise Concurrent(IndexError())
        with pytest.raises(Concurrent):
            raise Concurrent(KeyError(), IndexError())

    def test_specialised_single(self):
        """Specialised ``Concurrent[a]`` catches only ``Concurrent(a())``"""
        with pytest.raises(Concurrent[IndexError]):
            raise Concurrent(IndexError())
        with pytest.raises(Concurrent[KeyError]):
            raise Concurrent(KeyError())
        # check that inner test does not catch
        with pytest.raises(Concurrent[KeyError]):
            with pytest.raises(Concurrent[IndexError]):
                raise Concurrent(KeyError())
        with pytest.raises(Concurrent[IndexError]):
            with pytest.raises(Concurrent[KeyError]):
                raise Concurrent(IndexError())

    def test_specialised_multi(self):
        """Specialised ``Concurrent[a, b]`` catches only ``Concurrent(a(), b())``"""
        with pytest.raises(Concurrent[IndexError, KeyError]):
            raise Concurrent(IndexError(), KeyError())
        with pytest.raises(Concurrent[TypeError, ValueError]):
            raise Concurrent(TypeError(), ValueError())
        # reverse order
        with pytest.raises(Concurrent[IndexError, KeyError]):
            raise Concurrent(KeyError(), IndexError())
        with pytest.raises(Concurrent[TypeError, ValueError]):
            raise Concurrent(ValueError(), TypeError())
        # check that inner test does not catch
        with pytest.raises(Concurrent[IndexError, KeyError, ValueError]):
            with pytest.raises(Concurrent[IndexError, KeyError]):
                with pytest.raises(Concurrent[KeyError, ValueError]):
                    raise Concurrent(IndexError(), KeyError(), ValueError())

    def test_specialised_single_open(self):
        """Specialised ``Concurrent[a, ...]`` catches any ``Concurrent(a(), ...)``"""
        with pytest.raises(Concurrent[IndexError, ...]):
            raise Concurrent(IndexError())
        with pytest.raises(Concurrent[IndexError, ...]):
            raise Concurrent(IndexError(), KeyError())
        with pytest.raises(Concurrent[IndexError, ...]):
            raise Concurrent(IndexError(), TypeError(), KeyError())
        # check that inner test does not catch
        with pytest.raises(Concurrent[KeyError, ...]):
            with pytest.raises(Concurrent[IndexError, ...]):
                raise Concurrent(KeyError(), ValueError())
        with pytest.raises(Concurrent[IndexError, ...]):
            with pytest.raises(Concurrent[KeyError, ...]):
                raise Concurrent(IndexError(), ValueError())

    def test_specialised_multi_open(self):
        """Specialised ``Concurrent[a, ...]`` catches any ``Concurrent(a(), ...)``"""
        with pytest.raises(Concurrent[IndexError, KeyError, ...]):
            raise Concurrent(IndexError(), KeyError())
        with pytest.raises(Concurrent[IndexError, KeyError, ...]):
            raise Concurrent(IndexError(), KeyError(), ValueError())
        # check that inner test does not catch
        with pytest.raises(Concurrent[KeyError, ValueError, ...]):
            with pytest.raises(Concurrent[IndexError, ValueError, ...]):
                raise Concurrent(KeyError(), ValueError())
        with pytest.raises(Concurrent[IndexError, ValueError, ...]):
            with pytest.raises(Concurrent[KeyError, ValueError, ...]):
                raise Concurrent(IndexError(), ValueError())
