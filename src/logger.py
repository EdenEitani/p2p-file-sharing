import logging
import sys

def setup_logger(name='p2p_client', log_file='p2p_client.log', level=logging.DEBUG):
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    logger.handlers = []
    
    logger.propagate = False

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)

    log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(log_format)
    file_handler.setFormatter(log_format)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger