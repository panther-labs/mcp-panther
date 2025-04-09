from gql import gql

# Alert Queries
GET_TODAYS_ALERTS_QUERY = gql("""
query FirstPageOfAllAlerts($input: AlertsInput!) {
    alerts(input: $input) {
        edges {
            node {
                id
                title
                severity
                status
                createdAt
                type
                description
                reference
                runbook
                firstEventOccurredAt
                lastReceivedEventAt
                origin {
                    ... on Detection {
                        id
                        name
                    }
                }
            }
        }
        pageInfo {
            hasNextPage
            endCursor
            hasPreviousPage
            startCursor
        }
    }
}
""")

GET_ALERT_BY_ID_QUERY = gql("""
query GetAlertById($id: ID!) {
    alert(id: $id) {
        id
        title
        severity
        status
        createdAt
        type
        description
        reference
        runbook
        firstEventOccurredAt
        lastReceivedEventAt
        updatedAt
        origin {
            ... on Detection {
                id
                name
            }
        }
    }
}
""")

UPDATE_ALERT_STATUS_MUTATION = gql("""
mutation UpdateAlertStatusById($input: UpdateAlertStatusByIdInput!) {
    updateAlertStatusById(input: $input) {
        alerts {
            id
            status
            updatedAt
        }
    }
}
""")

ADD_ALERT_COMMENT_MUTATION = gql("""
mutation CreateAlertComment($input: CreateAlertCommentInput!) {
    createAlertComment(input: $input) {
        comment {
            id
            body
            createdAt
            createdBy {
                ... on User {
                    id
                    email
                    givenName
                    familyName
                }
            }
            format
        }
    }
}
""")

UPDATE_ALERTS_ASSIGNEE_BY_ID_MUTATION = gql("""
mutation UpdateAlertsAssigneeById($input: UpdateAlertsAssigneeByIdInput!) {
    updateAlertsAssigneeById(input: $input) {
        alerts {
            id
            assignee {
                id
                email
                givenName
                familyName
            }
        }
    }
}
""")

# Source Queries
GET_SOURCES_QUERY = gql("""
query Sources($input: SourcesInput) {
    sources(input: $input) {
        edges {
            node {
                integrationId
                integrationLabel
                integrationType
                isEditable
                isHealthy
                lastEventProcessedAtTime
                lastEventReceivedAtTime
                lastModified
                logTypes
                ... on S3LogIntegration {
                    awsAccountId
                    kmsKey
                    logProcessingRole
                    logStreamType
                    logStreamTypeOptions {
                        jsonArrayEnvelopeField
                    }
                    managedBucketNotifications
                    s3Bucket
                    s3Prefix
                    s3PrefixLogTypes {
                        prefix
                        logTypes
                        excludedPrefixes
                    }
                    stackName
                }
            }
        }
        pageInfo {
            hasNextPage
            hasPreviousPage
            startCursor
            endCursor
        }
    }
}
""")

# Data Lake Queries
EXECUTE_DATA_LAKE_QUERY = gql("""
mutation ExecuteDataLakeQuery($input: ExecuteDataLakeQueryInput!) {
    executeDataLakeQuery(input: $input) {
        id
    }
}
""")

GET_DATA_LAKE_QUERY = gql("""
query GetDataLakeQuery($id: ID!, $root: Boolean = false) {
    dataLakeQuery(id: $id, root: $root) {
        id
        status
        message
        sql
        startedAt
        completedAt
        results(input: { pageSize: 999 }) {
            edges {
                node
            }
            pageInfo {
                hasNextPage
                endCursor
            }
            columnInfo {
                order
                types
            }
            stats {
                bytesScanned
                executionTime
                rowCount
            }
        }
    }
}
""")

ALL_DATABASE_ENTITIES_QUERY = gql("""
query AllDatabaseEntities {
  dataLakeDatabases {
    name
    description
    tables {
      name
      description
      columns {
        name
        description
        type
      }
    }
  }
}
""")

LIST_DATABASES_QUERY = gql("""
query {
    dataLakeDatabases {
        name
        description
    }
}
""")

LIST_TABLES_FOR_DATABASE_QUERY = gql("""
query DatabaseTables($name: String!) {
    dataLakeDatabase(name: $name) {
        name
        description
        tables {
            name
            description
        }
    }
}
""")

# Add after ALL_DATABASE_ENTITIES_QUERY

LIST_SCHEMAS_QUERY = gql("""
query ListSchemas($input: SchemasInput!) {
    schemas(input: $input) {
        edges {
            node {
                name
                description
                revision
                isArchived
                isManaged
                referenceURL
                createdAt
                updatedAt
            }
        }
    }
}
""")

CREATE_OR_UPDATE_SCHEMA_MUTATION = gql("""
mutation CreateOrUpdateSchema($input: CreateOrUpdateSchemaInput!) {
    createOrUpdateSchema(input: $input) {
        schema {
            name
            description
            spec
            version
            revision
            isArchived
            isManaged
            isFieldDiscoveryEnabled
            referenceURL
            discoveredSpec
            createdAt
            updatedAt
        }
    }
}
""")

# User Queries
LIST_USERS_QUERY = gql("""
query ListUsers {
    users {
        id
        email
        givenName
        familyName
        createdAt
        lastLoggedInAt
        status
        enabled
        role {
            id
            name
            permissions
        }
    }
}
""")

# Metrics Queries
METRICS_ALERTS_PER_SEVERITY_QUERY = gql("""
query Metrics($input: MetricsInput!) {
    metrics(input: $input) {
        alertsPerSeverity {
            label
            value
            breakdown
        }
        totalAlerts
    }
}
""")

METRICS_ALERTS_PER_RULE_QUERY = gql("""
query Metrics($input: MetricsInput!) {
    metrics(input: $input) {
        alertsPerRule {
            entityId
            label
            value
        }
        totalAlerts
    }
}
""")

GET_SCHEMA_DETAILS_QUERY = gql("""
query GetSchemaDetails($name: String!) {
    schemas(input: { name: $name }) {
        edges {
            node {
                name
                description
                spec
                version
                revision
                isArchived
                isManaged
                isFieldDiscoveryEnabled
                referenceURL
                discoveredSpec
                createdAt
                updatedAt
            }
        }
    }
}
""")
