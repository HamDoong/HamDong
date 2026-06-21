# Demo Scenario

## Cast

- **Ali**: group creator and later one of the debtors
- **Sara**: pays the restaurant bill and receives settlement money
- **Reza**: joins the group and remains unpaid at the end of the demo

## Group

`شام جمعه`

## Story

Ali creates a Friday dinner group, invites Sara and Reza, and Sara records a shared restaurant expense of `900000 IRR`. HamDong calculates balances, generates a minimized settlement plan, tracks Ali's payment report, and records Sara's confirmation.

## Presentation Flow

1. Ali logs in through the OTP flow.
2. Sara logs in through the OTP flow.
3. Reza logs in through the OTP flow.
4. Ali creates the group `شام جمعه`.
5. Ali creates an invite.
6. Sara accepts the invite.
7. Reza accepts the invite.
8. Sara creates a `900000 IRR` expense.
9. The expense uses an equal split across Ali, Sara, and Reza.

## Expected Balances After Expense

| Person | Balance |
| --- | ---: |
| Ali | -300000 |
| Sara | +600000 |
| Reza | -300000 |

## Settlement Plan

| From | To | Amount |
| --- | --- | ---: |
| Ali | Sara | 300000 |
| Reza | Sara | 300000 |

## Payment Confirmation

1. Ali reports his plan item as paid.
2. Sara confirms the payment.

## Final Balance

| Person | Balance |
| --- | ---: |
| Ali | 0 |
| Sara | +300000 |
| Reza | -300000 |

## Demo Notes

- Use `api-tests/hamdong.http` during the presentation.
- In local debug mode, copy each returned `debug_otp` value into the variables at the top of the file.
- Pause briefly after invite acceptance and expense creation so async consumers can update projections.
