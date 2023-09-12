from flask import Flask, jsonify, request
from redis_connector import redis_connector
import os

import redis
import json
import requests
import schedule
import time
import threading
import requests
from flask_cors import CORS, cross_origin

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
app.config["DEBUG"] = True

redis_client = redis_connector()
# Service Registry Class
class ServiceRegistry:

    @staticmethod
    def register_service(service_name, service_host, service_port, parameters):
        try:
            service_data = {
                "host": service_host,
                "port": service_port,
                "parameters": parameters,
                "status": "UP"
            }

            redis_key = f"services:{service_name}"
            redis_client.set(redis_key, json.dumps(service_data))
            return f"Registered service '{service_name}' with host '{service_host}' and port '{service_port}' in Redis.", 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

# Register a service with parameters
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Invalid JSON data"}), 400

    service_name = data.get("service_name")
    service_host = data.get("service_host")
    service_port = data.get("service_port")
    parameters = data.get("parameters", {})

    if not service_name or not service_host or not service_port:
        return jsonify({"error": "Missing required fields"}), 400

    return ServiceRegistry.register_service(service_name, service_host, service_port, parameters)


# Deregister a service
@app.route('/deregister/<service_name>', methods=['DELETE'])
def deregister(service_name):
    redis_key = f"services:{service_name}"
    if redis_client.exists(redis_key):
        redis_client.delete(redis_key)
        return f"Deregistered service '{service_name}' from Redis.", 200
    else:
        return f"Service '{service_name}' not found in Redis.", 404

# Get service details by service name
@app.route('/service/<service_name>', methods=['GET'])
def get_service_details(service_name):
    try:
        redis_key = f"services:{service_name}"
        service_data = redis_client.get(redis_key)

        if service_data:
            return jsonify(json.loads(service_data.decode('utf-8'))), 200
        else:
            return jsonify({"error": f"Service '{service_name}' not found in Redis."}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# Function to perform health checks
def perform_health_checks():
    
    try:
        # Retrieve all service names from Redis
        service_keys = redis_client.keys("services:*")

        for redis_key in service_keys:
            service_data = json.loads(redis_client.get(redis_key).decode('utf-8'))

            if service_data["status"] == "UP":
                service_name = redis_key.decode('utf-8').split(":")[1]
                service_host = service_data["host"]
                service_port = service_data["port"]

                # Perform a health check by sending a GET request to the service
                try:
                    response = requests.get(f"http://{service_host}:{service_port}/health", timeout=5)

                    if response.status_code != 200:
                        # If the response status code is not 200, mark the service as DOWN
                        service_data["status"] = "DOWN"
                        redis_client.set(redis_key, json.dumps(service_data))

                except Exception as e:
                    # If there is an exception (e.g., connection error), mark the service as DOWN
                    service_data["status"] = "DOWN"
                    redis_client.set(redis_key, json.dumps(service_data))

    except Exception as e:
        print(f"Error performing health checks: {str(e)}")

# Schedule health checks every 1 minute
schedule.every(1).minutes.do(perform_health_checks)




# Function to run the scheduled tasks in a separate thread
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    # Start the scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.start()


app.run(host=os.getenv('IP', '0.0.0.0'), port=int(os.getenv('PORT', 8080)))