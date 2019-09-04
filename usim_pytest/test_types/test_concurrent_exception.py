import pytest

from usim import Concurrent


class FakeConcurrent:
    """Fake of ``Concurrent`` that offers some fields but is not a subclass"""
    template = BaseException


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
        """``Concurrent[a]`` matches only ``Concurrent(a())``"""
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
        """``Concurrent[a, b]`` matches only ``Concurrent(a(), b())``"""
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
        """``Concurrent[a, ...]`` matches any ``Concurrent(a(), ...)``"""
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
        """``Concurrent[a, b, ...]`` matches any ``Concurrent(a(), b(), ...)``"""
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

    def test_specialised_base(self):
        """``Concurrent[a]`` matches also ``Concurrent(b(): a)``"""
        with pytest.raises(Concurrent[LookupError]):
            raise Concurrent(IndexError())
        with pytest.raises(Concurrent[LookupError]):
            raise Concurrent(KeyError())
        # basetype may catch multiple subtypes
        with pytest.raises(Concurrent[LookupError]):
            raise Concurrent(KeyError(), IndexError())
        # basetype matches do not satisfy missing matchs
        # check that inner test does not catch
        with pytest.raises(Concurrent[LookupError]):
            with pytest.raises(Concurrent[LookupError, TypeError]):
                raise Concurrent(KeyError(), IndexError())

    def test_specialised_identity(self):
        """Various ``Concurrent`` forms are identical, not just equal"""
        assert type(Concurrent()) is Concurrent
        assert Concurrent[...] is Concurrent
        assert type(Concurrent(KeyError())) is Concurrent[KeyError]
        assert type(Concurrent(KeyError(), IndexError()))\
            is Concurrent[KeyError, IndexError]
        assert type(Concurrent(IndexError(), KeyError()))\
            is Concurrent[KeyError, IndexError]

    def test_specialised_subclass(self):
        """``Concurrent[T] :> Concurrent[U]`` if ``T :> U``"""
        assert issubclass(Concurrent[KeyError], Concurrent)
        assert issubclass(Concurrent[IndexError], Concurrent)
        assert issubclass(Concurrent[IndexError, KeyError], Concurrent)
        assert issubclass(Concurrent[KeyError], Concurrent[KeyError])
        assert issubclass(Concurrent[IndexError], Concurrent[LookupError])
        assert issubclass(Concurrent[IndexError, KeyError], Concurrent[KeyError, ...])
        assert not issubclass(
            Concurrent[KeyError, ...], Concurrent[IndexError, KeyError]
        )
        assert not issubclass(FakeConcurrent, Concurrent)
        assert not issubclass(KeyError, Concurrent[KeyError])
        assert not issubclass(KeyError, Concurrent[...])
        assert not issubclass(KeyError, Concurrent[KeyError, ...])
        # duplicate match does not include unmatched case
        assert not issubclass(
            Concurrent[KeyError, LookupError], Concurrent[KeyError, RuntimeError]
        )
