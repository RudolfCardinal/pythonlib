# https://stackoverflow.com/questions/28198585/how-to-take-action-on-a-test-failure-with-pytest
def pytest_exception_interact(node, call, report):
    if report.failed:
        filename = "/tmp/debugging"
        # call.excinfo contains an ExceptionInfo instance
        try:
            with open(filename, "r") as f:
                print(f"\n{f.read()}\n")
        except FileNotFoundError:
            print(f"\n{filename} does not exist\n")
