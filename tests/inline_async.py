"""Drive immediate fake-HA coroutines without Windows event-loop networking."""
import functools
import inspect


def finish(coroutine):
    try:
        coroutine.send(None)
    except StopIteration as result:
        return result.value
    finally:
        coroutine.close()
    raise AssertionError('Simulated HA operation unexpectedly waited on external I/O')


def immediate_tests(cls):
    for name, method in list(vars(cls).items()):
        if name.startswith('test_') and inspect.iscoroutinefunction(method):
            def wrap(method):
                @functools.wraps(method)
                def run(self):
                    return finish(method(self))
                return run
            setattr(cls,name,wrap(method))
    return cls
