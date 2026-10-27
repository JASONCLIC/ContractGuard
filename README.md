# ContractGuard

Authors: Yuxuan Zhang, Xinya Shi, Yuan Jing  
Authors: Shaohui Jing, Tianyi Ma, Zihan Miao

ContractGuard is a full-stack contract analysis application with:
- a Flask backend (`backend/`)
- a React + Vite frontend (`frontend/`)

## Website screenshots

Screenshots from the original project demonstration recordings.

### Homepage

![ContractGuard homepage with contract analysis and clause library entry points](docs/screenshots/dashboard.png)

### Contract risk analysis

![Analysis results showing risk levels, clause explanations and the original contract text](docs/screenshots/risk-analysis.png)

### Clause template library

![Clause template library with categories, sample wording and drafting guidance](docs/screenshots/clause-library.png)

### Risk clause quiz

![Interactive quiz for identifying risky contract clauses](docs/screenshots/risk-quiz.png)

## Prerequisites

- Python 3.9+
- Node.js 18+
- npm 9+

## Backend setup

### 1) Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

Choose one of the following based on your environment:

- Runtime only (recommended for deployment VMs):
  ```bash
  pip install -r backend/requirements-runtime.txt
  ```
- Runtime + test dependencies:
  ```bash
  pip install -r backend/requirements-runtime.txt -r backend/requirements-test.txt
  ```
- Full backend stack (runtime + ML training/evaluation):
  ```bash
  pip install -r backend/requirements.txt
  ```

### 3) Configure environment variables

Create and edit `backend/.env` (example fields):

```env
SECRET_KEY=your-secret
DATABASE_URL=mysql+pymysql://user:password@127.0.0.1:3306/contractguard
FRONTEND_ORIGIN=http://localhost:5173
```

### 4) Run the backend

```bash
python app.py
```

The backend will be available at `http://127.0.0.1:5000`.

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`.

## Testing

### Backend tests

```bash
source .venv/bin/activate
cd backend
pytest
```

### Frontend unit tests (Vitest)

```bash
cd frontend
npm run test:run
```

### Frontend E2E tests (Playwright)

```bash
cd frontend
npm run e2e
```
