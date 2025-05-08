from unittest.mock import AsyncMock, patch


def patch_rest_client(module_path):
    """Decorator for patching rest client in test functions.

    This is a more convenient way to mock the REST client compared to using fixtures.
    The mock client is passed as the first argument to the test function.

    Example usage:

    ```python
    @pytest.mark.asyncio
    @patch_rest_client("mcp_panther.panther_mcp_core.tools.rules")
    async def test_list_rules_success(mock_client):
        # Configure the mock for this specific test
        mock_client.get.return_value = ({"results": []}, 200)

        # Call the function that uses the client
        result = await list_rules()

        # Make assertions
        assert result["success"] is True
    ```

    Args:
        module_path (str): The import path to the module containing get_rest_client.

    Returns:
        function: Decorated test function with mock client injected
    """

    def decorator(test_func):
        async def wrapper(*args, **kwargs):
            patch_obj = patch(f"{module_path}.get_rest_client")
            client = AsyncMock()
            client.__aenter__.return_value = client
            client.__aexit__.return_value = None
            with patch_obj as mock_get_client:
                mock_get_client.return_value = client
                return await test_func(client, *args, **kwargs)

        return wrapper

    return decorator


def patch_graphql_client(module_path):
    """Decorator for patching the GraphQL client in test functions.

    This is a more convenient way to mock the GraphQL client compared to using fixtures.
    The mock client is passed as the first argument to the test function.

    Example usage:

    ```python
    @pytest.mark.asyncio
    @patch_graphql_client("mcp_panther.panther_mcp_core.tools.alerts")
    async def test_list_alerts(mock_client):
        # Configure the mock
        mock_client.execute.return_value = {"data": {"alerts": []}}

        # Call the function that uses the client
        result = await list_alerts()

        # Make assertions
        assert result["success"] is True
    ```

    Args:
        module_path (str): The import path to the module containing _create_panther_client.

    Returns:
        function: Decorated test function with mock client injected
    """

    def decorator(test_func):
        async def wrapper(*args, **kwargs):
            patch_obj = patch(f"{module_path}._create_panther_client")
            client = AsyncMock()
            client.execute = AsyncMock()
            client.__aenter__.return_value = client
            client.__aexit__.return_value = None

            with patch_obj as mock_create_client:
                mock_create_client.return_value = client
                return await test_func(client, *args, **kwargs)

        return wrapper

    return decorator


def patch_execute_query(module_path):
    """Decorator for patching the GraphQL client's _execute_query method in test functions.

    This is a convenient way to mock GraphQL query execution compared to using fixtures.
    The mock query executor is passed as the first argument to the test function.

    Example usage:

    ```python
    @pytest.mark.asyncio
    @patch_execute_query("mcp_panther.panther_mcp_core.tools.alerts")
    async def test_list_alerts(mock_execute_query):
        # Configure the mock
        mock_execute_query.return_value = {"data": {"alerts": []}}

        # Call the function that uses _execute_query
        result = await list_alerts()

        # Make assertions
        assert result["success"] is True
    ```

    Args:
        module_path (str): The import path to the module containing _execute_query.

    Returns:
        function: Decorated test function with mock execute_query injected
    """

    def decorator(test_func):
        async def wrapper(*args, **kwargs):
            with patch(f"{module_path}._execute_query") as mock:
                return await test_func(mock, *args, **kwargs)

        return wrapper

    return decorator
