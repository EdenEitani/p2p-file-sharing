import logging

def setup_logger(name='p2p_client', log_file='p2p_client.log', level=logging.DEBUG):
    """Set up logger with file and console handlers"""
    
    logger = logging.getLogger(name)
    logger.setLevel(level)

    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler(log_file)
    
    console_handler.setLevel(level)
    file_handler.setLevel(level)

    log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(log_format)
    file_handler.setFormatter(log_format)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
