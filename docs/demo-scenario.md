# Demo Scenario

Scenario: Ali, Sara, and Reza in group "شام جمعه".

Steps:
1) Ali requests OTP and logs in using `POST /api/v1/auth/otp/request/` and `POST /api/v1/auth/otp/verify/`.
2) Ali creates a group `POST /api/v1/groups/` — group title: "شام جمعه".
3) Ali creates invites for Sara and Reza; they accept via invite links and `POST /api/v1/groups/invites/{token}/accept/`.
4) Ali uploads a receipt via `POST /api/v1/media/receipts/`.
5) Sara creates an expense for 900000 IRR; the expense is split equally between Ali, Sara, Reza via `POST /api/v1/groups/{groupId}/expenses/`.
6) System calculates balances — shows Ali and Reza as debtors, Sara as creditor.
7) Generate settlement plan via `POST /api/v1/groups/{groupId}/settlement-plan/generate/`.
8) Plan suggests Ali -> Sara and Reza -> Sara. Activate via `POST /api/v1/settlement-plans/{plan_id}/activate/`.
9) Ali reports payment `POST /api/v1/settlement-plan-items/{item_id}/report-paid/`.
10) Sara confirms payment `POST /api/v1/settlements/{settlement_id}/confirm/`.
11) Balances update and reminders can be issued for outstanding items.

Use `api-tests/hamdong.http` to run the full scenario.
