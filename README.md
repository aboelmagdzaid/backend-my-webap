# backend-my-webap

Upgraded FastAPI backend for the office portal.

## What exists now

- JWT auth with role-based access
- Client / worker / admin / technical support users
- Tasks API
- Task comments API
- Payments API
- Subscriptions API
- Approvals API
- Audit logs
- Sign-in tracker
- Recovery endpoints for soft-deleted tasks and payments
- Snapshot records
- Summary reports endpoint

## Default seeded users

- `CL-2401` client
- `US-3021` worker / password `123456`
- `AD-9001` admin / password `123456`
- `SP-4401` technical support / password `123456`

## New API areas

- `/api/me`
- `/api/users`
- `/api/tasks`
- `/api/payments`
- `/api/subscriptions`
- `/api/approvals`
- `/api/audit-logs`
- `/api/signins`
- `/api/recovery/*`
- `/api/snapshots`
- `/api/reports/summary`

## Notes

- Password hashing now has a sha256 fallback if bcrypt backend is unavailable locally.
- Existing auth/register/contact endpoints were kept and the new system APIs were added alongside them.
- The DB is still SQLite-based in this repo, but the app structure is now much closer to your full portal blueprint.
