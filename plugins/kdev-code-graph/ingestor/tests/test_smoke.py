import kdev_ingestor


def test_package_importable():
    assert kdev_ingestor.__version__ == "0.1.0"
