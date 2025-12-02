import pytest
from app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_home_page(client):
    """Test that the home page loads successfully"""
    response = client.get("/")
    assert response.status_code == 200

def test_add_book(client):
    """Test adding a book"""
    book = {
        "title": "Test Book",
        "author": "Test Author",
        "publication_year": 2024,
        "image_url": "http://example.com/test.jpg"
    }
    response = client.post("/api/add_book", json=book)
    assert response.status_code == 200
    assert b"Book added successfully" in response.data

def test_search_existing_book(client):
    """Test searching for a book that exists"""
    response = client.get("/api/search?q=Test Book")
    assert response.status_code == 200
    assert b"Test Book" in response.data

def test_search_nonexistent_book(client):
    """Test searching for a book that does not exist"""
    response = client.get("/api/search?q=abcdef")
    assert response.status_code == 200
    # Should return empty list []
    assert response.json == []




#  MongoDB (Reviews) API Tests ---------

def test_add_review(client):
    """Test adding a review to MongoDB"""
    review = {
        "book_id": "1",
        "reviewer": "Test User",
        "review_text": "This is a test review",
        "rating": 5
    }
    response = client.post("/api/add_review", json=review)
    assert response.status_code == 200
    assert b"Review added successfully" in response.data

def test_get_reviews(client):
    """Test retrieving reviews from MongoDB"""
    response = client.get("/api/reviews")
    assert response.status_code == 200
    assert isinstance(response.json, list)