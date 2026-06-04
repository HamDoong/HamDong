# Demo Scenario

Ali, Sara, and Reza are in a group named `شام جمعه`.

## Story

Ali wants to split a Friday dinner with Sara and Reza. Sara pays the restaurant bill, the system calculates balances, generates an optimized settlement plan, and tracks a confirmed payment from Ali.

## Flow

1. Ali logs in.
2. Sara logs in.
3. Reza logs in.
4. Ali creates the group `شام جمعه`.
5. Ali creates an invite link.
6. Sara joins the group.
7. Reza joins the group.
8. Sara pays and records a `900000 IRR` expense.
9. The expense is split equally between Ali, Sara, and Reza.

## Expected Balances After Expense

| Person | Balance |
| --- | ---: |
| Ali | -300000 |
| Sara | +600000 |
| Reza | -300000 |

## Smart Settlement Plan

| From | To | Amount |
| --- | --- | ---: |
| Ali | Sara | 300000 |
| Reza | Sara | 300000 |

## Payment Confirmation

1. Ali reports his payment as paid.
2. Sara confirms the payment.

## Final Balance

| Person | Balance |
| --- | ---: |
| Ali | 0 |
| Sara | +300000 |
| Reza | -300000 |

Remaining unpaid plan items can still trigger reminders.

## REST Client File

Run the scenario from `api-tests/hamdong.http`. Copy debug OTP values manually when local `DEBUG=true`.
