def test_home_page_loads(client, temp_upload_dir):
    """The home page should load successfully."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Meeting Notes" in response.text


def test_home_page_has_upload_zone(client, temp_upload_dir):
    """The home page should have an upload zone."""
    response = client.get("/")
    assert response.status_code == 200
    assert "upload-zone" in response.text
    assert "Drop your recording" in response.text


def test_static_css_loads(client, temp_upload_dir):
    """Static CSS file should be accessible."""
    response = client.get("/static/css/style.css")
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]


def test_static_js_loads(client, temp_upload_dir):
    """Static JS file should be accessible."""
    response = client.get("/static/js/app.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
