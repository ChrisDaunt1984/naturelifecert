import pytest
from flask import g, session
from naturelifecert.db import get_db
from click.testing import CliRunner

@pytest.fixture
def cli_runner():
    return CliRunner()

def test_register(client, app):
    assert client.get('/auth/register').status_code == 200
    response = client.post(
        '/auth/register', data={'username': 'a', 'password': 'a'}
    )
    assert response.headers["Location"] == "/auth/login"

    with app.app_context():
        assert get_db().execute(
            "SELECT * FROM user WHERE username = 'a'",
        ).fetchone() is not None


@pytest.mark.parametrize("username, password, expected_output", [
    ("test_user", "test_password", "Created user test_user"),
    ("test_user", "test_password", "User test_user is already registered."),
    ("", "test_password", "Username is required."),
    ("test_user", "", "Password is required."),
])
def test_create_user_command(runner, app, username, password, expected_output):
    from naturelifecert.auth import create_user_command
    args = [username, "--password", password]
    with app.app_context():
        result = runner.invoke(create_user_command, args)
        assert expected_output in result.output
        assert result.exit_code == 0 if "Created user" in expected_output else 1

def test_login(client, auth):
    assert client.get('/auth/login').status_code == 200
    response = auth.login()
    assert response.headers["Location"] == "/"

    with client:
        client.get('/')
        assert session['user_id'] == 1
        assert g.user['username'] == 'test'



def test_logout(client, auth):
    auth.login()

    with client:
        auth.logout()
        assert 'user_id' not in session


if __name__ == '__main__':
    import pytest
    import sys
    pytest.main(sys.argv)