-- Servicing database schema: loans, payment methods, history, schedules,
-- forbearance requests and payment plans. Applied in filename order by
-- mortgage_advisor.db.session.apply_migrations().

CREATE TABLE IF NOT EXISTS loans (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    property_address TEXT NOT NULL,
    original_amount TEXT NOT NULL,
    current_balance TEXT NOT NULL,
    interest_rate TEXT NOT NULL,
    monthly_payment TEXT NOT NULL,
    loan_type TEXT NOT NULL,
    term_months INTEGER NOT NULL,
    remaining_months INTEGER NOT NULL,
    payment_day INTEGER NOT NULL,
    next_due_date TEXT NOT NULL,
    escrow_balance TEXT NOT NULL,
    autopay_enabled INTEGER DEFAULT 0,
    autopay_payment_method_id TEXT,
    origination_date TEXT NOT NULL,
    maturity_date TEXT,
    last_payment_date TEXT,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS payment_methods (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    method_type TEXT NOT NULL,
    last_four TEXT NOT NULL,
    institution_name TEXT NOT NULL,
    nickname TEXT,
    is_default INTEGER DEFAULT 0,
    is_autopay INTEGER DEFAULT 0,
    token TEXT,
    expiration_date TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS payment_history (
    id TEXT PRIMARY KEY,
    loan_id TEXT NOT NULL,
    payment_date TEXT NOT NULL,
    amount TEXT NOT NULL,
    principal_applied TEXT NOT NULL,
    interest_applied TEXT NOT NULL,
    escrow_applied TEXT NOT NULL,
    payment_method_id TEXT NOT NULL,
    payment_method_last_four TEXT NOT NULL,
    status TEXT NOT NULL,
    confirmation_number TEXT NOT NULL,
    posted_date TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (loan_id) REFERENCES loans(id)
);

CREATE TABLE IF NOT EXISTS payment_schedules (
    id TEXT PRIMARY KEY,
    loan_id TEXT NOT NULL,
    due_date TEXT NOT NULL,
    principal_amount TEXT NOT NULL,
    interest_amount TEXT NOT NULL,
    escrow_amount TEXT NOT NULL,
    total_amount TEXT NOT NULL,
    status TEXT DEFAULT 'scheduled',
    paid_date TEXT,
    paid_amount TEXT,
    payment_method_id TEXT,
    confirmation_number TEXT,
    FOREIGN KEY (loan_id) REFERENCES loans(id)
);

CREATE TABLE IF NOT EXISTS forbearance_requests (
    id TEXT PRIMARY KEY,
    loan_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    request_date TEXT NOT NULL,
    reason TEXT NOT NULL,
    requested_months INTEGER NOT NULL,
    status TEXT NOT NULL,
    approved_months INTEGER,
    start_date TEXT,
    end_date TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (loan_id) REFERENCES loans(id)
);

CREATE TABLE IF NOT EXISTS payment_plans (
    id TEXT PRIMARY KEY,
    loan_id TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    total_past_due TEXT NOT NULL,
    additional_monthly_amount TEXT NOT NULL,
    payments_remaining INTEGER NOT NULL,
    status TEXT DEFAULT 'active',
    created_at TEXT NOT NULL,
    FOREIGN KEY (loan_id) REFERENCES loans(id)
);

CREATE INDEX IF NOT EXISTS idx_loans_customer ON loans(customer_id);
CREATE INDEX IF NOT EXISTS idx_payment_methods_customer ON payment_methods(customer_id);
CREATE INDEX IF NOT EXISTS idx_payment_history_loan ON payment_history(loan_id);
CREATE INDEX IF NOT EXISTS idx_payment_schedules_loan ON payment_schedules(loan_id);
