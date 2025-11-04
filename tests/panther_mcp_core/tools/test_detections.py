import pytest

from mcp_panther.panther_mcp_core.tools.detections import (
    disable_detection,
    get_detection,
    list_detections,
)
from tests.utils.helpers import patch_rest_client

MOCK_RULE = {
    "id": "New.sign-in",
    "body": 'def rule(event):\n    # Return True to match the log event and trigger an alert.\n    return event.get("actionName") == "SIGN_IN"\n\ndef title(event):\n    # (Optional) Return a string which will be shown as the alert title.\n    # If no \'dedup\' function is defined, the return value of this method will act as deduplication string.\n\n    default_name = "A user"\n    id = None\n    email = None\n    name = None\n\n    actor = event.get("actor")\n    if actor:\n        id = actor.get("id")\n        name = actor.get("name")\n        attributes = actor.get("attributes")\n        email = attributes.get("email")\n\n    display_name = name or email or id or default_name\n\n    return f"{display_name} logged into Panther"',
    "dedupPeriodMinutes": 60,
    "description": "",
    "displayName": "New sign-in",
    "enabled": True,
    "logTypes": ["Panther.Audit"],
    "managed": False,
    "outputIDs": ["prod-slack", "prod-pagerduty"],
    "runbook": "",
    "severity": "MEDIUM",
    "threshold": 1,
    "createdBy": {"id": "user-123", "type": "User"},
    "createdAt": "2024-11-14T17:09:49.841715953Z",
    "lastModified": "2024-11-14T17:09:49.841716265Z",
    "tags": ["Authentication", "Login"],
    "tests": [
        {
            "expectedResult": False,
            "name": "Random Event",
            "resource": '{"actionName":"SIGN_OUT","actor":{"attributes":{"email":"derek@example.com"},"id":"1337","name":"Derek"}}',
        },
        {
            "expectedResult": False,
            "name": "Sign In Test",
            "resource": '{"actionName":"SIGN_IN","actor":{"attributes":{"email":"derek@example.com"},"id":"1337","name":"Derek"}}',
        },
    ],
    "reports": {"SOC2": ["CC6.1", "CC6.3"], "PCI DSS": ["Requirement 10.2"]},
    "summaryAttributes": ["actor.name", "actor.attributes.email"],
}


MOCK_RULE_HIGH_SEVERITY = {
    **MOCK_RULE,
    "id": "High.severity",
    "displayName": "Another rule with high severity",
    "severity": "HIGH",
    "outputIDs": ["dev-slack"],
}

MOCK_RULES_RESPONSE = {
    "results": [MOCK_RULE, MOCK_RULE_HIGH_SEVERITY],
    "next": "next-page-token",
}

RULES_MODULE_PATH = "mcp_panther.panther_mcp_core.tools.detections"


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_rules_success(mock_rest_client):
    """Test successful listing of rules."""
    mock_rest_client.get.return_value = (MOCK_RULES_RESPONSE, 200)

    result = await list_detections(["rules"])

    assert result["success"] is True
    assert len(result["rules"]) == 2
    assert result["total_rules"] == 2
    assert result["has_next_page"] is True
    assert result["next_cursor"] == "next-page-token"

    first_rule = result["rules"][0]
    assert first_rule["id"] == MOCK_RULE["id"]
    assert first_rule["severity"] == MOCK_RULE["severity"]
    assert first_rule["displayName"] == MOCK_RULE["displayName"]
    assert first_rule["enabled"] is True
    assert first_rule["threshold"] == MOCK_RULE["threshold"]
    assert first_rule["dedupPeriodMinutes"] == MOCK_RULE["dedupPeriodMinutes"]
    assert first_rule["createdBy"] == MOCK_RULE["createdBy"]
    assert first_rule["outputIDs"] == MOCK_RULE["outputIDs"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_rules_with_pagination(mock_rest_client):
    """Test listing rules with pagination."""
    mock_rest_client.get.return_value = (MOCK_RULES_RESPONSE, 200)

    await list_detections(["rules"], cursor="some-cursor", limit=50)

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == "/rules"
    assert kwargs["params"]["cursor"] == "some-cursor"
    assert kwargs["params"]["limit"] == 50


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_rules_error(mock_rest_client):
    """Test handling of errors when listing rules."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await list_detections(["rules"])

    assert result["success"] is False
    assert "Failed" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_with_output_ids_filter(mock_rest_client):
    """Test client-side filtering by output_ids."""
    mock_rest_client.get.return_value = (MOCK_RULES_RESPONSE, 200)

    # Filter for prod-slack (only in MOCK_RULE, not in MOCK_RULE_HIGH_SEVERITY)
    result = await list_detections(["rules"], output_ids=["prod-slack"])

    assert result["success"] is True
    assert len(result["rules"]) == 1
    assert result["rules"][0]["id"] == MOCK_RULE["id"]
    assert "prod-slack" in result["rules"][0]["outputIDs"]

    # Filter for dev-slack (only in MOCK_RULE_HIGH_SEVERITY)
    result = await list_detections(["rules"], output_ids=["dev-slack"])

    assert result["success"] is True
    assert len(result["rules"]) == 1
    assert result["rules"][0]["id"] == MOCK_RULE_HIGH_SEVERITY["id"]
    assert "dev-slack" in result["rules"][0]["outputIDs"]

    # Filter for both (should return both rules)
    result = await list_detections(["rules"], output_ids=["prod-slack", "dev-slack"])

    assert result["success"] is True
    assert len(result["rules"]) == 2

    # Filter for non-existent output ID (should return no results)
    result = await list_detections(["rules"], output_ids=["nonexistent-output"])

    assert result["success"] is True
    assert len(result["rules"]) == 0


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_get_detection_rule_success(mock_rest_client):
    """Test successful retrieval of a single rule."""
    mock_rest_client.get.return_value = (MOCK_RULE, 200)

    result = await get_detection(MOCK_RULE["id"], ["rules"])

    assert result["success"] is True
    assert result["rule"]["id"] == MOCK_RULE["id"]
    assert result["rule"]["severity"] == MOCK_RULE["severity"]
    assert result["rule"]["body"] == MOCK_RULE["body"]
    assert len(result["rule"]["tests"]) == 2

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == f"/rules/{MOCK_RULE['id']}"


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_get_detection_rule_not_found(mock_rest_client):
    """Test handling of non-existent rule."""
    mock_rest_client.get.return_value = ({}, 404)

    result = await get_detection("nonexistent-rule", ["rules"])

    assert result["success"] is False
    assert (
        "No detection found with ID nonexistent-rule in any of the specified types"
        in result["message"]
    )


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_get_detection_rule_error(mock_rest_client):
    """Test handling of errors when getting rule by ID."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await get_detection(MOCK_RULE["id"], ["rules"])

    assert result["success"] is False
    assert "Failed" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_disable_detection_success(mock_rest_client):
    """Test successful disabling of a rule."""
    # For the disable_detection test, we need two responses:
    # 1. GET to fetch current rule data
    # 2. PUT to update with enabled=False
    mock_rest_client.get.return_value = (MOCK_RULE, 200)
    disabled_rule = {**MOCK_RULE, "enabled": False}
    mock_rest_client.put.return_value = (disabled_rule, 200)

    result = await disable_detection(MOCK_RULE["id"], "rules")

    assert result["success"] is True
    assert result["rule"]["enabled"] is False

    mock_rest_client.put.assert_called_once()
    args, kwargs = mock_rest_client.put.call_args
    assert args[0] == f"/rules/{MOCK_RULE['id']}"
    assert kwargs["json_data"]["enabled"] is False
    assert kwargs["params"]["run-tests-first"] == "false"


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_disable_detection_not_found(mock_rest_client):
    """Test disabling a non-existent rule."""
    mock_rest_client.get.return_value = ({}, 404)

    result = await disable_detection("nonexistent-rule", "rules")

    assert result["success"] is False
    assert "Rules with ID nonexistent-rule not found" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_disable_detection_error(mock_rest_client):
    """Test handling of errors when disabling a rule."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await disable_detection(MOCK_RULE["id"], "rules")

    assert result["success"] is False
    assert "Failed" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_scheduled_rules_success(mock_rest_client):
    """Test successful listing of scheduled rules."""
    mock_scheduled_rule_base = {
        **MOCK_RULE,
        "id": "scheduled.data.exfiltration",
        "displayName": "Scheduled Data Exfiltration Check",
        "scheduledQueries": [
            "SELECT * FROM data_movement WHERE bytes_transferred > 1000000 AND destination_ip NOT IN (trusted_ips)"
        ],
    }

    mock_scheduled_rule_variation = {
        **mock_scheduled_rule_base,
        "id": "scheduled.unused.credentials",
        "displayName": "Scheduled Unused Credentials Check",
        "scheduledQueries": [
            "SELECT * FROM credential_usage WHERE last_used < NOW() - INTERVAL '90 days'"
        ],
    }

    mock_scheduled_rules = {
        "results": [mock_scheduled_rule_base, mock_scheduled_rule_variation],
        "next": "next-token",
    }
    mock_rest_client.get.return_value = (mock_scheduled_rules, 200)

    result = await list_detections(["scheduled_rules"])

    assert result["success"] is True
    assert len(result["scheduled_rules"]) == 2
    assert result["total_scheduled_rules"] == 2
    assert result["has_next_page"] is True

    mock_rest_client.get.assert_called_once()
    args, _ = mock_rest_client.get.call_args
    assert args[0] == "/scheduled-rules"


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_scheduled_rules_error(mock_rest_client):
    """Test handling of errors when listing scheduled rules."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await list_detections(["scheduled_rules"])

    assert result["success"] is False
    assert "Failed" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_scheduled_rules_with_pagination(mock_rest_client):
    """Test pagination for listing scheduled rules."""
    scheduled_rules_response = {
        "results": [
            {
                "id": "scheduled.test.rule",
                "displayName": "Test Scheduled Rule",
                "scheduledQueries": ["SELECT * FROM test"],
            }
        ],
        "next": "next-scheduled-token",
    }
    mock_rest_client.get.return_value = (scheduled_rules_response, 200)

    await list_detections(["scheduled_rules"], cursor="some-cursor", limit=25)

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == "/scheduled-rules"
    assert kwargs["params"]["cursor"] == "some-cursor"
    assert kwargs["params"]["limit"] == 25


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_get_detection_scheduled_rule_success(mock_rest_client):
    """Test successful retrieval of a single scheduled rule."""
    scheduled_rule = {
        **MOCK_RULE,
        "id": "scheduled.data.exfiltration",
        "displayName": "Scheduled Data Exfiltration Check",
        "scheduledQueries": [
            "SELECT * FROM data_movement WHERE bytes_transferred > 1000000 AND destination_ip NOT IN (trusted_ips)"
        ],
    }
    mock_rest_client.get.return_value = (scheduled_rule, 200)

    result = await get_detection(scheduled_rule["id"], ["scheduled_rules"])

    assert result["success"] is True
    assert result["scheduled_rule"]["id"] == scheduled_rule["id"]
    assert "scheduledQueries" in result["scheduled_rule"]
    assert len(result["scheduled_rule"]["scheduledQueries"]) == 1


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_get_detection_scheduled_rule_not_found(mock_rest_client):
    """Test handling of non-existent scheduled rule."""
    mock_rest_client.get.return_value = ({}, 404)

    result = await get_detection("nonexistent.scheduled.rule", ["scheduled_rules"])

    assert result["success"] is False
    assert (
        "No detection found with ID nonexistent.scheduled.rule in any of the specified types"
        in result["message"]
    )


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_get_detection_scheduled_rule_error(mock_rest_client):
    """Test handling of errors when getting scheduled rule by ID."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await get_detection("scheduled.rule.id", ["scheduled_rules"])

    assert result["success"] is False
    assert "Failed" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_simple_rules_success(mock_rest_client):
    """Test successful listing of simple rules."""
    simple_rule_base = {
        **MOCK_RULE,
        "id": "simple.ip.blocklist",
        "displayName": "Simple IP Blocklist Rule",
        "description": "Alerts on traffic from known malicious IPs",
    }

    simple_rule_variation = {
        **simple_rule_base,
        "id": "simple.domain.blocklist",
        "displayName": "Simple Domain Blocklist Rule",
        "description": "Alerts on traffic to known malicious domains",
    }

    mock_simple_rules = {
        "results": [simple_rule_base, simple_rule_variation],
        "next": "next-token",
    }
    mock_rest_client.get.return_value = (mock_simple_rules, 200)

    result = await list_detections(["simple_rules"])

    assert result["success"] is True
    assert len(result["simple_rules"]) == 2
    assert result["total_simple_rules"] == 2
    assert result["has_next_page"] is True

    mock_rest_client.get.assert_called_once()
    args, _ = mock_rest_client.get.call_args
    assert args[0] == "/simple-rules"


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_simple_rules_with_pagination(mock_rest_client):
    """Test pagination for listing simple rules."""
    simple_rules_response = {
        "results": [{"id": "simple.test.rule", "displayName": "Test Simple Rule"}],
        "next": "next-simple-token",
    }
    mock_rest_client.get.return_value = (simple_rules_response, 200)

    await list_detections(["simple_rules"], cursor="simple-cursor", limit=30)

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == "/simple-rules"
    assert kwargs["params"]["cursor"] == "simple-cursor"
    assert kwargs["params"]["limit"] == 30


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_simple_rules_error(mock_rest_client):
    """Test handling of errors when listing simple rules."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await list_detections(["simple_rules"])

    assert result["success"] is False
    assert "Failed" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_get_detection_simple_rule_success(mock_rest_client):
    """Test successful retrieval of a single simple rule."""
    simple_rule = {
        **MOCK_RULE,
        "id": "simple.ip.blocklist",
        "displayName": "Simple IP Blocklist Rule",
        "description": "Alerts on traffic from known malicious IPs",
    }
    mock_rest_client.get.return_value = (simple_rule, 200)

    result = await get_detection(simple_rule["id"], ["simple_rules"])

    assert result["success"] is True
    assert result["simple_rule"]["id"] == simple_rule["id"]
    assert result["simple_rule"]["displayName"] == simple_rule["displayName"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_get_detection_simple_rule_not_found(mock_rest_client):
    """Test handling of non-existent simple rule."""
    mock_rest_client.get.return_value = ({}, 404)

    result = await get_detection("nonexistent.simple.rule", ["simple_rules"])

    assert result["success"] is False
    assert (
        "No detection found with ID nonexistent.simple.rule in any of the specified types"
        in result["message"]
    )


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_get_detection_simple_rule_error(mock_rest_client):
    """Test handling of errors when getting simple rule by ID."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await get_detection("simple.rule.id", ["simple_rules"])

    assert result["success"] is False
    assert "Failed" in result["message"]


# Policy Tests
MOCK_POLICY = {
    "id": "AWS.S3.Bucket.PublicReadACP",
    "body": 'def policy(resource):\n    # Return True if the resource fails the policy check\n    return resource.get("Grants", []) != []\n',
    "description": "S3 bucket should not allow public read access to ACL",
    "displayName": "S3 Bucket Public Read ACP",
    "enabled": True,
    "resourceTypes": ["AWS.S3.Bucket"],
    "managed": False,
    "severity": "HIGH",
    "createdBy": {"id": "user-456", "type": "User"},
    "createdAt": "2024-11-14T17:09:49.841715953Z",
    "lastModified": "2024-11-14T17:09:49.841716265Z",
    "tags": ["AWS", "S3", "Security"],
    "tests": [
        {
            "expectedResult": False,
            "name": "Private Bucket",
            "resource": '{"Grants": []}',
        },
        {
            "expectedResult": True,
            "name": "Public Bucket",
            "resource": '{"Grants": [{"Grantee": {"Type": "Group", "URI": "http://acs.amazonaws.com/groups/global/AllUsers"}}]}',
        },
    ],
    "reports": {"SOC2": ["CC6.1"], "CIS": ["2.1.1"]},
}

MOCK_POLICY_MEDIUM_SEVERITY = {
    **MOCK_POLICY,
    "id": "AWS.EC2.Instance.UnencryptedVolume",
    "displayName": "EC2 Instance with Unencrypted Volume",
    "severity": "MEDIUM",
    "resourceTypes": ["AWS.EC2.Instance"],
}

MOCK_POLICIES_RESPONSE = {
    "results": [MOCK_POLICY, MOCK_POLICY_MEDIUM_SEVERITY],
    "next": "next-policy-token",
}


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_policies_success(mock_rest_client):
    """Test successful listing of policies."""
    mock_rest_client.get.return_value = (MOCK_POLICIES_RESPONSE, 200)

    result = await list_detections(["policies"])

    assert result["success"] is True
    assert len(result["policies"]) == 2
    assert result["total_policies"] == 2
    assert result["has_next_page"] is True
    assert result["next_cursor"] == "next-policy-token"

    first_policy = result["policies"][0]
    assert first_policy["id"] == MOCK_POLICY["id"]
    assert first_policy["severity"] == MOCK_POLICY["severity"]
    assert first_policy["displayName"] == MOCK_POLICY["displayName"]
    assert first_policy["enabled"] is True
    assert first_policy["resourceTypes"] == MOCK_POLICY["resourceTypes"]
    assert first_policy["createdBy"] == MOCK_POLICY["createdBy"]

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == "/policies"


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_policies_with_pagination(mock_rest_client):
    """Test listing policies with pagination."""
    mock_rest_client.get.return_value = (MOCK_POLICIES_RESPONSE, 200)

    await list_detections(["policies"], cursor="some-policy-cursor", limit=50)

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == "/policies"
    assert kwargs["params"]["cursor"] == "some-policy-cursor"
    assert kwargs["params"]["limit"] == 50


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_policies_error(mock_rest_client):
    """Test handling of errors when listing policies."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await list_detections(["policies"])

    assert result["success"] is False
    assert "Failed to list detection types ['policies']" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_get_detection_policy_success(mock_rest_client):
    """Test successful retrieval of a single policy."""
    mock_rest_client.get.return_value = (MOCK_POLICY, 200)

    result = await get_detection(MOCK_POLICY["id"], ["policies"])

    assert result["success"] is True
    assert result["policy"]["id"] == MOCK_POLICY["id"]
    assert result["policy"]["severity"] == MOCK_POLICY["severity"]
    assert result["policy"]["body"] == MOCK_POLICY["body"]
    assert len(result["policy"]["tests"]) == 2
    assert result["policy"]["resourceTypes"] == MOCK_POLICY["resourceTypes"]

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == f"/policies/{MOCK_POLICY['id']}"


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_get_detection_policy_not_found(mock_rest_client):
    """Test handling of non-existent policy."""
    mock_rest_client.get.return_value = ({}, 404)

    result = await get_detection("nonexistent-policy", ["policies"])

    assert result["success"] is False
    assert (
        "No detection found with ID nonexistent-policy in any of the specified types"
        in result["message"]
    )


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_get_detection_policy_error(mock_rest_client):
    """Test handling of errors when getting policy by ID."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await get_detection(MOCK_POLICY["id"], ["policies"])

    assert result["success"] is False
    assert "Failed to get detection details for types ['policies']" in result["message"]


@pytest.mark.asyncio
async def test_list_detections_invalid_detection_type():
    """Test validation of invalid detection_type parameter."""
    result = await list_detections(["invalid_type"])

    assert result["success"] is False
    assert "Invalid detection_types ['invalid_type']" in result["message"]
    assert (
        "Valid values are: rules, scheduled_rules, simple_rules, policies"
        in result["message"]
    )


@pytest.mark.asyncio
async def test_get_detection_invalid_detection_type():
    """Test validation of invalid detection_type parameter."""
    result = await get_detection("some-id", ["invalid_type"])

    assert result["success"] is False
    assert "Invalid detection_types ['invalid_type']" in result["message"]
    assert (
        "Valid values are: rules, scheduled_rules, simple_rules, policies"
        in result["message"]
    )


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_multiple_types(mock_rest_client):
    """Test listing multiple detection types."""

    # Mock responses for both rules and policies
    def side_effect(endpoint, **kwargs):
        if endpoint == "/rules":
            return (MOCK_RULES_RESPONSE, 200)
        elif endpoint == "/policies":
            return (MOCK_POLICIES_RESPONSE, 200)
        else:
            return ({"results": []}, 200)

    mock_rest_client.get.side_effect = side_effect

    result = await list_detections(["rules", "policies"])

    assert result["success"] is True
    assert "rules" in result
    assert "policies" in result
    assert len(result["rules"]) == 2  # From MOCK_RULES_RESPONSE
    assert len(result["policies"]) == 2  # From MOCK_POLICIES_RESPONSE
    assert result["total_all_detections"] == 4
    assert result["detection_types_queried"] == ["rules", "policies"]

    # Should have called both endpoints
    assert mock_rest_client.get.call_count == 2


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_get_detection_multiple_types_found_in_one(mock_rest_client):
    """Test getting detection by ID when found in one of multiple types."""

    def side_effect(endpoint, **kwargs):
        if "/rules/" in endpoint:
            return (MOCK_RULE, 200)
        else:
            return ({}, 404)

    mock_rest_client.get.side_effect = side_effect

    result = await get_detection("some-id", ["rules", "policies"])

    assert result["success"] is True
    assert "rule" in result
    assert "found_in_types" in result
    assert "not_found_in_types" in result
    assert result["found_in_types"] == ["rules"]
    assert result["not_found_in_types"] == ["policies"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_get_detection_multiple_types_not_found(mock_rest_client):
    """Test getting detection by ID when not found in any of multiple types."""
    mock_rest_client.get.return_value = ({}, 404)

    result = await get_detection("some-id", ["rules", "policies"])

    assert result["success"] is False
    assert (
        "No detection found with ID some-id in any of the specified types"
        in result["message"]
    )


@pytest.mark.asyncio
async def test_list_detections_empty_types():
    """Test validation when no detection types are provided."""
    result = await list_detections([])

    assert result["success"] is False
    assert "At least one detection type must be specified" in result["message"]


@pytest.mark.asyncio
async def test_get_detection_empty_types():
    """Test validation when no detection types are provided."""
    result = await get_detection("some-id", [])

    assert result["success"] is False
    assert "At least one detection type must be specified" in result["message"]


@pytest.mark.asyncio
async def test_list_detections_with_cursor_multiple_types():
    """Test that cursor pagination is not supported with multiple types."""
    result = await list_detections(["rules", "policies"], cursor="some-cursor")

    assert result["success"] is False
    assert (
        "Cursor pagination is not supported when querying multiple detection types"
        in result["message"]
    )


@pytest.mark.asyncio
async def test_list_detections_with_filtering_validation():
    """Test validation of filtering parameters in list_detections."""
    # Test invalid state
    result = await list_detections(["rules"], state="invalid")
    assert result["success"] is False
    assert "Invalid state value" in result["message"]

    # Test invalid severity
    result = await list_detections(["rules"], severity=["INVALID"])
    assert result["success"] is False
    assert "Invalid severity values" in result["message"]

    # Test invalid compliance_status
    result = await list_detections(["policies"], compliance_status="INVALID")
    assert result["success"] is False
    assert "Invalid compliance_status value" in result["message"]


@pytest.mark.asyncio
async def test_list_detections_with_detection_type_specific_params():
    """Test validation of detection-type-specific parameters."""
    # Test log_type with policies (should fail)
    result = await list_detections(["policies"], log_type=["AWS.CloudTrail"])
    assert result["success"] is False
    assert (
        "log_type parameter is only valid for 'rules' and 'simple_rules'"
        in result["message"]
    )

    # Test resource_type with rules (should fail)
    result = await list_detections(["rules"], resource_type=["AWS.S3.Bucket"])
    assert result["success"] is False
    assert "resource_type parameter is only valid for 'policies'" in result["message"]

    # Test compliance_status with rules (should fail)
    result = await list_detections(["rules"], compliance_status="PASS")
    assert result["success"] is False
    assert (
        "compliance_status parameter is only valid for 'policies'" in result["message"]
    )


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_with_default_params(mock_rest_client):
    """Test that default parameters are correctly set."""
    mock_rest_client.get.return_value = (MOCK_RULES_RESPONSE, 200)

    await list_detections(["rules"])

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    params = kwargs["params"]
    assert "severity" not in params
    assert "state" not in params
    assert "tag" not in params
    assert "log-type" not in params
    assert "created_by" not in params
    assert "last_modified_by" not in params
    assert params["limit"] == 100
    assert "name_contains" not in params


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_with_filtering_params(mock_rest_client):
    """Test that filtering parameters are properly passed to the API."""
    mock_rest_client.get.return_value = (MOCK_RULES_RESPONSE, 200)

    await list_detections(
        ["rules"],
        name_contains="test",
        state="enabled",
        severity=["HIGH", "CRITICAL"],
        tag=["AWS", "Security"],
        log_type=["AWS.CloudTrail"],
        created_by="user123",
        last_modified_by="user456",
    )

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == "/rules"
    params = kwargs["params"]
    assert params["name-contains"] == "test"
    assert params["state"] == "enabled"
    assert params["severity"] == ["HIGH", "CRITICAL"]
    assert params["tag"] == ["AWS", "Security"]
    assert params["log-type"] == ["AWS.CloudTrail"]
    assert params["created-by"] == "user123"
    assert params["last-modified-by"] == "user456"


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_policies_with_filtering(mock_rest_client):
    """Test policy-specific filtering parameters."""
    mock_rest_client.get.return_value = (MOCK_POLICIES_RESPONSE, 200)

    await list_detections(
        ["policies"], resource_type=["AWS.S3.Bucket"], compliance_status="FAIL"
    )

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == "/policies"
    params = kwargs["params"]
    assert params["resource-type"] == ["AWS.S3.Bucket"]
    assert params["compliance-status"] == "FAIL"


# Realistic Parameter Combination Tests
@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_security_analyst_workflow_high_priority_aws_rules(
    mock_rest_client,
):
    """Test realistic security analyst workflow: Find high priority AWS rules for incident response."""
    mock_rest_client.get.return_value = (MOCK_RULES_RESPONSE, 200)

    result = await list_detections(
        ["rules"],
        severity=["HIGH", "CRITICAL"],
        log_type=["AWS.CloudTrail", "AWS.VPCFlow"],
        tag=["AWS", "Authentication"],
        state="enabled",
        limit=20,
    )

    assert result["success"] is True
    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    params = kwargs["params"]
    assert params["severity"] == ["HIGH", "CRITICAL"]
    assert params["log-type"] == ["AWS.CloudTrail", "AWS.VPCFlow"]
    assert params["tag"] == ["AWS", "Authentication"]
    assert params["state"] == "enabled"
    assert params["limit"] == 20


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_security_analyst_workflow_coverage_gap_analysis(
    mock_rest_client,
):
    """Test realistic workflow: Identify coverage gaps for specific log sources."""

    # Mock responses for both rules and simple_rules
    def side_effect(endpoint, **kwargs):
        if endpoint in ["/rules", "/simple-rules"]:
            return (MOCK_RULES_RESPONSE, 200)
        else:
            return ({"results": []}, 200)

    mock_rest_client.get.side_effect = side_effect

    result = await list_detections(
        ["rules", "simple_rules"],
        log_type=["AWS.S3ServerAccess"],
        state="enabled",
        severity=["MEDIUM", "HIGH", "CRITICAL"],
        name_contains="exfiltration",
    )

    # Multiple types with name_contains should succeed
    assert result["success"] is True
    assert "rules" in result
    assert "simple_rules" in result


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_security_analyst_workflow_threat_hunting_scope(
    mock_rest_client,
):
    """Test realistic workflow: Scope threat hunting rules by creator and modification."""
    mock_rest_client.get.return_value = (MOCK_RULES_RESPONSE, 200)

    result = await list_detections(
        ["rules"],
        tag=["Threat Hunting", "Advanced Persistent Threat"],
        severity=["MEDIUM", "HIGH", "CRITICAL"],
        created_by="security-team",
        last_modified_by="threat-hunter-1",
        state="enabled",
        limit=50,
    )

    assert result["success"] is True
    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    params = kwargs["params"]
    assert params["tag"] == ["Threat Hunting", "Advanced Persistent Threat"]
    assert params["created-by"] == "security-team"
    assert params["last-modified-by"] == "threat-hunter-1"


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_security_analyst_workflow_compliance_audit(
    mock_rest_client,
):
    """Test realistic workflow: Compliance audit for cloud security policies."""
    mock_rest_client.get.return_value = (MOCK_POLICIES_RESPONSE, 200)

    result = await list_detections(
        ["policies"],
        resource_type=["AWS.S3.Bucket", "AWS.EC2.Instance", "AWS.IAM.Role"],
        severity=["HIGH", "CRITICAL"],
        compliance_status="FAIL",
        state="enabled",
        tag=["Compliance", "SOC2", "CIS"],
    )

    assert result["success"] is True
    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    params = kwargs["params"]
    assert params["resource-type"] == [
        "AWS.S3.Bucket",
        "AWS.EC2.Instance",
        "AWS.IAM.Role",
    ]
    assert params["compliance-status"] == "FAIL"
    assert params["tag"] == ["Compliance", "SOC2", "CIS"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_security_analyst_workflow_insider_threat_investigation(
    mock_rest_client,
):
    """Test realistic workflow: Investigate potential insider threat patterns."""
    mock_rest_client.get.return_value = (MOCK_RULES_RESPONSE, 200)

    result = await list_detections(
        ["rules"],
        log_type=["Okta.SystemLog", "AWS.CloudTrail", "Box.Event"],
        tag=["Insider Threat", "Data Exfiltration", "Privilege Escalation"],
        severity=["MEDIUM", "HIGH", "CRITICAL"],
        name_contains="suspicious",
        state="enabled",
    )

    assert result["success"] is True
    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    params = kwargs["params"]
    assert params["log-type"] == ["Okta.SystemLog", "AWS.CloudTrail", "Box.Event"]
    assert params["name-contains"] == "suspicious"


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_security_analyst_workflow_incident_response_triage(
    mock_rest_client,
):
    """Test realistic workflow: Rapid incident response triage for critical alerts."""
    mock_rest_client.get.return_value = (MOCK_RULES_RESPONSE, 200)

    result = await list_detections(
        ["rules"],
        severity=["CRITICAL"],
        tag=["Initial Access", "Credential Access", "Lateral Movement", "Exfiltration"],
        state="enabled",
        limit=10,  # Focus on top 10 most critical
    )

    assert result["success"] is True
    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    params = kwargs["params"]
    assert params["severity"] == ["CRITICAL"]
    assert params["limit"] == 10


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_security_analyst_workflow_log_source_coverage_review(
    mock_rest_client,
):
    """Test realistic workflow: Review detection coverage for specific log sources."""
    mock_rest_client.get.return_value = (MOCK_RULES_RESPONSE, 200)

    result = await list_detections(
        ["rules", "simple_rules"],  # This should work for coverage analysis
        log_type=["AWS.CloudTrail"],
        severity=["HIGH", "CRITICAL"],
        state="enabled",
    )

    # Should succeed with proper multiple type handling
    assert result["success"] is True or "multiple detection types" in result.get(
        "message", ""
    )


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_security_analyst_workflow_custom_rule_audit(
    mock_rest_client,
):
    """Test realistic workflow: Audit custom (non-managed) rules for quality assurance."""
    # Create custom rule mock (managed=False)
    custom_rule_response = {"results": [{**MOCK_RULE, "managed": False}], "next": None}
    mock_rest_client.get.return_value = (custom_rule_response, 200)

    result = await list_detections(
        ["rules"],
        created_by="custom-rule-author",
        severity=["MEDIUM", "HIGH", "CRITICAL"],
        state="enabled",
        tag=["Custom", "Organization Specific"],
    )

    assert result["success"] is True
    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    params = kwargs["params"]
    assert params["created-by"] == "custom-rule-author"
    assert params["tag"] == ["Custom", "Organization Specific"]


# Edge Cases and Boundary Condition Tests
@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_empty_result_set(mock_rest_client):
    """Test handling of empty result sets."""
    empty_response = {"results": [], "next": None}
    mock_rest_client.get.return_value = (empty_response, 200)

    result = await list_detections(["rules"], severity=["CRITICAL"])

    assert result["success"] is True
    assert result["rules"] == []
    assert result["total_rules"] == 0
    assert result["has_next_page"] is False


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_maximum_limit(mock_rest_client):
    """Test with maximum allowed limit value."""
    mock_rest_client.get.return_value = (MOCK_RULES_RESPONSE, 200)

    result = await list_detections(["rules"], limit=1000)

    assert result["success"] is True
    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert kwargs["params"]["limit"] == 1000


@pytest.mark.asyncio
async def test_list_detections_minimum_limit():
    """Test with minimum allowed limit value."""
    result = await list_detections(["rules"], limit=1)
    # Should not fail validation
    assert "limit" not in result.get("message", "")


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_unicode_name_contains(mock_rest_client):
    """Test handling of unicode characters in name_contains."""
    mock_rest_client.get.return_value = (MOCK_RULES_RESPONSE, 200)

    result = await list_detections(
        ["rules"],
        name_contains="测试规则",  # Chinese characters
    )

    assert result["success"] is True
    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert kwargs["params"]["name-contains"] == "测试规则"


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_special_characters_in_filters(mock_rest_client):
    """Test handling of special characters in filter parameters."""
    mock_rest_client.get.return_value = (MOCK_RULES_RESPONSE, 200)

    result = await list_detections(
        ["rules"],
        name_contains="rule@#$%^&*()",
        tag=["Tag with spaces", "Tag-with-dashes", "Tag_with_underscores"],
        created_by="user@domain.com",
    )

    assert result["success"] is True
    mock_rest_client.get.assert_called_once()


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_very_long_cursor(mock_rest_client):
    """Test handling of very long cursor tokens."""
    mock_rest_client.get.return_value = (MOCK_RULES_RESPONSE, 200)

    # Create a very long cursor token
    long_cursor = "a" * 2000

    result = await list_detections(["rules"], cursor=long_cursor)

    assert result["success"] is True
    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert kwargs["params"]["cursor"] == long_cursor


# Error Handling Edge Cases
@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_api_timeout_error(mock_rest_client):
    """Test handling of API timeout errors."""
    import asyncio

    mock_rest_client.get.side_effect = asyncio.TimeoutError("Request timed out")

    result = await list_detections(["rules"])

    assert result["success"] is False
    assert "Failed to list detection types" in result["message"]
    assert "Request timed out" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_partial_failure_multiple_types(mock_rest_client):
    """Test handling when one detection type succeeds and another fails."""

    def side_effect(endpoint, **kwargs):
        if endpoint == "/rules":
            return (MOCK_RULES_RESPONSE, 200)
        elif endpoint == "/policies":
            raise Exception("Policies API unavailable")
        else:
            return ({"results": []}, 200)

    mock_rest_client.get.side_effect = side_effect

    result = await list_detections(["rules", "policies"])

    assert result["success"] is False
    assert "Failed to list detection types" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_detections_malformed_api_response(mock_rest_client):
    """Test handling of malformed API responses."""
    # Missing 'results' key
    malformed_response = {"next": None}
    mock_rest_client.get.return_value = (malformed_response, 200)

    result = await list_detections(["rules"])

    assert result["success"] is True
    assert result["rules"] == []  # Should handle missing 'results' gracefully


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_get_detection_with_malformed_response(mock_rest_client):
    """Test get_detection with malformed API response."""
    # API returns success but with unexpected structure
    malformed_response = {"unexpected": "data"}
    mock_rest_client.get.return_value = (malformed_response, 200)

    result = await get_detection("test-rule", ["rules"])

    assert result["success"] is True
    assert result["rule"] == malformed_response


# Parameter Validation Tests
@pytest.mark.asyncio
async def test_list_detections_invalid_severity_mixed_valid_invalid():
    """Test validation with mix of valid and invalid severity values."""
    result = await list_detections(["rules"], severity=["HIGH", "INVALID", "CRITICAL"])

    assert result["success"] is False
    assert "Invalid severity values: ['INVALID']" in result["message"]


@pytest.mark.asyncio
async def test_list_detections_case_sensitive_severity_validation():
    """Test that severity validation is case-sensitive."""
    result = await list_detections(["rules"], severity=["high", "CRITICAL"])

    assert result["success"] is False
    assert "Invalid severity values: ['high']" in result["message"]


@pytest.mark.asyncio
async def test_list_detections_case_sensitive_state_validation():
    """Test that state validation is case-sensitive."""
    result = await list_detections(["rules"], state="Enabled")

    assert result["success"] is False
    assert "Invalid state value" in result["message"]


@pytest.mark.asyncio
async def test_list_detections_cross_contamination_validation():
    """Test validation prevents cross-contamination of detection-type-specific params."""
    # Try to use log_type with policies
    result = await list_detections(["policies"], log_type=["AWS.CloudTrail"])
    assert result["success"] is False
    assert (
        "log_type parameter is only valid for 'rules' and 'simple_rules'"
        in result["message"]
    )

    # Try to use resource_type with rules
    result = await list_detections(["rules"], resource_type=["AWS.S3.Bucket"])
    assert result["success"] is False
    assert "resource_type parameter is only valid for 'policies'" in result["message"]

    # Try to use compliance_status with rules
    result = await list_detections(["rules"], compliance_status="FAIL")
    assert result["success"] is False
    assert (
        "compliance_status parameter is only valid for 'policies'" in result["message"]
    )


@pytest.mark.asyncio
async def test_list_detections_mixed_types_with_restricted_params():
    """Test mixed detection types with some having restricted parameters."""
    # This should work - rules and simple_rules can use log_type
    result = await list_detections(
        ["rules", "simple_rules"], log_type=["AWS.CloudTrail"]
    )
    # Should not fail validation
    assert "log_type parameter is only valid" not in result.get("message", "")


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_get_detection_empty_detection_id(mock_rest_client):
    """Test get_detection with empty detection ID."""
    mock_rest_client.get.return_value = ({}, 404)

    result = await get_detection("", ["rules"])

    assert result["success"] is False
    mock_rest_client.get.assert_called_once()


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_disable_detection_already_disabled(mock_rest_client):
    """Test disabling a detection that's already disabled."""
    already_disabled_rule = {**MOCK_RULE, "enabled": False}
    mock_rest_client.get.return_value = (already_disabled_rule, 200)
    mock_rest_client.put.return_value = (already_disabled_rule, 200)

    result = await disable_detection(MOCK_RULE["id"], "rules")

    assert result["success"] is True
    assert result["rule"]["enabled"] is False
    # Should still make the API call
    mock_rest_client.put.assert_called_once()


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_disable_detection_concurrent_modification(mock_rest_client):
    """Test disable_detection when rule is modified between GET and PUT."""
    # GET returns original rule
    mock_rest_client.get.return_value = (MOCK_RULE, 200)
    # PUT fails due to concurrent modification (422 Unprocessable Entity)
    mock_rest_client.put.side_effect = Exception("Concurrent modification detected")

    result = await disable_detection(MOCK_RULE["id"], "rules")

    assert result["success"] is False
    assert "Failed to disable rules" in result["message"]
    assert "Concurrent modification detected" in result["message"]
