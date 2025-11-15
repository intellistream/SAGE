import pytest

from sage.libs.io.sink import FileSink, MemWriteSink, RetriveSink, TerminalSink


@pytest.fixture
def sample_qa_data():
    return ("What is AI?", "Artificial Intelligence")


@pytest.fixture
def sample_chunks_data():
    return ("Explain AI", ["AI is ...", "It involves ..."])


@pytest.fixture
def temp_file_path(tmp_path):
    return tmp_path / "test_output.txt"


def test_terminal_sink(capsys, sample_qa_data):
    sink = TerminalSink(config={})
    sink.execute(sample_qa_data)
    captured = capsys.readouterr()
    assert "[Q] Question :" in captured.out
    assert "[A] Answer :" in captured.out


def test_retrive_sink(capsys, sample_chunks_data):
    sink = RetriveSink(config={})
    sink.execute(sample_chunks_data)
    captured = capsys.readouterr()
    assert "[Q] Question :" in captured.out
    assert "[A] Chunks :" in captured.out


def test_file_sink_writes(tmp_path, sample_qa_data):
    file_path = tmp_path / "qa_output.txt"
    sink = FileSink(config={"file_path": str(file_path)})
    sink.execute(sample_qa_data)
    with open(file_path, encoding="utf-8") as f:
        content = f.read()
    assert "Question:" in content
    assert "Answer  :" in content


def test_mem_write_sink_various_inputs(tmp_path):
    file_path = tmp_path / "mem_output.txt"
    sink = MemWriteSink(config={"file_path": str(file_path)})

    # Test with a string
    sink.execute("single string")
    # Test with list of strings
    sink.execute(["list", "of", "strings"])
    # Test with tuple of strings (any length)
    sink.execute(("tuple", "of", "strings"))

    with open(file_path, encoding="utf-8") as f:
        lines = f.readlines()

    # Check that lines were written (should be at least the header + entries)
    assert any("single string" in line for line in lines)
    assert any("list" in line for line in lines)
    assert any("tuple" in line for line in lines)


def test_mem_write_sink_handles_non_string(tmp_path):
    file_path = tmp_path / "mem_output.txt"
    sink = MemWriteSink(config={"file_path": str(file_path)})

    # Provide a non-string input - MemWriteSink can handle any type via _parse_input
    sink.execute(12345)
    with open(file_path, encoding="utf-8") as f:
        content = f.read()
    assert "12345" in content
