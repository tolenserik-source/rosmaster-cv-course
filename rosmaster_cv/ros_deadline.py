"""Bound ROS1 startup as well as processing, even if master registration retries."""
import multiprocessing
import os
import signal


def _worker(function, arguments, connection):
    try:
        result = function(*arguments)
        connection.send(("ok", result))
    except Exception as exc:
        connection.send(("error", "{}: {}".format(type(exc).__name__, exc)))
    finally:
        connection.close()


def run_with_deadline(function, arguments, timeout):
    """Run a serializable module-level callable in an isolated bounded worker."""
    if timeout <= 0:
        raise ValueError("Deadline must be positive")
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_worker, args=(function, arguments, sender))
    process.daemon = True
    process.start()
    sender.close()
    try:
        if not receiver.poll(timeout):
            raise RuntimeError("ROS operation exceeded {} wall-clock seconds including startup. Check ROS_MASTER_URI, master, network, topic and factory environment".format(timeout))
        try:
            status, payload = receiver.recv()
        except EOFError:
            raise RuntimeError("ROS worker exited before returning a result; inspect the factory environment")
        if status != "ok":
            raise RuntimeError(payload)
        return payload
    finally:
        receiver.close()
        process.join(0.3)
        if process.is_alive():
            process.terminate()
            process.join(1.0)
        if process.is_alive() and os.name == "posix":
            # Python 3.6 has no Process.kill().
            os.kill(process.pid, signal.SIGKILL)
            process.join(1.0)
