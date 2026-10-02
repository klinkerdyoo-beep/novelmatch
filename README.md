# NovelMatch AI

NovelMatch AI is an AI-powered novel recommendation application that helps users discover novels based on their personal reading preferences.

The application collects information about the user's preferences and a novel they are interested in, then analyzes the information to provide a personalized result and recommendation.

## Features

- User Preference
  - Select preferred and disliked genres
  - Specify favorite books
  - Describe preferred character traits
  - Describe preferred story characteristics
  - Rate previously read novels

- Novel Evaluation
  - Enter a novel title and author
  - Analyze the novel based on the user's preferences

- Personalized Analysis Result
  - Generate a personalized compatibility score
  - Explain why the novel matches the user's preferences
  - Provide an AI-generated analysis and recommendation

## Tech Stack

- Python
- Streamlit
- Google Gemini API
- HTML / CSS
- Pandas

## Project Structure

```text
novelmatch/
├── assets/
├── components/
├── pages/
├── style/
├── main.py
├── requirements.txt
└── README.md
```

## Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/novelmatch.git
cd novelmatch  

### 2. Create a virtual environment

python -m venv .venv

### 3. Activate the virtual environment

Windows:
.venv\Scripts\activate

macOS / Linux:
source .venv/bin/activate

### 4. Install dependencies

pip install -r requirements.txt

### 5. Set up the environment variables
Create a .env file in the project root:

GEMINI_API_KEY=your_api_key_here

### 6. Run the application

streamlit run main.py

The application will open in your browser at:
http://localhost:8501
