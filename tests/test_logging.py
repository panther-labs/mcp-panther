import logging

from mcp_panther.server import configure_logging, logger


def test_configure_logging_file(tmp_path):
    log_file = tmp_path / "out.log"
    configure_logging(str(log_file), force=True)
    logger.setLevel(logging.INFO)
    logger.info("test message")
    fast_logger = logging.getLogger("FastMCP.test")
    fast_logger.setLevel(logging.INFO)
    fast_logger.info("fast message")
    logging.shutdown()
    data = log_file.read_text()
    assert "test message" in data
    assert "fast message" in data
    # reset to stderr to avoid side effects
    configure_logging(force=True)
    logger.setLevel(logging.WARNING)
