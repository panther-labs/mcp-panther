import pytest

from mcp_panther.panther_mcp_core.tools.rules import (
    disable_rule,
    get_policy_by_id,
    get_rule_by_id,
    get_scheduled_rule_by_id,
    get_simple_rule_by_id,
    list_policies,
    list_rules,
    list_scheduled_rules,
    list_simple_rules,
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
    "runbook": "",
    "severity": "MEDIUM",
    "threshold": 1,
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
}

MOCK_RULES_RESPONSE = {
    "results": [MOCK_RULE, MOCK_RULE_HIGH_SEVERITY],
    "next": "next-page-token",
}

RULES_MODULE_PATH = "mcp_panther.panther_mcp_core.tools.rules"


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_rules_success(mock_rest_client):
    """Test successful listing of rules."""
    mock_rest_client.get.return_value = (MOCK_RULES_RESPONSE, 200)

    result = await list_rules()

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


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_rules_with_pagination(mock_rest_client):
    """Test listing rules with pagination."""
    mock_rest_client.get.return_value = (MOCK_RULES_RESPONSE, 200)

    await list_rules(cursor="some-cursor", limit=50)

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == "/rules"
    assert kwargs["params"]["cursor"] == "some-cursor"
    assert kwargs["params"]["limit"] == 50


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_rules_error(mock_rest_client):
    """Test handling of errors when listing rules."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await list_rules()

    assert result["success"] is False
    assert "Failed" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_get_rule_by_id_success(mock_rest_client):
    """Test successful retrieval of a single rule."""
    mock_rest_client.get.return_value = (MOCK_RULE, 200)

    result = await get_rule_by_id(MOCK_RULE["id"])

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
async def test_get_rule_by_id_not_found(mock_rest_client):
    """Test handling of non-existent rule."""
    mock_rest_client.get.return_value = ({}, 404)

    result = await get_rule_by_id("nonexistent-rule")

    assert result["success"] is False
    assert "No rule found with ID" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_get_rule_by_id_error(mock_rest_client):
    """Test handling of errors when getting rule by ID."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await get_rule_by_id(MOCK_RULE["id"])

    assert result["success"] is False
    assert "Failed" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_disable_rule_success(mock_rest_client):
    """Test successful disabling of a rule."""
    # For the disable_rule test, we need two responses:
    # 1. GET to fetch current rule data
    # 2. PUT to update with enabled=False
    mock_rest_client.get.return_value = (MOCK_RULE, 200)
    disabled_rule = {**MOCK_RULE, "enabled": False}
    mock_rest_client.put.return_value = (disabled_rule, 200)

    result = await disable_rule(MOCK_RULE["id"])

    assert result["success"] is True
    assert result["rule"]["enabled"] is False

    mock_rest_client.put.assert_called_once()
    args, kwargs = mock_rest_client.put.call_args
    assert args[0] == f"/rules/{MOCK_RULE['id']}"
    assert kwargs["json_data"]["enabled"] is False
    assert kwargs["params"]["run-tests-first"] == "false"


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_disable_rule_not_found(mock_rest_client):
    """Test disabling a non-existent rule."""
    mock_rest_client.get.return_value = ({}, 404)

    result = await disable_rule("nonexistent-rule")

    assert result["success"] is False
    assert "Rule with ID nonexistent-rule not found" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_disable_rule_error(mock_rest_client):
    """Test handling of errors when disabling a rule."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await disable_rule(MOCK_RULE["id"])

    assert result["success"] is False
    assert "Failed" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_scheduled_rules_success(mock_rest_client):
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

    result = await list_scheduled_rules()

    assert result["success"] is True
    assert len(result["scheduled_rules"]) == 2
    assert result["total_scheduled_rules"] == 2
    assert result["has_next_page"] is True

    mock_rest_client.get.assert_called_once()
    args, _ = mock_rest_client.get.call_args
    assert args[0] == "/scheduled-rules"


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_scheduled_rules_error(mock_rest_client):
    """Test handling of errors when listing scheduled rules."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await list_scheduled_rules()

    assert result["success"] is False
    assert "Failed" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_scheduled_rules_with_pagination(mock_rest_client):
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

    await list_scheduled_rules(cursor="some-cursor", limit=25)

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == "/scheduled-rules"
    assert kwargs["params"]["cursor"] == "some-cursor"
    assert kwargs["params"]["limit"] == 25


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_get_scheduled_rule_by_id_success(mock_rest_client):
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

    result = await get_scheduled_rule_by_id(scheduled_rule["id"])

    assert result["success"] is True
    assert result["scheduled_rule"]["id"] == scheduled_rule["id"]
    assert "scheduledQueries" in result["scheduled_rule"]
    assert len(result["scheduled_rule"]["scheduledQueries"]) == 1


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_get_scheduled_rule_by_id_not_found(mock_rest_client):
    """Test handling of non-existent scheduled rule."""
    mock_rest_client.get.return_value = ({}, 404)

    result = await get_scheduled_rule_by_id("nonexistent.scheduled.rule")

    assert result["success"] is False
    assert "No scheduled rule found with ID" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_get_scheduled_rule_by_id_error(mock_rest_client):
    """Test handling of errors when getting scheduled rule by ID."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await get_scheduled_rule_by_id("scheduled.rule.id")

    assert result["success"] is False
    assert "Failed" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_simple_rules_success(mock_rest_client):
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

    result = await list_simple_rules()

    assert result["success"] is True
    assert len(result["simple_rules"]) == 2
    assert result["total_simple_rules"] == 2
    assert result["has_next_page"] is True

    mock_rest_client.get.assert_called_once()
    args, _ = mock_rest_client.get.call_args
    assert args[0] == "/simple-rules"


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_simple_rules_with_pagination(mock_rest_client):
    """Test pagination for listing simple rules."""
    simple_rules_response = {
        "results": [{"id": "simple.test.rule", "displayName": "Test Simple Rule"}],
        "next": "next-simple-token",
    }
    mock_rest_client.get.return_value = (simple_rules_response, 200)

    await list_simple_rules(cursor="simple-cursor", limit=30)

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == "/simple-rules"
    assert kwargs["params"]["cursor"] == "simple-cursor"
    assert kwargs["params"]["limit"] == 30


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_simple_rules_error(mock_rest_client):
    """Test handling of errors when listing simple rules."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await list_simple_rules()

    assert result["success"] is False
    assert "Failed" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_get_simple_rule_by_id_success(mock_rest_client):
    """Test successful retrieval of a single simple rule."""
    simple_rule = {
        **MOCK_RULE,
        "id": "simple.ip.blocklist",
        "displayName": "Simple IP Blocklist Rule",
        "description": "Alerts on traffic from known malicious IPs",
    }
    mock_rest_client.get.return_value = (simple_rule, 200)

    result = await get_simple_rule_by_id(simple_rule["id"])

    assert result["success"] is True
    assert result["simple_rule"]["id"] == simple_rule["id"]
    assert result["simple_rule"]["displayName"] == simple_rule["displayName"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_get_simple_rule_by_id_not_found(mock_rest_client):
    """Test handling of non-existent simple rule."""
    mock_rest_client.get.return_value = ({}, 404)

    result = await get_simple_rule_by_id("nonexistent.simple.rule")

    assert result["success"] is False
    assert "No simple rule found with ID" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_get_simple_rule_by_id_error(mock_rest_client):
    """Test handling of errors when getting simple rule by ID."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await get_simple_rule_by_id("simple.rule.id")

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
async def test_list_policies_success(mock_rest_client):
    """Test successful listing of policies."""
    mock_rest_client.get.return_value = (MOCK_POLICIES_RESPONSE, 200)

    result = await list_policies()

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

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == "/policies"


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_policies_with_pagination(mock_rest_client):
    """Test listing policies with pagination."""
    mock_rest_client.get.return_value = (MOCK_POLICIES_RESPONSE, 200)

    await list_policies(cursor="some-policy-cursor", limit=50)

    mock_rest_client.get.assert_called_once()
    args, kwargs = mock_rest_client.get.call_args
    assert args[0] == "/policies"
    assert kwargs["params"]["cursor"] == "some-policy-cursor"
    assert kwargs["params"]["limit"] == 50


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_list_policies_error(mock_rest_client):
    """Test handling of errors when listing policies."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await list_policies()

    assert result["success"] is False
    assert "Failed to fetch policies" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_get_policy_by_id_success(mock_rest_client):
    """Test successful retrieval of a single policy."""
    mock_rest_client.get.return_value = (MOCK_POLICY, 200)

    result = await get_policy_by_id(MOCK_POLICY["id"])

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
async def test_get_policy_by_id_not_found(mock_rest_client):
    """Test handling of non-existent policy."""
    mock_rest_client.get.return_value = ({}, 404)

    result = await get_policy_by_id("nonexistent-policy")

    assert result["success"] is False
    assert "No policy found with ID" in result["message"]


@pytest.mark.asyncio
@patch_rest_client(RULES_MODULE_PATH)
async def test_get_policy_by_id_error(mock_rest_client):
    """Test handling of errors when getting policy by ID."""
    mock_rest_client.get.side_effect = Exception("Test error")

    result = await get_policy_by_id(MOCK_POLICY["id"])

    assert result["success"] is False
    assert "Failed to fetch policy details" in result["message"]
