import yaml

# Read Redis connection details from the YAML file
config_file = "redis_config.yaml"  # Adjust the filename as needed

def redis_connector():

    try:
        with open(config_file, "r") as file:
            redis_config = yaml.safe_load(file)
    except FileNotFoundError:
        print(f"Configuration file '{config_file}' not found.")
        exit(1)

    # Connect to Redis using the configuration
    import redis

    redis_host = redis_config["redis_host"]
    redis_port = redis_config["redis_port"]
    redis_db = redis_config["redis_db"]

    redis_client = redis.StrictRedis(host=redis_host, port=redis_port, db=redis_db)

    return redis_client

