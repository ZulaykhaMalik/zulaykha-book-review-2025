
// Section Switching Logic

function showSection(id) {
  ["homeSection", "searchSection", "addBookSection", "allBooksSection", "reviewsSection"].forEach(s =>
    document.getElementById(s).classList.add("hidden")
  );
  document.getElementById(id).classList.remove("hidden");

  if (id === "allBooksSection") showAllBooks();
  if (id === "reviewsSection") loadReviews();

  if (id !== "searchSection") {
    const searchBox = document.getElementById("searchBox");
    const searchResults = document.getElementById("searchResults");
    if (searchBox && searchResults) {
      searchBox.value = "";
      searchResults.innerHTML = "";
    }
  }

  if (id !== "addBookSection") {
    const bookList = document.getElementById("bookList");
    if (bookList) bookList.innerHTML = "";
  }
}


// Sidebar Navigation

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("menuHome").onclick = () => showSection("homeSection");
  document.getElementById("menuSearch").onclick = () => showSection("searchSection");
  document.getElementById("menuAdd").onclick = () => showSection("addBookSection");
  document.getElementById("menuAll").onclick = () => showSection("allBooksSection");
  document.getElementById("menuReviews").onclick = () => showSection("reviewsSection");
  showSection("homeSection");
});


// SQLite Book Functions

function renderBookCard(book) {
  return `
    <div class="book-card">
      <img src="${book.image_url || '/static/default-book.jpg'}" alt="${book.title}">
      <h3>${book.title}</h3>
      <p><strong>Author:</strong> ${book.author}</p>
      <p><strong>Year:</strong> ${book.publication_year || ""}</p>
    </div>
  `;
}

function showAllBooks() {
  fetch("/api/books")
    .then(r => r.json())
    .then(data => {
      const container = document.getElementById("allbooks");
      container.innerHTML = data.length
        ? data.map(renderBookCard).join("")
        : "<p>No books available.</p>";
    });
}

function addBook() {
  const book = {
    title: document.getElementById("bookTitle").value.trim(),
    author: document.getElementById("author").value.trim(),
    publication_year: document.getElementById("publicationYear").value.trim(),
    image_url: document.getElementById("imageUrl").value.trim()
  };

  if (!book.title || !book.author) {
    alert("Please enter both title and author.");
    return;
  }

  fetch("/api/add_book", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(book)
  })
    .then(r => r.json())
    .then(() => {
      document.getElementById("bookList").innerHTML = renderBookCard(book);
      alert("✅ Book added successfully!");
      document.getElementById("bookTitle").value = "";
      document.getElementById("author").value = "";
      document.getElementById("publicationYear").value = "";
      document.getElementById("imageUrl").value = "";
    })
    .catch(err => console.error("Error adding book:", err));
}

function searchBooks() {
  const q = document.getElementById("searchBox").value.trim();
  const resultsDiv = document.getElementById("searchResults");

  if (!q) {
    resultsDiv.innerHTML = "<p>Please enter something to search.</p>";
    return;
  }

  fetch(`/api/search?q=${encodeURIComponent(q)}`)
    .then(r => r.json())
    .then(data => {
      resultsDiv.innerHTML = `
        <div class="form-box">
          <button onclick="clearSearch()">Clear Search</button>
        </div>
      `;

      const booksHTML = data.length
        ? data.map(renderBookCard).join("")
        : "<p>No results found.</p>";

      // Append books below the buttons
      resultsDiv.innerHTML = booksHTML + resultsDiv.innerHTML;
    });
}

function clearSearch() {
  document.getElementById("searchBox").value = "";
  document.getElementById("searchResults").innerHTML = "";
}


// MongoDB Review Functions ------------

function loadReviews() {
  fetch("/api/reviews")
    .then(r => r.json())
    .then(data => {
      const container = document.getElementById("reviewsList");
      if (!data.length) {
        container.innerHTML = "<p>No reviews found.</p>";
        return;
      }

      container.innerHTML = data.map(r => `
        <div class="book-card">
          <h3>Book ID: ${r.book_id}</h3>
          <p><strong>${r.reviewer || "Anonymous"}</strong> (${r.rating || "N/A"}/5)</p>
          <p>${r.review_text}</p>
          <p><small>${r.created_at ? new Date(r.created_at).toLocaleString() : ""}</small></p>
        </div>
      `).join("");
    })
    .catch(err => {
      console.error("Error loading reviews:", err);
      document.getElementById("reviewsList").innerHTML = "<p>Failed to load reviews.</p>";
    });
}

function addReview() {
  const review = {
    book_id: document.getElementById("reviewBookId").value.trim(),
    reviewer: document.getElementById("reviewerName").value.trim(),
    review_text: document.getElementById("reviewText").value.trim(),
    rating: parseInt(document.getElementById("reviewRating").value)
  };

  if (!review.book_id || !review.review_text) {
  alert("Book ID and review text are required.");
  // Allow the request to continue so the backend can log the error
}

  fetch("/api/add_review", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(review)
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        alert(`⚠️ ${data.error}`);
        return;
      }

      // ✅ Show only the newly added review (hide old ones)
      const container = document.getElementById("reviewsList");
      container.innerHTML = `
        <div class="book-card">
          <h3>Book ID: ${review.book_id}</h3>
          <p><strong>${review.reviewer || "Anonymous"}</strong> (${review.rating || "N/A"}/5)</p>
          <p>${review.review_text}</p>
          <p><small>${new Date().toLocaleString()}</small></p>
        </div>
      `;

      alert("✅ Review added successfully!");

      // Clear form fields
      document.getElementById("reviewBookId").value = "";
      document.getElementById("reviewerName").value = "";
      document.getElementById("reviewText").value = "";
      document.getElementById("reviewRating").value = "";
    })
    .catch(err => {
      console.error("Error adding review:", err);
      alert("❌ Failed to add review. Check console for details.");
    });
}