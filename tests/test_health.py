def test_health_check_returns_healthy(client):
    """The health endpoint should return a healthy status."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data


def test_health_check_is_fast(client):
    """
    Health checks need to be quick since they're called frequently.
    This is more of a sanity check than a real performance test.
    """
    import time

    start = time.time()
    response = client.get("/health")
    elapsed = time.time() - start

    assert response.status_code == 200
    # should complete in under 100ms
    assert elapsed < 0.1
