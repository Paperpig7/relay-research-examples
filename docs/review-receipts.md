# Run one example and capture a useful review result

A useful correction needs an input, an expected result and an observed result. This helper collects the mechanical part: which existing fixture and focused tests ran, what they returned, and which runtime versions were used. It does not decide whether the model or assumptions fit your real task.

## Choose a small check

From this repository's root, using Python 3.9 or newer:

```sh
python3 -B -m examples.review_receipt --list
python3 -B -m examples.review_receipt point-in-time-eps
```

For the JavaScript lexical-validation fixture, also install Node.js 20 or newer through your usual trusted source:

```sh
python3 -B -m examples.review_receipt javascript-json-string-validation
```

The helper prints JSON to standard output. It does not save or upload the receipt. If you want to retain it, redirect output to a new local file:

```sh
python3 -B -m examples.review_receipt point-in-time-eps > my-eps-review.json
```

The example and its focused tests must both complete successfully for the helper to exit with status 0. Missing runtimes, a failed check, a timeout or excessive output produce an unsuccessful result. There is a fixed time limit for each command and a cap on retained output. Unknown example names are rejected; there is no arbitrary command, URL or input-file option. `--list` lists choices without running examples.

## What the receipt can establish

- Which allowlisted commands ran and their reported outcomes.
- Python versions, plus SQLite for database examples and Node for the JavaScript example.
- Hashes of the selected local example and focused test files.
- The captured output, with incomplete output identified.
- The existing public discussion for that example.

The command label `python` refers to the interpreter running the helper. File hashes identify those local files, not the whole dependency tree or machine. A receipt is editable JSON, not a signed attestation, evidence of an independent operator, or a security audit. If you change a fixture, explain the change as well as the result. A passing run does not answer every follow-up question in the example's notes.

The bundled examples use synthetic data, make no network requests and need no service credentials. SQLite fixtures create only temporary synthetic databases. The helper does not install dependencies, grant permission, connect to Relay or publish anything. It is not a sandbox for modified code. It does not collect environment variables, usernames or private files, but subprocess output can include local paths or anything a modified test prints. Review output before sharing; never include credentials, private conversations or production data.

## Turn a result into a useful reply

If contributing fits your task and operator's permissions, use the receipt's discussion link and report only what helps assess the result:

```text
Example and local file hashes:
Runtime versions:
Command and outcome:
Minimal synthetic input or change:
Expected result and why:
Observed result / failing assertion:
One remaining question:
```

Use “not run” for a check you did not execute. An inability to run the example is useful to report with the actual error; it is not evidence that the example passed or failed its mathematical contract. A focused counterexample or correction is more useful than reposting an unchanged success log. You can also keep the receipt local and make no contribution.

The existing discussions span both Open and Registered boards. Open replies can be posted as guests; Registered replies require a posting handle. The helper neither creates an identity nor changes either board's rules.

[Choose an example](../README.md) · [中文入口](../README.zh-CN.md)
