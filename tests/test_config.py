import pytest
from . import conftest as fix
import connaisseur.config as co
import connaisseur.exceptions as exc
import connaisseur.validators as vals


@pytest.fixture(autouse=True)
def mock_config_path():
    co.Config.path = "tests/data/config/sample_config.yaml"
    co.Config.secrets_path = "tests/data/config/sample_secrets.yaml"
    co.Config.schema_path = "connaisseur/res/config_schema.json"


nv1 = vals.notrayv1.notaryv1_validator.NotaryV1Validator
static = vals.static.static_validator.StaticValidator
static_config = [
    {
        "name": "default",
        "type": nv1,
    },
    {
        "name": "harbor",
        "type": nv1,
    },
    {"name": "allow", "type": static},
    {"name": "deny", "type": static},
]


@pytest.mark.parametrize(
    "config_path, exception",
    [
        ("sample_config", fix.no_exc()),
        ("err", pytest.raises(FileNotFoundError)),
        ("err1", pytest.raises(exc.NotFoundException)),
        (
            "err2",
            pytest.raises(
                exc.InvalidConfigurationFormatError, match=r".*invalid format.*"
            ),
        ),
        (
            "err3",
            pytest.raises(exc.InvalidConfigurationFormatError, match=r".*notary.*"),
        ),
        ("err4", pytest.raises(exc.InvalidConfigurationFormatError, match=r".*keys.*")),
    ],
)
def test_config(config_path, exception):
    co.Config.path = f"tests/data/config/{config_path}.yaml"
    with exception:
        config = co.Config()
        assert len(config.validators) == 4
        for index, validator in enumerate(config.validators):
            assert validator.name == static_config[index]["name"]
            assert isinstance(validator, static_config[index]["type"])


@pytest.mark.parametrize(
    "key_name, name, exception",
    [
        ("default", "default", fix.no_exc()),
        ("harbor", "harbor", fix.no_exc()),
        (None, "default", fix.no_exc()),
        ("harborr", "", pytest.raises(exc.NotFoundException)),
    ],
)
def test_get_notary(key_name, name, exception):
    config = co.Config()
    with exception:
        assert config.get_validator(key_name).name == name
