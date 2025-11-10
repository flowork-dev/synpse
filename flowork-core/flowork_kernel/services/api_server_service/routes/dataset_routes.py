########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\api_server_service\routes\dataset_routes.py total lines 148 
########################################################################

from .base_api_route import BaseApiRoute
class DatasetRoutes(BaseApiRoute):
    """
    Manages API routes for dataset CRUD operations.
    """
    def register_routes(self):
        return {
            "GET /api/v1/datasets": self.handle_get_datasets,
            "POST /api/v1/datasets": self.handle_post_datasets,
            "DELETE /api/v1/datasets/{dataset_name}": self.handle_delete_dataset,
            "GET /api/v1/datasets/{dataset_name}/data": self.handle_get_dataset_data,
            "POST /api/v1/datasets/{dataset_name}/data": self.handle_post_dataset_data,
            "PUT /api/v1/datasets/{dataset_name}/data": self.handle_put_dataset_row,
            "DELETE /api/v1/datasets/{dataset_name}/data/{row_id}": self.handle_delete_dataset_row,
        }
    async def handle_get_datasets(self, request):
        dataset_manager = self.service_instance.dataset_manager_service
        if not dataset_manager:
            return self._json_response(
                {"error": "DatasetManagerService is not available."}, status=503
            )
        datasets = dataset_manager.list_datasets()
        return self._json_response(datasets)
    async def handle_post_datasets(self, request):
        dataset_manager = self.service_instance.dataset_manager_service
        if not dataset_manager:
            return self._json_response(
                {"error": "DatasetManagerService is not available."}, status=503
            )
        body = await request.json()
        if "name" not in body:
            return self._json_response(
                {"error": "Request body must contain 'name' for the new dataset."},
                status=400,
            )
        success = dataset_manager.create_dataset(body["name"])
        if success:
            return self._json_response(
                {"status": "success", "message": f"Dataset '{body['name']}' created."},
                status=201,
            )
        else:
            return self._json_response(
                {
                    "error": f"Dataset '{body['name']}' already exists or could not be created."
                },
                status=409,
            )
    async def handle_get_dataset_data(self, request):
        dataset_name = request.match_info.get("dataset_name")
        dataset_manager = self.service_instance.dataset_manager_service
        if not dataset_manager:
            return self._json_response(
                {"error": "DatasetManagerService is not available."}, status=503
            )
        data = dataset_manager.get_dataset_data(dataset_name)
        return self._json_response(data)
    async def handle_post_dataset_data(self, request):
        dataset_name = request.match_info.get("dataset_name")
        dataset_manager = self.service_instance.dataset_manager_service
        if not dataset_manager:
            return self._json_response(
                {"error": "DatasetManagerService is not available."}, status=503
            )
        body = await request.json()
        if "data" not in body or not isinstance(body["data"], list):
            return self._json_response(
                {
                    "error": "Request body must contain a 'data' list of prompt/response objects."
                },
                status=400,
            )
        success = dataset_manager.add_data_to_dataset(dataset_name, body["data"])
        if success:
            return self._json_response(
                {
                    "status": "success",
                    "message": f"Added {len(body['data'])} records to dataset '{dataset_name}'.",
                }
            )
        else:
            return self._json_response(
                {"error": f"Failed to add data to dataset '{dataset_name}'."},
                status=500,
            )
    async def handle_delete_dataset(self, request):
        dataset_name = request.match_info.get("dataset_name")
        dataset_manager = self.service_instance.dataset_manager_service
        if not dataset_manager:
            return self._json_response(
                {"error": "DatasetManagerService is not available."}, status=503
            )
        if not dataset_name:
            return self._json_response(
                {"error": "Dataset name is required for deletion."}, status=400
            )
        success = dataset_manager.delete_dataset(dataset_name)
        if success:
            return self._json_response(None, status=204)
        else:
            return self._json_response(
                {"error": f"Dataset '{dataset_name}' not found."}, status=404
            )
    async def handle_put_dataset_row(self, request):
        dataset_name = request.match_info.get("dataset_name")
        dataset_manager = self.service_instance.dataset_manager_service
        if not dataset_manager:
            return self._json_response(
                {"error": "DatasetManagerService is not available."}, status=503
            )
        body = await request.json()
        if "id" not in body:
            return self._json_response(
                {
                    "error": "Request body must contain the row data, including its 'id'."
                },
                status=400,
            )
        success = dataset_manager.update_dataset_row(dataset_name, body)
        if success:
            return self._json_response(
                {"status": "success", "message": f"Row {body['id']} updated."}
            )
        else:
            return self._json_response(
                {"error": "Dataset or Row ID not found."}, status=404
            )
    async def handle_delete_dataset_row(self, request):
        dataset_name = request.match_info.get("dataset_name")
        row_id = request.match_info.get("row_id")
        dataset_manager = self.service_instance.dataset_manager_service
        if not dataset_manager:
            return self._json_response(
                {"error": "DatasetManagerService is not available."}, status=503
            )
        success = dataset_manager.delete_dataset_row(dataset_name, row_id)
        if success:
            return self._json_response(None, status=204)
        else:
            return self._json_response(
                {"error": "Dataset or Row ID not found."}, status=404
            )
