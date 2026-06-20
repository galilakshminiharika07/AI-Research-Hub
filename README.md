# AI Research Hub & Feed Summarizer

An intelligent, self-hosted web application that aggregates, categorizes, and summarizes research papers and blogs from top AI/ML sources (arXiv, MIT News, Berkeley AI Research). 

Using rule-based NLP heuristics, it extracts key paper structural components (Problem, Solution, Method, Results) and auto-generates formatted LinkedIn posts, Executive Summaries, and Key Takeaways in multiple customizable tones.

---

## 🌟 Features

*   **Real-time RSS Fetching:** Aggregates research articles dynamically from 6 pre-configured streams:
    *   arXiv Artificial Intelligence (`cs.AI`)
    *   arXiv Machine Learning (`cs.LG`)
    *   arXiv Computer Vision (`cs.CV`)
    *   arXiv Computation & Language / NLP (`cs.CL`)
    *   MIT News - Artificial Intelligence
    *   Berkeley AI Research (BAIR) Blog
*   **LaTeX & Math Sanitizer:** Automatically cleans LaTeX syntax (`$$`, `\mathbf`, etc.) into clean Unicode equivalents for clean reading.
*   **Smart Classification:** Heuristically analyzes titles and abstracts to categorize articles into subfields like *Computer Vision*, *Natural Language Processing*, *Reinforcement Learning*, *Robotics*, and *AI Ethics*.
*   **NLP Heuristic Extractor:** Automatically parses abstracts to isolate:
    *   **The Challenge:** The underlying problem addressed by the researchers.
    *   **The Innovation:** The proposed solution or framework.
    *   **How It Works:** The methodologies, algorithms, or architectures.
    *   **The Impact:** The empirical results and findings.
*   **Social Content Generator:** Creates ready-to-share summaries customized by format (LinkedIn Post, Executive Brief, Takeaways) and tone (Professional, Academic, Enthusiast).

---

## 🛠️ Tech Stack

*   **Backend:** Python 3, Flask (RESTful APIs)
*   **Parsing & NLP:** `feedparser`, `beautifulsoup4`, Regex
*   **Frontend:** Vanilla HTML5, CSS3 (Modern dark-mode dashboard UI), JavaScript (ES6+)

---

## 🚀 Getting Started

### Prerequisites

*   Python 3.8 or higher installed on your system.

### Installation

1.  **Clone or navigate** to the project workspace directory:
    ```bash
    cd C:\Users\laksh\Desktop\Learnings\agy_cli_projects
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Running the Application

1.  **Start the Flask server:**
    ```bash
    python app.py
    ```

2.  **Access the Dashboard:**
    Open your web browser and navigate to:
    [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 📁 Project Directory Structure

```text
├── app.py                # Main Flask application and backend parser
├── requirements.txt      # List of Python dependencies
├── templates/
│   └── index.html        # Main dashboard frontend interface
├── static/
│   ├── css/
│   │   └── style.css     # Theme stylesheets (dark mode, glassmorphism UI)
│   └── js/
│   │   └── app.js        # Dynamic feed fetching, filters, and summary generation
├── test_feed.py          # Script for testing RSS parser connectivity
└── .gitignore            # Version control exclusions
```

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to fork the repository and submit pull requests.
