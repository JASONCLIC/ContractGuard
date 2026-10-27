# Field → list of QA questions.
# The QA model will be asked each question against the contract text;
# the answer with the highest confidence score wins.
# Keep questions concise and grounded in typical contract language.

FIELD_QUESTIONS = {
    "contract_name": [
        "What is the title of this contract?",
        "What type of agreement is this?",
    ],
    "party_a": [
        "What is the name of the company or employer?",
        "Who is Party A or the employer in this agreement?",
        "What is the registered name of the hiring company or firm?",
        "What company or organisation is offering this employment?",
    ],
    "party_b": [
        "What is the full name of the employee?",
        "Who is Party B or the employee in this agreement?",
    ],
    "job_title": [
        "What specific position is Party B employed in?",
        "What specific role or title does the intern or employee serve as?",
        "What position or internship title is stated in this contract?",
        "What job title is assigned to the employee?",
        "What is the exact designation or role of the person hired?",
    ],
    "work_location": [
        "What is the specific address of the employee's workplace?",
        "At which office address will Party B work?",
        "What is the work location address?",
    ],
    "salary_amount": [
        "What is the exact salary or compensation amount including the currency?",
        "What is the annual or monthly base salary stated in this contract?",
        "How much is the salary in GBP, USD, EUR, SGD, AUD, CAD, or RMB?",
        "What is the gross salary figure with its currency symbol?",
        "What is the total remuneration amount mentioned in the agreement?",
    ],
    "payment_cycle": [
        "On which specific day of the month is salary paid?",
        "When exactly is the salary payment made each month?",
        "How frequently is salary paid and on what date?",
    ],
    "probation": [
        "How long is the probationary or assessment period in months?",
        "What is the duration of the trial, probation, or assessment period?",
    ],
    "contract_term": [
        "When does the contract or internship start and when does it end?",
        "What are the start date and end date of this agreement or internship?",
    ],
    "termination_conditions": [
        "Under what conditions can the employer terminate the contract?",
        "How many days notice is required to terminate the contract?",
        "What grounds allow termination of this agreement?",
    ],
    "breach_liability": [
        "What penalty or liquidated damages must be paid for breach of contract?",
        "What is the financial penalty if the employee resigns early?",
        "How much must Party B pay if they breach the contract?",
    ],
    "dispute_resolution": [
        "What arbitration body or court resolves disputes under this contract?",
        "Where are disputes submitted for resolution?",
        "What dispute resolution process applies to this agreement?",
    ],
}
