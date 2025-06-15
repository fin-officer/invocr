# scripts/init-db.sql
-- Database initialization script for InvOCR

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create database user if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'invocr') THEN
        CREATE ROLE invocr WITH LOGIN PASSWORD 'invocr_password';
    END IF;
END
$$;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE invocr TO invocr;
GRANT ALL ON SCHEMA public TO invocr;

-- Create tables
CREATE TABLE IF NOT EXISTS conversion_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    input_format VARCHAR(10) NOT NULL,
    output_format VARCHAR(10) NOT NULL,
    file_name VARCHAR(255),
    file_size BIGINT,
    languages TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    metadata JSONB,
    result_path VARCHAR(500)
);

CREATE TABLE IF NOT EXISTS ocr_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES conversion_jobs(id) ON DELETE CASCADE,
    text_content TEXT,
    confidence DECIMAL(3,2),
    language VARCHAR(10),
    engine VARCHAR(20),
    processing_time DECIMAL(10,3),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversion_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES conversion_jobs(id) ON DELETE CASCADE,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15,6),
    metric_unit VARCHAR(20),
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS api_usage_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER NOT NULL,
    response_time DECIMAL(10,3),
    user_agent TEXT,
    ip_address INET,
    request_size BIGINT,
    response_size BIGINT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_conversion_jobs_job_id ON conversion_jobs(job_id);
CREATE INDEX IF NOT EXISTS idx_conversion_jobs_status ON conversion_jobs(status);
CREATE INDEX IF NOT EXISTS idx_conversion_jobs_created_at ON conversion_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_ocr_results_job_id ON ocr_results(job_id);
CREATE INDEX IF NOT EXISTS idx_conversion_metrics_job_id ON conversion_metrics(job_id);
CREATE INDEX IF NOT EXISTS idx_api_usage_stats_endpoint ON api_usage_stats(endpoint);
CREATE INDEX IF NOT EXISTS idx_api_usage_stats_timestamp ON api_usage_stats(timestamp);

-- Create views for analytics
CREATE OR REPLACE VIEW conversion_summary AS
SELECT
    DATE_TRUNC('day', created_at) as date,
    input_format,
    output_format,
    status,
    COUNT(*) as job_count,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_processing_time,
    AVG(file_size) as avg_file_size
FROM conversion_jobs
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', created_at), input_format, output_format, status
ORDER BY date DESC;

CREATE OR REPLACE VIEW ocr_performance AS
SELECT
    DATE_TRUNC('hour', created_at) as hour,
    engine,
    language,
    COUNT(*) as ocr_count,
    AVG(confidence) as avg_confidence,
    AVG(processing_time) as avg_processing_time
FROM ocr_results
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE_TRUNC('hour', created_at), engine, language
ORDER BY hour DESC;

CREATE OR REPLACE VIEW api_performance AS
SELECT
    DATE_TRUNC('hour', timestamp) as hour,
    endpoint,
    COUNT(*) as request_count,
    AVG(response_time) as avg_response_time,
    COUNT(CASE WHEN status_code >= 400 THEN 1 END) as error_count,
    COUNT(CASE WHEN status_code < 400 THEN 1 END) as success_count
FROM api_usage_stats
WHERE timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', timestamp), endpoint
ORDER BY hour DESC;

-- Create function for cleanup old records
CREATE OR REPLACE FUNCTION cleanup_old_records()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER := 0;
BEGIN
    -- Delete conversion jobs older than 30 days
    DELETE FROM conversion_jobs
    WHERE created_at < NOW() - INTERVAL '30 days'
    AND status IN ('completed', 'failed');

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    -- Delete API usage stats older than 7 days
    DELETE FROM api_usage_stats
    WHERE timestamp < NOW() - INTERVAL '7 days';

    -- Vacuum to reclaim space
    VACUUM ANALYZE conversion_jobs;
    VACUUM ANALYZE api_usage_stats;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create scheduled cleanup (requires pg_cron extension)
-- SELECT cron.schedule('cleanup-invocr', '0 2 * * *', 'SELECT cleanup_old_records();');

-- Insert sample data for testing
INSERT INTO conversion_jobs (job_id, status, input_format, output_format, file_name, file_size, created_at, completed_at)
VALUES
    ('test-job-1', 'completed', 'pdf', 'json', 'sample_invoice.pdf', 1024000, NOW() - INTERVAL '1 hour', NOW() - INTERVAL '50 minutes'),
    ('test-job-2', 'completed', 'jpg', 'json', 'receipt.jpg', 512000, NOW() - INTERVAL '2 hours', NOW() - INTERVAL '1 hour 55 minutes'),
    ('test-job-3', 'failed', 'pdf', 'xml', 'corrupted.pdf', 2048000, NOW() - INTERVAL '3 hours', NOW() - INTERVAL '2 hours 30 minutes');

-- Grant permissions to tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO invocr;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO invocr;

COMMIT;