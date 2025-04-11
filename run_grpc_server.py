# run_grpc_server.py (place in project root or scripts/)
import asyncio
import grpc
import logging

# Import generated code and service implementation
from app.grpc.generated import workflow_pb2_grpc
from app.grpc.server import WorkflowServiceImpl

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def serve() -> None:
    server = grpc.aio.server()
    workflow_pb2_grpc.add_WorkflowServiceServicer_to_server(
        WorkflowServiceImpl(), server
    )

    listen_addr = "[::]:50051" # Standard gRPC port, listen on all interfaces
    server.add_insecure_port(listen_addr)

    logger.info(f"Starting gRPC server on {listen_addr}")
    await server.start()
    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Stopping server...")
        await server.stop(0) # Graceful stop
        logger.info("Server stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(serve())
    except Exception as e:
        logger.exception(f"Failed to run gRPC server: {e}")