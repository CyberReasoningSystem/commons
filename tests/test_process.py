from commons import process


def test_arguments() -> None:
    created_process = process.create_process(
        "others/streams_checkers/bin/arguments",
        process.InputStream.ARGUMENTS,
        [b"ping"],
    )
    process.execute_process(created_process)
    assert created_process.output.startswith(b"pong")


def test_stdin() -> None:
    created_process = process.create_process(
        "others/streams_checkers/bin/stdin",
        process.InputStream.STDIN,
        b"ping\n",
    )
    process.execute_process(created_process)
    assert created_process.output.startswith(b"pong")


def test_file() -> None:
    created_process = process.create_process(
        "others/streams_checkers/bin/file",
        process.InputStream.FILES,
        b"ping",
    )
    process.execute_process(created_process)
    assert created_process.output.startswith(b"pong")
