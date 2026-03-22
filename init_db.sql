-- SQL initialization script for Accounting Office API
-- Run this once to create schema and seed core data

PRAGMA foreign_keys = ON;

-- Roles are inlined by enum field values.

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    user_number TEXT NOT NULL UNIQUE,
    email TEXT UNIQUE,
    password_hash TEXT,
    role TEXT NOT NULL CHECK(role IN ('client','worker','admin','technical_support')),
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);

CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    subject TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    resource TEXT NOT NULL,
    resource_id INTEGER,
    details TEXT,
    ip_address TEXT,
    user_agent TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Seed an initial admin user (password must be hashed in application logic)
INSERT OR IGNORE INTO users (name, user_number, email, password_hash, role, is_active)
VALUES
    ('Admin User', 'admin001', 'admin@company.local', '', 'admin', 1);

-- Optional default contact and audit samples
INSERT INTO contacts (name, email, phone, subject, message, status)
VALUES
    ('Guest', 'guest@domain.local', '123-456-7890', 'Hello', 'This is a sample message', 'pending');

INSERT INTO audit_logs (user_id, action, resource, resource_id, details, ip_address, user_agent)
VALUES
    (1, 'seed', 'system', NULL, 'Seeded initial data', '127.0.0.1', 'init-script');
