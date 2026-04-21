from app import create_app


def test_app_boots():
    app = create_app()
    assert app is not None
    assert app.config is not None


def test_public_pages_respond():
    app = create_app()
    client = app.test_client()

    for route in ["/", "/login", "/register", "/book", "/admin", "/admin/verify"]:
        response = client.get(route)
        assert response.status_code == 200
