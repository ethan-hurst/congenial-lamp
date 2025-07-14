import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  IconButton,
  Chip,
  Alert,
  CircularProgress,
  Tooltip,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  LinearProgress,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  FileCopy as CopyIcon,
  Settings as SettingsIcon,
  CloudQueue as CloudIcon,
  Storage as StorageIcon,
  Speed as SpeedIcon,
  Memory as MemoryIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { api } from '../../services/api';
import { useProjectStore } from '../../stores/projectStore';

interface DatabaseInstance {
  id: string;
  project_id: string;
  name: string;
  db_type: 'postgresql' | 'mysql';
  version: string;
  size: 'micro' | 'small' | 'medium' | 'large';
  region: string;
  status: 'provisioning' | 'ready' | 'error' | 'deleting';
  host?: string;
  port?: number;
  database_name: string;
  username: string;
  connection_string?: string;
  created_at: string;
  backup_enabled: boolean;
  backup_schedule?: string;
}

interface DatabaseMetrics {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  connections: number;
  queries_per_second: number;
}

interface DatabaseManagerProps {
  projectId: string;
  onDatabaseCreated?: (db: DatabaseInstance) => void;
}

const sizeConfig = {
  micro: { cpu: 0.5, memory: 0.5, storage: 10, price: 0.01 },
  small: { cpu: 1, memory: 1, storage: 20, price: 0.05 },
  medium: { cpu: 2, memory: 4, storage: 50, price: 0.20 },
  large: { cpu: 4, memory: 8, storage: 100, price: 0.80 },
};

export const DatabaseManager: React.FC<DatabaseManagerProps> = ({
  projectId,
  onDatabaseCreated,
}) => {
  const [databases, setDatabases] = useState<DatabaseInstance[]>([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [selectedDb, setSelectedDb] = useState<DatabaseInstance | null>(null);
  const [metrics, setMetrics] = useState<Record<string, DatabaseMetrics>>({});
  const [connectionStrings, setConnectionStrings] = useState<Record<string, string>>({});
  const [showConnectionString, setShowConnectionString] = useState<Record<string, boolean>>({});

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    type: 'postgresql' as const,
    version: '15',
    size: 'small' as const,
    region: 'us-east-1',
  });

  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    fetchDatabases();
    const interval = setInterval(fetchDatabases, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, [projectId]);

  const fetchDatabases = async () => {
    try {
      const response = await api.get(`/api/v1/databases?project_id=${projectId}`);
      setDatabases(response.data);
      
      // Fetch metrics for ready databases
      response.data.forEach((db: DatabaseInstance) => {
        if (db.status === 'ready') {
          fetchMetrics(db.id);
        }
      });
    } catch (error) {
      console.error('Failed to fetch databases:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchMetrics = async (instanceId: string) => {
    try {
      const response = await api.get(`/api/v1/databases/${instanceId}/metrics`);
      setMetrics(prev => ({ ...prev, [instanceId]: response.data }));
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
    }
  };

  const handleCreateDatabase = async () => {
    const errors: Record<string, string> = {};
    if (!formData.name) errors.name = 'Name is required';
    if (formData.name.length > 100) errors.name = 'Name must be less than 100 characters';
    
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }

    try {
      const response = await api.post(`/api/v1/databases?project_id=${projectId}`, formData);
      const newDatabase = response.data;
      setDatabases([...databases, newDatabase]);
      setCreateDialogOpen(false);
      setFormData({
        name: '',
        type: 'postgresql',
        version: '15',
        size: 'small',
        region: 'us-east-1',
      });
      
      if (onDatabaseCreated) {
        onDatabaseCreated(newDatabase);
      }
    } catch (error: any) {
      setFormErrors({ general: error.response?.data?.detail || 'Failed to create database' });
    }
  };

  const handleDeleteDatabase = async (instanceId: string) => {
    if (!confirm('Are you sure you want to delete this database? This action cannot be undone.')) {
      return;
    }

    try {
      await api.delete(`/api/v1/databases/${instanceId}`);
      setDatabases(databases.filter(db => db.id !== instanceId));
    } catch (error) {
      console.error('Failed to delete database:', error);
    }
  };

  const fetchConnectionString = async (instanceId: string) => {
    try {
      const response = await api.get(`/api/v1/databases/${instanceId}/connection-string`);
      setConnectionStrings(prev => ({ ...prev, [instanceId]: response.data.connection_string }));
      setShowConnectionString(prev => ({ ...prev, [instanceId]: true }));
    } catch (error) {
      console.error('Failed to fetch connection string:', error);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ready': return 'success';
      case 'provisioning': return 'info';
      case 'error': return 'error';
      case 'deleting': return 'warning';
      default: return 'default';
    }
  };

  const renderMetrics = (dbId: string) => {
    const dbMetrics = metrics[dbId];
    if (!dbMetrics) return null;

    return (
      <Grid container spacing={2} sx={{ mt: 1 }}>
        <Grid item xs={6} sm={3}>
          <Box display="flex" alignItems="center">
            <SpeedIcon fontSize="small" sx={{ mr: 1 }} />
            <Box>
              <Typography variant="caption" color="textSecondary">CPU</Typography>
              <Typography variant="body2">{dbMetrics.cpu_usage}%</Typography>
            </Box>
          </Box>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Box display="flex" alignItems="center">
            <MemoryIcon fontSize="small" sx={{ mr: 1 }} />
            <Box>
              <Typography variant="caption" color="textSecondary">Memory</Typography>
              <Typography variant="body2">{dbMetrics.memory_usage}%</Typography>
            </Box>
          </Box>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Box display="flex" alignItems="center">
            <StorageIcon fontSize="small" sx={{ mr: 1 }} />
            <Box>
              <Typography variant="caption" color="textSecondary">Disk</Typography>
              <Typography variant="body2">{dbMetrics.disk_usage}%</Typography>
            </Box>
          </Box>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Box display="flex" alignItems="center">
            <CloudIcon fontSize="small" sx={{ mr: 1 }} />
            <Box>
              <Typography variant="caption" color="textSecondary">QPS</Typography>
              <Typography variant="body2">{dbMetrics.queries_per_second}</Typography>
            </Box>
          </Box>
        </Grid>
      </Grid>
    );
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5">Database Management</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateDialogOpen(true)}
        >
          Create Database
        </Button>
      </Box>

      {databases.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <StorageIcon sx={{ fontSize: 48, mb: 2, opacity: 0.5 }} />
          <Typography variant="h6" gutterBottom>No databases yet</Typography>
          <Typography variant="body2" color="textSecondary" paragraph>
            Create your first database to start building your application
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
          >
            Create Database
          </Button>
        </Paper>
      ) : (
        <Grid container spacing={3}>
          {databases.map((db) => (
            <Grid item xs={12} key={db.id}>
              <Card>
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="flex-start">
                    <Box flex={1}>
                      <Box display="flex" alignItems="center" mb={1}>
                        <Typography variant="h6">{db.name}</Typography>
                        <Chip
                          label={db.status}
                          color={getStatusColor(db.status) as any}
                          size="small"
                          sx={{ ml: 2 }}
                        />
                        {db.backup_enabled && (
                          <Chip
                            label="Backup Enabled"
                            color="primary"
                            size="small"
                            variant="outlined"
                            sx={{ ml: 1 }}
                          />
                        )}
                      </Box>
                      
                      <Grid container spacing={2}>
                        <Grid item xs={12} sm={6} md={3}>
                          <Typography variant="caption" color="textSecondary">Type</Typography>
                          <Typography variant="body2">{db.db_type} v{db.version}</Typography>
                        </Grid>
                        <Grid item xs={12} sm={6} md={3}>
                          <Typography variant="caption" color="textSecondary">Size</Typography>
                          <Typography variant="body2">
                            {db.size} (${sizeConfig[db.size].price}/hr)
                          </Typography>
                        </Grid>
                        <Grid item xs={12} sm={6} md={3}>
                          <Typography variant="caption" color="textSecondary">Region</Typography>
                          <Typography variant="body2">{db.region}</Typography>
                        </Grid>
                        <Grid item xs={12} sm={6} md={3}>
                          <Typography variant="caption" color="textSecondary">Created</Typography>
                          <Typography variant="body2">
                            {new Date(db.created_at).toLocaleDateString()}
                          </Typography>
                        </Grid>
                      </Grid>

                      {db.status === 'ready' && (
                        <>
                          <Box mt={2}>
                            {!showConnectionString[db.id] ? (
                              <Button
                                size="small"
                                onClick={() => fetchConnectionString(db.id)}
                              >
                                Show Connection String
                              </Button>
                            ) : (
                              <Box>
                                <Typography variant="caption" color="textSecondary">
                                  Connection String
                                </Typography>
                                <Paper variant="outlined" sx={{ p: 1, mt: 0.5 }}>
                                  <Box display="flex" alignItems="center">
                                    <Typography
                                      variant="body2"
                                      sx={{
                                        fontFamily: 'monospace',
                                        flex: 1,
                                        overflow: 'hidden',
                                        textOverflow: 'ellipsis',
                                      }}
                                    >
                                      {connectionStrings[db.id] || 'Loading...'}
                                    </Typography>
                                    <IconButton
                                      size="small"
                                      onClick={() => copyToClipboard(connectionStrings[db.id])}
                                    >
                                      <CopyIcon fontSize="small" />
                                    </IconButton>
                                  </Box>
                                </Paper>
                              </Box>
                            )}
                          </Box>

                          {renderMetrics(db.id)}
                        </>
                      )}

                      {db.status === 'provisioning' && (
                        <Box mt={2}>
                          <LinearProgress />
                          <Typography variant="caption" color="textSecondary" sx={{ mt: 1 }}>
                            Provisioning database... This may take a few minutes.
                          </Typography>
                        </Box>
                      )}
                    </Box>

                    <Box>
                      <IconButton
                        onClick={() => fetchDatabases()}
                        disabled={db.status === 'provisioning'}
                      >
                        <RefreshIcon />
                      </IconButton>
                      <IconButton
                        onClick={() => handleDeleteDatabase(db.id)}
                        disabled={db.status !== 'ready' && db.status !== 'error'}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Create Database Dialog */}
      <Dialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Create New Database</DialogTitle>
        <DialogContent>
          {formErrors.general && (
            <Alert severity="error" sx={{ mb: 2 }}>{formErrors.general}</Alert>
          )}
          
          <TextField
            fullWidth
            label="Database Name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            error={!!formErrors.name}
            helperText={formErrors.name}
            margin="normal"
          />

          <FormControl fullWidth margin="normal">
            <InputLabel>Database Type</InputLabel>
            <Select
              value={formData.type}
              onChange={(e) => setFormData({ ...formData, type: e.target.value as any })}
              label="Database Type"
            >
              <MenuItem value="postgresql">PostgreSQL</MenuItem>
              <MenuItem value="mysql">MySQL</MenuItem>
            </Select>
          </FormControl>

          <FormControl fullWidth margin="normal">
            <InputLabel>Version</InputLabel>
            <Select
              value={formData.version}
              onChange={(e) => setFormData({ ...formData, version: e.target.value })}
              label="Version"
            >
              {formData.type === 'postgresql' ? (
                <>
                  <MenuItem value="15">15</MenuItem>
                  <MenuItem value="14">14</MenuItem>
                  <MenuItem value="13">13</MenuItem>
                </>
              ) : (
                <>
                  <MenuItem value="8.0">8.0</MenuItem>
                  <MenuItem value="5.7">5.7</MenuItem>
                </>
              )}
            </Select>
          </FormControl>

          <FormControl fullWidth margin="normal">
            <InputLabel>Size</InputLabel>
            <Select
              value={formData.size}
              onChange={(e) => setFormData({ ...formData, size: e.target.value as any })}
              label="Size"
            >
              <MenuItem value="micro">
                Micro - {sizeConfig.micro.cpu} CPU, {sizeConfig.micro.memory}GB RAM (${sizeConfig.micro.price}/hr)
              </MenuItem>
              <MenuItem value="small">
                Small - {sizeConfig.small.cpu} CPU, {sizeConfig.small.memory}GB RAM (${sizeConfig.small.price}/hr)
              </MenuItem>
              <MenuItem value="medium">
                Medium - {sizeConfig.medium.cpu} CPU, {sizeConfig.medium.memory}GB RAM (${sizeConfig.medium.price}/hr)
              </MenuItem>
              <MenuItem value="large">
                Large - {sizeConfig.large.cpu} CPU, {sizeConfig.large.memory}GB RAM (${sizeConfig.large.price}/hr)
              </MenuItem>
            </Select>
          </FormControl>

          <FormControl fullWidth margin="normal">
            <InputLabel>Region</InputLabel>
            <Select
              value={formData.region}
              onChange={(e) => setFormData({ ...formData, region: e.target.value })}
              label="Region"
            >
              <MenuItem value="us-east-1">US East (N. Virginia)</MenuItem>
              <MenuItem value="us-west-2">US West (Oregon)</MenuItem>
              <MenuItem value="eu-west-1">EU (Ireland)</MenuItem>
              <MenuItem value="ap-southeast-1">Asia Pacific (Singapore)</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreateDatabase} variant="contained">
            Create Database
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};