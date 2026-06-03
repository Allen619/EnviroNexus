import pytest

from app.core.exceptions import MissingUserIdError
from app.dependencies import get_user_id


def test_get_user_id_raises_when_blank():
    with pytest.raises(MissingUserIdError):
        get_user_id(x_user_id="   ")


def test_get_user_id_strips():
    assert get_user_id(x_user_id="  user-1  ") == "user-1"
