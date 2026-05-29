# Python Lambda module-name collision in PR review test runs

## Trigger
Use this when reviewing Python repositories that contain multiple Lambda/function directories where each directory exposes the handler as the same top-level module name, commonly `lambda_function.py`, and the tests mutate `sys.path` or import `lambda_function` directly.

## Durable pitfall
A broad pytest invocation that runs multiple Lambda test directories in one Python process can import the first `lambda_function` module and leave it cached in `sys.modules`. Later tests for a different Lambda directory may then patch or assert against the wrong module, producing misleading errors such as:

```text
AttributeError: module 'lambda_function' from '.../Account-Creation-Approve/lambda_function.py' has no attribute 'get_bootstrap_dependencies'
```

This is not automatically a PR regression. It can be an invocation artifact caused by identical module names and shared interpreter state.

## Review pattern
1. Run the broad test command if it is the repo's normal CI command, but inspect failures for wrong-path imports or missing attributes from a sibling Lambda module.
2. If the failure shows module-cache collision, re-run the impacted test directories in separate pytest invocations / separate Python processes.
3. Treat the focused per-directory results as stronger local evidence for the changed code when remote CI is also green.
4. In the review body, disclose the combined-run artifact and the successful focused runs, e.g.:

```text
A combined local pytest invocation failed because both Lambda folders import as `lambda_function` and the first import stayed cached in `sys.modules`; the focused suites passed when run separately.
```

5. Do not request changes solely for the combined-run failure unless the repo's documented CI command fails the same way on the current head, or the PR changed the test/import structure and introduced the collision.

## Useful commands
Adapt dependencies to the repo; the key is one pytest process per Lambda test directory:

```bash
uv run --isolated --python 3.11 \
  --with pytest --with pytest-testdox --with boto3 --with requests \
  --with firebase-admin --with google-cloud-firestore --with botocore \
  pytest Account-Creation-Approve/test_lambda_function_approve.py -q

uv run --isolated --python 3.11 \
  --with pytest --with pytest-testdox --with boto3 --with requests \
  --with firebase-admin --with google-cloud-firestore --with botocore \
  pytest Account-Creation-Preparation/test_lambda_function_preparation.py -q
```
