# LedgerFlow Collections PRD

## Original Problem Statement
Build a production-ready money collection management app for field agents and administrators, with mobile employee workflows, admin analytics, digital receipts, WhatsApp sharing, expenses, and seeded realistic data.

## Architecture Decisions
- React single-page interface with role-based portal switcher (Employee opens by default).
- FastAPI API with MongoDB collections for vendors, employees, collections, and expenses.
- Live dashboard calculations derived from persisted records; receipt sharing uses WhatsApp deep links and browser print.

## User Personas
- Field collection agent: logs collections and field expenses quickly from a phone.
- Collection administrator: monitors totals, records, team activity, vendors, and expenses.

## Core Requirements
- Employee mobile KPIs, collection form, digital receipt, WhatsApp share, printing, and expense history.
- Admin KPIs, collection trend, filters/search/export, vendor/employee management, and expense audit.
- Seed 5 vendors, 3 employees, and historical example records.

## What Has Been Implemented — 2026-07-28
- Full Employee and Admin portals with responsive role toggle.
- MongoDB-backed collection, expense, vendor, employee, and dashboard APIs, including startup seed data.
- Real-time receipt preview, WhatsApp sharing, print action, CSV export, dashboard refreshes, and management forms.
- End-to-end validation completed for all major flows.

## Feature Added — 2026-07-28
- Secure phone number and password sign-in for administrators and field employees.
- Administrator-created employee accounts with temporary passwords and a required first-login password change.
- Server-side role protection isolates each employee to their own profile, collections, expenses, and dashboard.
- Administrators can open an employee profile and daily activity report listing collection amounts and vendors.

## Prioritized Backlog
### P0
- None.
### P1
- Add date-range controls and PDF export for administrators.
- Add confirmation dialog and edit workflows for vendor and employee records.
### P2
- Add account authentication, audit events, and notification preferences.

## Next Tasks
- Gather feedback from field agents on the collection form and receipt layout.
- Expand reporting filters and add downloadable administrative summaries.
