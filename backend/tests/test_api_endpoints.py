import pytest


@pytest.mark.api
class TestQueryEndpoint:
    """Tests for POST /api/query"""

    def test_query_with_session_id(self, client, mock_rag_system, sample_query_request):
        response = client.post("/api/query", json=sample_query_request)

        assert response.status_code == 200
        assert response.json() == {
            "answer": "This is a test response about course content.",
            "sources": ["Building Towards Computer Use with Anthropic - Lesson 1"],
            "source_links": ["https://example.com/lesson1"],
            "session_id": "test-session-123",
        }
        mock_rag_system.query.assert_called_once_with(
            "What is computer use in AI?", "test-session-123"
        )
        mock_rag_system.session_manager.create_session.assert_not_called()

    def test_query_without_session_id_creates_session(self, client, mock_rag_system):
        response = client.post("/api/query", json={"query": "What is computer use?"})

        assert response.status_code == 200
        assert response.json()["session_id"] == "new-session-456"
        mock_rag_system.session_manager.create_session.assert_called_once()
        mock_rag_system.query.assert_called_once_with(
            "What is computer use?", "new-session-456"
        )

    def test_query_with_empty_session_id_creates_session(self, client, mock_rag_system):
        response = client.post("/api/query", json={"query": "hi", "session_id": ""})

        assert response.status_code == 200
        assert response.json()["session_id"] == "new-session-456"

    def test_query_allows_missing_source_links(self, client, mock_rag_system):
        mock_rag_system.query.return_value = ("answer", ["Course A"], [None])

        response = client.post("/api/query", json={"query": "q"})

        assert response.status_code == 200
        assert response.json()["source_links"] == [None]

    def test_query_missing_query_field(self, client, mock_rag_system):
        response = client.post("/api/query", json={})

        assert response.status_code == 422
        mock_rag_system.query.assert_not_called()

    def test_query_wrong_type(self, client):
        response = client.post("/api/query", json={"query": 123})
        assert response.status_code == 422

    def test_query_ignores_extra_fields(self, client):
        response = client.post("/api/query", json={"query": "q", "extra": "x"})
        assert response.status_code == 200

    def test_query_rag_error_returns_500(self, client, mock_rag_system):
        mock_rag_system.query.side_effect = RuntimeError("Anthropic API down")

        response = client.post("/api/query", json={"query": "q"})

        assert response.status_code == 500
        assert response.json() == {"detail": "Anthropic API down"}


@pytest.mark.api
class TestCoursesEndpoint:
    """Tests for GET /api/courses"""

    def test_courses_returns_stats(self, client):
        response = client.get("/api/courses")

        assert response.status_code == 200
        assert response.json() == {
            "total_courses": 2,
            "course_titles": [
                "Building Towards Computer Use with Anthropic",
                "Advanced AI Techniques",
            ],
        }

    def test_courses_empty_catalog(self, client, mock_rag_system):
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }

        response = client.get("/api/courses")

        assert response.status_code == 200
        assert response.json() == {"total_courses": 0, "course_titles": []}

    def test_courses_error_returns_500(self, client, mock_rag_system):
        mock_rag_system.get_course_analytics.side_effect = RuntimeError("db gone")

        response = client.get("/api/courses")

        assert response.status_code == 500
        assert response.json() == {"detail": "db gone"}


@pytest.mark.api
class TestClearSessionEndpoint:
    """Tests for POST /api/clear-session"""

    def test_clear_session(self, client, mock_rag_system, sample_clear_session_request):
        response = client.post("/api/clear-session", json=sample_clear_session_request)

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "message": "Session cleared successfully",
        }
        mock_rag_system.session_manager.clear_session.assert_called_once_with(
            "test-session-123"
        )

    def test_clear_session_missing_field(self, client):
        response = client.post("/api/clear-session", json={})
        assert response.status_code == 422

    def test_clear_session_wrong_type(self, client):
        response = client.post("/api/clear-session", json={"session_id": 123})
        assert response.status_code == 422

    def test_clear_session_error_returns_500(self, client, mock_rag_system):
        mock_rag_system.session_manager.clear_session.side_effect = KeyError("x")

        response = client.post("/api/clear-session", json={"session_id": "s"})

        assert response.status_code == 500


@pytest.mark.api
class TestStaticAndCors:
    """Tests for the frontend mount and CORS middleware"""

    def test_root_serves_frontend_without_cache(self, client):
        response = client.get("/")

        assert response.status_code == 200
        assert "Course Materials" in response.text
        assert (
            response.headers["cache-control"] == "no-cache, no-store, must-revalidate"
        )

    def test_unknown_path_returns_404(self, client):
        assert client.get("/does-not-exist.js").status_code == 404

    def test_cors_preflight(self, client):
        response = client.options(
            "/api/query",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "POST",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://example.com"
        assert "POST" in response.headers["access-control-allow-methods"]

    def test_cors_header_on_simple_request(self, client):
        response = client.get("/api/courses", headers={"Origin": "http://example.com"})
        assert response.headers["access-control-allow-origin"] == "*"


@pytest.mark.api
@pytest.mark.integration
def test_session_workflow(client, mock_rag_system):
    """New session is created, reused on follow-up, then cleared"""
    first = client.post("/api/query", json={"query": "What courses exist?"})
    session_id = first.json()["session_id"]

    follow_up = client.post(
        "/api/query", json={"query": "Elaborate", "session_id": session_id}
    )
    cleared = client.post("/api/clear-session", json={"session_id": session_id})

    assert follow_up.json()["session_id"] == session_id
    assert cleared.status_code == 200
    assert mock_rag_system.session_manager.create_session.call_count == 1
    mock_rag_system.session_manager.clear_session.assert_called_once_with(session_id)
