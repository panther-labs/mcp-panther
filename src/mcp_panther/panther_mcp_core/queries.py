from gql import gql

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
query GetDataLakeQuery($id: ID!, $root: Boolean = false, $resultsInput: DataLakeQueryResultsInput) {
    dataLakeQuery(id: $id, root: $root) {
        id
        status
        message
        sql
        startedAt
        completedAt
        results(input: $resultsInput) {
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

LIST_DATABASES_QUERY = gql("""
query ListDatabases {
    dataLakeDatabases {
        name
        description
    }
}
""")

LIST_TABLES_QUERY = gql("""
query ListTables($databaseName: String!, $pageSize: Int, $cursor: String) {
  dataLakeDatabaseTables(
    input: {
      databaseName: $databaseName
      pageSize: $pageSize
      cursor: $cursor
    }
  ) {
    edges {
      node {
        name
        description
        logType
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
""")

GET_COLUMNS_FOR_TABLE_QUERY = gql("""
query GetColumnDetails($databaseName: String!, $tableName: String!) {
  dataLakeDatabaseTable(input: { databaseName: $databaseName, tableName: $tableName }) {
    name,
    displayName,
    description,
    logType,
    columns {
      name,
      type,
      description
    }
  }
}
""")

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

METRICS_BYTES_PROCESSED_QUERY = gql("""
query GetBytesProcessedMetrics($input: MetricsInput!) {
    metrics(input: $input) {
        bytesProcessedPerSource {
            label
            value
            breakdown
        }
    }
}
""")

GET_SCHEMA_DETAILS_QUERY = gql("""
query GetSchemaDetails($name: String!) {
    schemas(input: { contains: $name }) {
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

# Data Lake Query Management
LIST_DATA_LAKE_QUERIES = gql("""
query ListDataLakeQueries($input: DataLakeQueriesInput) {
    dataLakeQueries(input: $input) {
        edges {
            node {
                id
                sql
                name
                status
                message
                startedAt
                completedAt
                isScheduled
                issuedBy {
                    ... on User {
                        id
                        email
                        givenName
                        familyName
                    }
                    ... on APIToken {
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

CANCEL_DATA_LAKE_QUERY = gql("""
mutation CancelDataLakeQuery($input: CancelDataLakeQueryInput!) {
    cancelDataLakeQuery(input: $input) {
        id
    }
}
""")

# AI Inference Queries
AI_SUMMARIZE_ALERT_MUTATION = gql("""
mutation AISummarizeAlert($input: AISummarizeAlertInput!) {
    aiSummarizeAlert(input: $input) {
        streamId
    }
}
""")

AI_INFERENCE_STREAM_QUERY = gql("""
query AIInferenceStream($streamId: String!) {
    aiInferenceStream(streamId: $streamId) {
        error
        finished
        responseText
        streamId
    }
}
""")

AI_INFERENCE_STREAMS_METADATA_QUERY = gql("""
query AIInferenceStreamsMetadata($input: AIInferenceStreamsMetadataInput!) {
    aiInferenceStreamsMetadata(input: $input) {
        edges {
            node {
                streamId
            }
        }
    }
}
""")
