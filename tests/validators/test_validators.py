import pytest
from .. import conftest as fix
import connaisseur.validators.validator as val
import connaisseur.exceptions as exc


@pytest.mark.parametrize(
    "validator_dict, class_, exception",
    [
        (
            {
                "type": "notaryv1",
                "name": "notary1",
                "host": "me",
                "pub_root_keys": [{"name": "i'm", "key": "not_empty"}],
            },
            val.NotaryV1Validator,
            fix.no_exc(),
        ),
        (
            {"type": "notaryv2", "name": "notary2", "host": "me"},
            val.NotaryV2Validator,
            pytest.raises(NotImplementedError),
        ),
        (
            {"type": "cosign", "name": "cosigngn"},
            val.CosignValidator,
            pytest.raises(NotImplementedError),
        ),
        (
            {"type": "static", "name": "allow", "approve": True},
            val.StaticValidator,
            fix.no_exc(),
        ),
        ({"type": "ayy"}, None, pytest.raises(exc.NoSuchClassError)),
    ],
)
def test_new(validator_dict, class_, exception):
    with exception:
        assert isinstance(val.Validator(**validator_dict), class_)
