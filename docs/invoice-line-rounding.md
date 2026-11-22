# Can two wrong invoice lines give the right subtotal?

Yes. On the two lines below, Python’s binary float calculation gives **1.03 and 1.01**. The exact decimal calculation with half-even rounding gives **1.04 and 1.00**. Both add up to **2.04**. A test that checks only the invoice subtotal misses both errors. [中文复核](#中文复核)

## Two acceptance tests

Give each line a quantity of three. Pass the unit price to the application as decimal text. Assert the line amount after multiplying, before any discount or tax. The expected amounts are available as integer cents in a [two-row JSON fixture](../examples/invoice_line_cases.json).

| Unit price | Exact line amount | Half-up | Half-even | What the line tests |
| --- | ---: | ---: | ---: | --- |
| `"0.345"` | 1.035 | 1.04 | 1.04 | Both policies select 104 cents. Rounding the unit price first gives 1.05 under half-up or 1.02 under half-even. |
| `"0.335"` | 1.005 | 1.01 | 1.00 | The retained cent is even at 100. This line distinguishes the two tie rules. |

Choose the column that matches the application’s stated policy. Convert each rounded line to integer cents before comparing it with the fixture. Under half-up, the two rounded lines sum to 2.05. Adding their exact amounts first and rounding 2.040 once gives 2.04. A match establishes what the application returned for these inputs. Several implementations can produce the same result. These examples cover positive, whole-quantity lines in a currency with two decimal places. Refunds, discount allocation and tax calculation need their own rules.

## Reproduce the comparison

From the repository root, run the example and its tests with Python 3.9 or newer. The JSON receipt includes the runtime version, the hashes of the fixture, code and tests, and the discussion link.

```sh
python3 -B -m examples.review_receipt invoice-line-rounding
```

For the table alone, run `python3 -B -m examples.invoice_line_rounding`. The example reads each unit price as text, constructs a `Decimal`, multiplies by quantity and calls `quantize` with the chosen rule. On the first line, binary float multiplication lands just below the exact decimal midpoint. [Python decimal rounding modes](https://docs.python.org/3/library/decimal.html#rounding-modes) · [Python’s floating-point tutorial](https://docs.python.org/3/tutorial/floatingpoint.html)

To inspect the two JavaScript operations from the discussion, run this optional Node.js check in a POSIX shell from the same directory. Both operations gave 1.03 on the first line and 1.01 on the second in Node 20.17.0.

```sh
node --input-type=commonjs - <<'JS'
const cases = require('./examples/invoice_line_cases.json');
for (const row of cases) {
  const amount = row.quantity * Number(row.unit_price);
  console.log(row.unit_price, Math.round(amount * 100) / 100, amount.toFixed(2));
}
JS
```

## 中文复核

数量都是 3。单价为 `"0.345"` 时，精确行金额为 1.035。按“四舍五入”或“恰好一半时取偶数”保留两位小数，结果都是 1.04。单价换成 `"0.335"` 时，精确行金额为 1.005，两种规则分别得到 1.01 和 1.00。

在自己的程序中读入上面的 JSON，保留单价字符串，按约定的规则逐行计算。把逐行舍入后的金额换算成整数分，再分别与 `half_up_cents` 或 `half_even_cents` 比较。尤其要检查第二种规则：示例中的浮点运算和舍入得到 1.03 和 1.01，小计却恰好也是 2.04。

## Where the cases came from

A Relay question supplied the 0.335 line and asked for a case that would expose float rounding under either decimal policy. Relay’s host contributed the 0.345 line. A Guest subsequently reported reproducing that result on Node 24.22.1 and Python 3.13.5. The report predates this runnable fixture. [Original question](https://relay-commons.ericx.workers.dev/t/07e1ec4a-0302-4f28-8854-a63e36abaac3) · [Host’s worked case](https://relay-commons.ericx.workers.dev/t/07e1ec4a-0302-4f28-8854-a63e36abaac3?reply=dbd20c5c-82c0-453a-b306-2a54199b9983#post-dbd20c5c-82c0-453a-b306-2a54199b9983) · [Reported reproduction](https://relay-commons.ericx.workers.dev/t/07e1ec4a-0302-4f28-8854-a63e36abaac3?reply=edb67ab5-26c0-49fa-9dba-aa7aaa2e5095#post-edb67ab5-26c0-49fa-9dba-aa7aaa2e5095)
