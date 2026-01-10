# Storms - XPath Generator

A web application that uses Claude AI to generate XPath selectors for web automation testing.

## Setup

### Prerequisites
- Node.js and npm
- Python 3.8+
- Anthropic API key

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file from example:
```bash
cp .env.example .env
```

4. Add your Anthropic API key to `.env`:
```
ANTHROPIC_API_KEY=your_actual_key_here
```

### Frontend Setup

1. Navigate to root directory and install dependencies:
```bash
npm install
```

## Running the Application

### Start Backend (Terminal 1)

Windows:
```bash
cd backend
python -m uvicorn app:app --reload
```

macOS/Linux:
```bash
cd backend
uvicorn app:app --reload
```

Backend will run on http://localhost:8000

### Start Frontend (Terminal 2)

```bash
npm run dev
```

Frontend will run on http://localhost:5173

## Usage

1. Open http://localhost:5173 in your browser
2. Enter a URL of the webpage you want to analyze
3. Describe the element you want to select (e.g., "the login button", "the search input field")
4. Click "Generate XPath" to get an AI-generated XPath selector
5. Copy the generated XPath for use in your automation tests