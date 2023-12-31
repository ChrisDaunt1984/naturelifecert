from naturelifecert import create_app


def test_config():
    assert not create_app().testing
    assert create_app({'TESTING': True}).testing


def test_hello(client):
    response = client.get('/hello')
    assert response.data == b'Hello, World!'

if __name__ == '__main__':
    import pytest
    import sys
    pytest.main(sys.argv)