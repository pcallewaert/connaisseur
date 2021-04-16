import pytest
import connaisseur.validators.interface as vi


def test_init():
    assert vi.ValidatorInterface("")


def test_validate():
    with pytest.raises(NotImplementedError):
        assert vi.ValidatorInterface("").validate(None)


def test_healthy():
    assert vi.ValidatorInterface("").healthy is True


def test_str():
    with pytest.raises(AttributeError):
        assert str(vi.ValidatorInterface(""))
