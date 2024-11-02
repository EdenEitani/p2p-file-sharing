# First time setup
chmod +x setup.sh
./setup.sh

# Build and start all services
docker-compose up --build

# Attach to specific container
docker-compose exec seeder bash    # Connect to seeder
docker-compose exec leecher1 bash  # Connect to leecher1
docker-compose exec leecher2 bash  # Connect to leecher2

# View logs for specific service
docker-compose logs -f seeder
docker-compose logs -f leecher1
docker-compose logs -f leecher2

# Stop all services
docker-compose down

# Restart specific service
docker-compose restart leecher1

# Testing the system:
# 1. Connect to seeder:
docker-compose exec seeder bash
# Then share a file:
python src/client_handler.py 172.20.0.3 8001 172.20.0.2 8888

# 2. Connect to leecher1 or leecher2:
docker-compose exec leecher1 bash
# Then download the file:
python src/client_handler.py 172.20.0.4 8002 172.20.0.2 8888