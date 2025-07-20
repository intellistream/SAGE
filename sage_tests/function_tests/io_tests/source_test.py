import pytest

from sage_libs.io.source import FileSource


@pytest.fixture
def sample_file(tmp_path):
    file_path = tmp_path / "sample.txt"
    content = "line1\nline2\nline3\n"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return file_path

def test_file_source_reads_lines(sample_file):
    fs = FileSource(config={"data_path": str(sample_file)})
    # 读第一行
    data1 = fs.execute()
    assert data1 == "line1"

    # 读第二行
    data2 = fs.execute()
    assert data2 == "line2"

    # 读第三行
    data3 = fs.execute()
    assert data3 == "line3"

