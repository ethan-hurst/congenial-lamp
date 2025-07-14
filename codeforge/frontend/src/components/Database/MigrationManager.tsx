import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  IconButton,
  Timeline,
  TimelineItem,
  TimelineSeparator,
  TimelineConnector,
  TimelineContent,
  TimelineDot,
  TimelineOppositeContent,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  CircularProgress,
  Chip,
  Card,
  CardContent,
  CardActions,
  Tooltip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Collapse,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  PlayArrow as PlayIcon,
  Upload as UploadIcon,
  History as HistoryIcon,
  Code as CodeIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Schedule as PendingIcon,
  Undo as RollbackIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  Description as FileIcon,
  Timer as TimerIcon,
} from '@mui/icons-material';
import Editor from '@monaco-editor/react';
import { api } from '../../services/api';

interface Migration {
  id: string;
  version: number;
  name: string;
  description?: string;
  status: 'pending' | 'applied' | 'failed' | 'rolled_back';
  applied_at?: string;
  applied_by?: string;
  execution_time_ms?: number;
  error_message?: string;
}

interface MigrationManagerProps {
  databaseId: string;
  currentBranch: string;
}

const Input = styled('input')({
  display: 'none',
});

export const MigrationManager: React.FC<MigrationManagerProps> = ({
  databaseId,
  currentBranch,
}) => {
  const [migrations, setMigrations] = useState<Migration[]>([]);
  const [loading, setLoading] = useState(true);
  const [applyDialogOpen, setApplyDialogOpen] = useState(false);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [selectedMigration, setSelectedMigration] = useState<Migration | null>(null);
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
  const [migrationContent, setMigrationContent] = useState('');
  const [migrationName, setMigrationName] = useState('');
  const [migrationDescription, setMigrationDescription] = useState('');
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    fetchMigrations();
  }, [databaseId, currentBranch]);

  const fetchMigrations = async () => {
    try {
      const response = await api.get(
        `/api/v1/databases/${databaseId}/migrations?branch=${currentBranch}`
      );
      setMigrations(response.data);
    } catch (error) {
      console.error('Failed to fetch migrations:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleApplyMigration = async () => {
    if (!migrationContent) {
      setFormErrors({ content: 'Migration content is required' });
      return;
    }

    setLoading(true);
    try {
      const response = await api.post(`/api/v1/databases/${databaseId}/migrations`, {
        branch: currentBranch,
        migration_file: migrationContent,
      });

      if (response.data.id) {
        await fetchMigrations();
        setApplyDialogOpen(false);
        setMigrationContent('');
        setMigrationName('');
        setMigrationDescription('');
      }
    } catch (error: any) {
      setFormErrors({ general: error.response?.data?.detail || 'Failed to apply migration' });
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (e) => {
      const content = e.target?.result as string;
      setMigrationContent(content);
      setMigrationName(file.name);
      setUploadDialogOpen(true);
    };
    reader.readAsText(file);
  };

  const handleRollback = async (version: number) => {
    if (!confirm(`Are you sure you want to rollback to version ${version}? This will undo all migrations after this version.`)) {
      return;
    }

    setLoading(true);
    try {
      await api.post(`/api/v1/databases/${databaseId}/migrations/${version}/rollback`, {
        branch: currentBranch,
        reason: 'Manual rollback from UI',
      });
      await fetchMigrations();
    } catch (error) {
      console.error('Failed to rollback migration:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleExpanded = (migrationId: string) => {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(migrationId)) {
      newExpanded.delete(migrationId);
    } else {
      newExpanded.add(migrationId);
    }
    setExpandedItems(newExpanded);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'applied':
        return <SuccessIcon color="success" />;
      case 'failed':
        return <ErrorIcon color="error" />;
      case 'pending':
        return <PendingIcon color="action" />;
      case 'rolled_back':
        return <RollbackIcon color="warning" />;
      default:
        return <PendingIcon />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'applied':
        return 'success';
      case 'failed':
        return 'error';
      case 'pending':
        return 'default';
      case 'rolled_back':
        return 'warning';
      default:
        return 'default';
    }
  };

  const defaultMigrationTemplate = `-- Migration: ${migrationName || 'new_migration'}
-- Description: ${migrationDescription || 'Add description here'}
-- Author: ${new Date().toISOString()}

-- UP Migration (apply changes)
BEGIN;

-- Add your migration SQL here
-- Example:
-- CREATE TABLE IF NOT EXISTS users (
--     id SERIAL PRIMARY KEY,
--     email VARCHAR(255) UNIQUE NOT NULL,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

COMMIT;

-- DOWN Migration (rollback changes)
-- BEGIN;
-- DROP TABLE IF EXISTS users;
-- COMMIT;
`;

  if (loading && migrations.length === 0) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h6">Migration History</Typography>
          <Typography variant="body2" color="textSecondary">
            Branch: <Chip label={currentBranch} size="small" />
          </Typography>
        </Box>
        <Box>
          <label htmlFor="migration-file-upload">
            <Input
              id="migration-file-upload"
              type="file"
              accept=".sql"
              onChange={handleFileUpload}
            />
            <Button
              variant="outlined"
              component="span"
              startIcon={<UploadIcon />}
              sx={{ mr: 1 }}
            >
              Upload SQL
            </Button>
          </label>
          <Button
            variant="contained"
            startIcon={<PlayIcon />}
            onClick={() => {
              setMigrationContent(defaultMigrationTemplate);
              setApplyDialogOpen(true);
            }}
          >
            New Migration
          </Button>
        </Box>
      </Box>

      {migrations.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <HistoryIcon sx={{ fontSize: 48, mb: 2, opacity: 0.5 }} />
          <Typography variant="h6" gutterBottom>No migrations yet</Typography>
          <Typography variant="body2" color="textSecondary" paragraph>
            Create your first migration to update the database schema
          </Typography>
          <Button
            variant="contained"
            startIcon={<PlayIcon />}
            onClick={() => {
              setMigrationContent(defaultMigrationTemplate);
              setApplyDialogOpen(true);
            }}
          >
            Create First Migration
          </Button>
        </Paper>
      ) : (
        <Timeline position="alternate">
          {migrations.map((migration, index) => (
            <TimelineItem key={migration.id}>
              <TimelineOppositeContent color="textSecondary">
                <Typography variant="caption">
                  Version {migration.version}
                </Typography>
                {migration.applied_at && (
                  <Typography variant="caption" display="block">
                    {new Date(migration.applied_at).toLocaleString()}
                  </Typography>
                )}
              </TimelineOppositeContent>
              <TimelineSeparator>
                <TimelineDot>{getStatusIcon(migration.status)}</TimelineDot>
                {index < migrations.length - 1 && <TimelineConnector />}
              </TimelineSeparator>
              <TimelineContent>
                <Card>
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="flex-start">
                      <Box flex={1}>
                        <Typography variant="subtitle2" fontWeight="bold">
                          {migration.name}
                        </Typography>
                        {migration.description && (
                          <Typography variant="body2" color="textSecondary">
                            {migration.description}
                          </Typography>
                        )}
                        <Box mt={1}>
                          <Chip
                            label={migration.status}
                            size="small"
                            color={getStatusColor(migration.status) as any}
                          />
                          {migration.execution_time_ms && (
                            <Chip
                              icon={<TimerIcon />}
                              label={`${migration.execution_time_ms}ms`}
                              size="small"
                              variant="outlined"
                              sx={{ ml: 1 }}
                            />
                          )}
                        </Box>
                      </Box>
                      <IconButton
                        size="small"
                        onClick={() => toggleExpanded(migration.id)}
                      >
                        {expandedItems.has(migration.id) ? <CollapseIcon /> : <ExpandIcon />}
                      </IconButton>
                    </Box>
                    
                    <Collapse in={expandedItems.has(migration.id)}>
                      <Box mt={2}>
                        {migration.applied_by && (
                          <Typography variant="caption" display="block">
                            Applied by: {migration.applied_by}
                          </Typography>
                        )}
                        {migration.error_message && (
                          <Alert severity="error" sx={{ mt: 1 }}>
                            {migration.error_message}
                          </Alert>
                        )}
                      </Box>
                    </Collapse>
                  </CardContent>
                  {migration.status === 'applied' && (
                    <CardActions>
                      <Button
                        size="small"
                        color="warning"
                        startIcon={<RollbackIcon />}
                        onClick={() => handleRollback(migration.version)}
                      >
                        Rollback
                      </Button>
                    </CardActions>
                  )}
                </Card>
              </TimelineContent>
            </TimelineItem>
          ))}
        </Timeline>
      )}

      {/* Apply Migration Dialog */}
      <Dialog
        open={applyDialogOpen}
        onClose={() => setApplyDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Apply New Migration</DialogTitle>
        <DialogContent>
          {formErrors.general && (
            <Alert severity="error" sx={{ mb: 2 }}>{formErrors.general}</Alert>
          )}
          
          <TextField
            fullWidth
            label="Migration Name"
            value={migrationName}
            onChange={(e) => setMigrationName(e.target.value)}
            margin="normal"
          />

          <TextField
            fullWidth
            label="Description"
            value={migrationDescription}
            onChange={(e) => setMigrationDescription(e.target.value)}
            margin="normal"
            multiline
            rows={2}
          />

          <Box mt={2}>
            <Typography variant="subtitle2" gutterBottom>
              Migration SQL
            </Typography>
            <Paper variant="outlined" sx={{ overflow: 'hidden' }}>
              <Editor
                height="400px"
                language="sql"
                value={migrationContent}
                onChange={(value) => setMigrationContent(value || '')}
                theme="vs-light"
                options={{
                  minimap: { enabled: false },
                  fontSize: 14,
                  lineNumbers: 'on',
                  scrollBeyondLastLine: false,
                  automaticLayout: true,
                }}
              />
            </Paper>
            {formErrors.content && (
              <Typography variant="caption" color="error" sx={{ mt: 1 }}>
                {formErrors.content}
              </Typography>
            )}
          </Box>

          <Alert severity="info" sx={{ mt: 2 }}>
            Migrations are applied within a transaction. If any part fails, all changes will be rolled back.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setApplyDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleApplyMigration}
            variant="contained"
            disabled={loading}
            startIcon={loading ? <CircularProgress size={20} /> : <PlayIcon />}
          >
            Apply Migration
          </Button>
        </DialogActions>
      </Dialog>

      {/* Upload Migration Dialog */}
      <Dialog
        open={uploadDialogOpen}
        onClose={() => setUploadDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Upload Migration File</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Migration Name"
            value={migrationName}
            onChange={(e) => setMigrationName(e.target.value)}
            margin="normal"
          />

          <TextField
            fullWidth
            label="Description"
            value={migrationDescription}
            onChange={(e) => setMigrationDescription(e.target.value)}
            margin="normal"
            multiline
            rows={2}
          />

          <Box mt={2}>
            <Typography variant="subtitle2" gutterBottom>
              Migration Content Preview
            </Typography>
            <Paper variant="outlined" sx={{ p: 2, bgcolor: '#f5f5f5', maxHeight: 300, overflow: 'auto' }}>
              <pre style={{ margin: 0, fontSize: '0.875rem' }}>{migrationContent}</pre>
            </Paper>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUploadDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={() => {
              setUploadDialogOpen(false);
              setApplyDialogOpen(true);
            }}
            variant="contained"
          >
            Continue to Apply
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};