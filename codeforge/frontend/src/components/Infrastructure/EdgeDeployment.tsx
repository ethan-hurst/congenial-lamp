import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Chip,
  IconButton,
  Alert,
  CircularProgress,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Paper,
  Tabs,
  Tab,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  TableContainer,
  LinearProgress,
  Tooltip,
} from '@mui/material';
import {
  Public as EdgeIcon,
  Add as AddIcon,
  CloudUpload as UploadIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  Speed as SpeedIcon,
  Memory as MemoryIcon,
  ExpandMore as ExpandMoreIcon,
  Code as CodeIcon,
  Timeline as MetricsIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Language as RuntimeIcon,
  Map as MapIcon,
  CloudQueue as CloudIcon,
  Logout as DeployIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';
import { api } from '../../services/api';

interface EdgeDeployment {
  id: string;
  name: string;
  description?: string;
  version: string;
  status: string;
  runtime: string;
  runtime_version: string;
  memory_limit: number;
  timeout: number;
  edge_locations: string[];
  deployment_url?: string;
  requests_per_minute: number;
  average_response_time: number;
  error_rate: number;
  cache_hit_ratio: number;
  cpu_usage: number;
  memory_usage: number;
  last_deployed_at?: string;
  created_at: string;
}

interface EdgeLocation {
  code: string;
  name: string;
  country: string;
  continent: string;
  latitude: number;
  longitude: number;
}

interface EdgeDeploymentProps {
  projectId: string;
}

interface CreateDeploymentDialogProps {
  open: boolean;
  onClose: () => void;
  onCreate: (config: any, codeFile: File) => void;
  loading: boolean;
}

const CreateDeploymentDialog: React.FC<CreateDeploymentDialogProps> = ({
  open,
  onClose,
  onCreate,
  loading,
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [runtime, setRuntime] = useState('nodejs');
  const [runtimeVersion, setRuntimeVersion] = useState('18');
  const [memoryLimit, setMemoryLimit] = useState(512);
  const [timeout, setTimeout] = useState(30);
  const [targetRegions, setTargetRegions] = useState<string[]>(['North America', 'Europe']);
  const [deploymentStrategy, setDeploymentStrategy] = useState('rolling');
  const [environmentVars, setEnvironmentVars] = useState<{[key: string]: string}>({});
  const [codeFile, setCodeFile] = useState<File | null>(null);
  const [error, setError] = useState('');
  const [tabValue, setTabValue] = useState(0);

  const availableRegions = [
    'North America',
    'Europe',
    'Asia Pacific',
    'South America',
    'Africa',
    'Middle East',
    'Oceania'
  ];

  const runtimeVersions = {
    nodejs: ['14', '16', '18', '20'],
    python: ['3.8', '3.9', '3.10', '3.11'],
    deno: ['1.37', '1.38', '1.39'],
    go: ['1.19', '1.20', '1.21'],
    rust: ['1.70', '1.71', '1.72'],
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      if (file.size > 50 * 1024 * 1024) { // 50MB limit
        setError('File size must be less than 50MB');
        return;
      }
      setCodeFile(file);
      setError('');
    }
  };

  const addEnvironmentVar = () => {
    const key = `ENV_VAR_${Object.keys(environmentVars).length + 1}`;
    setEnvironmentVars({ ...environmentVars, [key]: '' });
  };

  const updateEnvironmentVar = (oldKey: string, newKey: string, value: string) => {
    const newVars = { ...environmentVars };
    delete newVars[oldKey];
    newVars[newKey] = value;
    setEnvironmentVars(newVars);
  };

  const removeEnvironmentVar = (key: string) => {
    const newVars = { ...environmentVars };
    delete newVars[key];
    setEnvironmentVars(newVars);
  };

  const handleSubmit = () => {
    if (!name.trim()) {
      setError('Please enter a deployment name');
      return;
    }
    if (!codeFile) {
      setError('Please upload a code bundle');
      return;
    }
    if (targetRegions.length === 0) {
      setError('Please select at least one target region');
      return;
    }

    setError('');
    onCreate({
      name: name.trim(),
      description: description.trim(),
      runtime,
      runtime_version: runtimeVersion,
      memory_limit: memoryLimit,
      timeout,
      target_regions: targetRegions,
      deployment_strategy: deploymentStrategy,
      environment_variables: environmentVars,
    }, codeFile);
  };

  const handleClose = () => {
    setName('');
    setDescription('');
    setRuntime('nodejs');
    setRuntimeVersion('18');
    setMemoryLimit(512);
    setTimeout(30);
    setTargetRegions(['North America', 'Europe']);
    setDeploymentStrategy('rolling');
    setEnvironmentVars({});
    setCodeFile(null);
    setError('');
    setTabValue(0);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>Create Edge Deployment</DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 1 }}>
          <Tabs value={tabValue} onChange={(_, value) => setTabValue(value)} sx={{ mb: 2 }}>
            <Tab label="Basic Configuration" />
            <Tab label="Runtime Settings" />
            <Tab label="Environment" />
          </Tabs>

          {tabValue === 0 && (
            <Box>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Deployment Name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    margin="normal"
                    placeholder="my-edge-app"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Description"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    margin="normal"
                    placeholder="Edge deployment for..."
                  />
                </Grid>
              </Grid>

              <Box sx={{ mt: 2, mb: 2 }}>
                <Typography variant="subtitle1" gutterBottom>
                  Code Bundle
                </Typography>
                <input
                  accept=".zip,.tar.gz"
                  style={{ display: 'none' }}
                  id="code-file-upload"
                  type="file"
                  onChange={handleFileUpload}
                />
                <label htmlFor="code-file-upload">
                  <Button
                    variant="outlined"
                    component="span"
                    startIcon={<UploadIcon />}
                    fullWidth
                  >
                    {codeFile ? codeFile.name : 'Upload Code Bundle (.zip or .tar.gz)'}
                  </Button>
                </label>
                {codeFile && (
                  <Typography variant="caption" color="textSecondary" sx={{ mt: 1, display: 'block' }}>
                    Size: {(codeFile.size / 1024 / 1024).toFixed(2)} MB
                  </Typography>
                )}
              </Box>

              <FormControl fullWidth margin="normal">
                <InputLabel>Target Regions</InputLabel>
                <Select
                  multiple
                  value={targetRegions}
                  onChange={(e) => setTargetRegions(e.target.value as string[])}
                  label="Target Regions"
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((value) => (
                        <Chip key={value} label={value} size="small" />
                      ))}
                    </Box>
                  )}
                >
                  {availableRegions.map((region) => (
                    <MenuItem key={region} value={region}>
                      {region}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>
          )}

          {tabValue === 1 && (
            <Box>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth margin="normal">
                    <InputLabel>Runtime</InputLabel>
                    <Select
                      value={runtime}
                      onChange={(e) => {
                        setRuntime(e.target.value);
                        setRuntimeVersion(runtimeVersions[e.target.value as keyof typeof runtimeVersions][0]);
                      }}
                      label="Runtime"
                    >
                      <MenuItem value="nodejs">Node.js</MenuItem>
                      <MenuItem value="python">Python</MenuItem>
                      <MenuItem value="deno">Deno</MenuItem>
                      <MenuItem value="go">Go</MenuItem>
                      <MenuItem value="rust">Rust</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth margin="normal">
                    <InputLabel>Runtime Version</InputLabel>
                    <Select
                      value={runtimeVersion}
                      onChange={(e) => setRuntimeVersion(e.target.value)}
                      label="Runtime Version"
                    >
                      {runtimeVersions[runtime as keyof typeof runtimeVersions]?.map((version) => (
                        <MenuItem key={version} value={version}>
                          {version}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>

              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Memory Limit (MB)"
                    type="number"
                    value={memoryLimit}
                    onChange={(e) => setMemoryLimit(parseInt(e.target.value))}
                    margin="normal"
                    inputProps={{ min: 128, max: 4096, step: 128 }}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Timeout (seconds)"
                    type="number"
                    value={timeout}
                    onChange={(e) => setTimeout(parseInt(e.target.value))}
                    margin="normal"
                    inputProps={{ min: 1, max: 300 }}
                  />
                </Grid>
              </Grid>

              <FormControl fullWidth margin="normal">
                <InputLabel>Deployment Strategy</InputLabel>
                <Select
                  value={deploymentStrategy}
                  onChange={(e) => setDeploymentStrategy(e.target.value)}
                  label="Deployment Strategy"
                >
                  <MenuItem value="rolling">Rolling Deployment</MenuItem>
                  <MenuItem value="blue_green">Blue-Green Deployment</MenuItem>
                  <MenuItem value="canary">Canary Deployment</MenuItem>
                </Select>
              </FormControl>
            </Box>
          )}

          {tabValue === 2 && (
            <Box>
              <Typography variant="subtitle1" gutterBottom>
                Environment Variables
              </Typography>
              {Object.entries(environmentVars).map(([key, value], index) => (
                <Grid container spacing={1} key={index} sx={{ mb: 1 }}>
                  <Grid item xs={5}>
                    <TextField
                      fullWidth
                      label="Key"
                      value={key}
                      onChange={(e) => updateEnvironmentVar(key, e.target.value, value)}
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={5}>
                    <TextField
                      fullWidth
                      label="Value"
                      value={value}
                      onChange={(e) => updateEnvironmentVar(key, key, e.target.value)}
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={2}>
                    <IconButton
                      color="error"
                      onClick={() => removeEnvironmentVar(key)}
                      size="small"
                    >
                      <DeleteIcon />
                    </IconButton>
                  </Grid>
                </Grid>
              ))}
              <Button
                startIcon={<AddIcon />}
                onClick={addEnvironmentVar}
                variant="outlined"
                size="small"
              >
                Add Environment Variable
              </Button>
            </Box>
          )}

          {error && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {error}
            </Alert>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={loading}
        >
          {loading ? <CircularProgress size={24} /> : 'Deploy to Edge'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

const EdgeDeploymentCard: React.FC<{
  deployment: EdgeDeployment;
  onUpdate: (deploymentId: string) => void;
  onDelete: (deploymentId: string) => void;
  onViewLogs: (deploymentId: string) => void;
  onScale: (deploymentId: string) => void;
}> = ({ deployment, onUpdate, onDelete, onViewLogs, onScale }) => {
  const getStatusIcon = () => {
    switch (deployment.status) {
      case 'active':
        return <CheckCircleIcon color="success" />;
      case 'deploying':
        return <CircularProgress size={20} />;
      case 'failed':
        return <ErrorIcon color="error" />;
      default:
        return <WarningIcon color="warning" />;
    }
  };

  const getStatusColor = () => {
    switch (deployment.status) {
      case 'active':
        return 'success';
      case 'deploying':
        return 'warning';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const formatMemory = (mb: number) => {
    return mb >= 1024 ? `${(mb / 1024).toFixed(1)}GB` : `${mb}MB`;
  };

  return (
    <Card>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
          <Box display="flex" alignItems="center" gap={1}>
            <EdgeIcon />
            <Box>
              <Typography variant="h6">{deployment.name}</Typography>
              {deployment.description && (
                <Typography variant="caption" color="textSecondary">
                  {deployment.description}
                </Typography>
              )}
            </Box>
          </Box>
          <Box display="flex" alignItems="center" gap={1}>
            <Chip
              label={deployment.status}
              color={getStatusColor() as any}
              size="small"
              icon={getStatusIcon()}
            />
            <IconButton size="small" onClick={() => onUpdate(deployment.id)}>
              <SettingsIcon />
            </IconButton>
            <IconButton
              size="small"
              color="error"
              onClick={() => onDelete(deployment.id)}
            >
              <DeleteIcon />
            </IconButton>
          </Box>
        </Box>

        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <RuntimeIcon fontSize="small" />
                <Typography variant="subtitle2">Runtime</Typography>
              </Box>
              <Typography variant="body2">
                <strong>{deployment.runtime}</strong> v{deployment.runtime_version}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Memory: {formatMemory(deployment.memory_limit)}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Timeout: {deployment.timeout}s
              </Typography>
            </Paper>
          </Grid>

          <Grid item xs={12} sm={6}>
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <MetricsIcon fontSize="small" />
                <Typography variant="subtitle2">Performance</Typography>
              </Box>
              <Typography variant="body2">
                <strong>{deployment.requests_per_minute}</strong> RPM
              </Typography>
              <Typography variant="body2">
                <strong>{deployment.average_response_time}ms</strong> Avg Response
              </Typography>
              <Typography variant="body2">
                <strong>{(deployment.error_rate * 100).toFixed(2)}%</strong> Error Rate
              </Typography>
            </Paper>
          </Grid>
        </Grid>

        <Box mt={2}>
          <Typography variant="subtitle2" gutterBottom>
            Edge Locations ({deployment.edge_locations.length})
          </Typography>
          <Box display="flex" gap={1} flexWrap="wrap">
            {deployment.edge_locations.slice(0, 5).map((location, index) => (
              <Chip key={index} label={location} size="small" variant="outlined" />
            ))}
            {deployment.edge_locations.length > 5 && (
              <Chip
                label={`+${deployment.edge_locations.length - 5} more`}
                size="small"
                variant="outlined"
              />
            )}
          </Box>
        </Box>

        <Box mt={2}>
          <Typography variant="subtitle2" gutterBottom>
            Resource Usage
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={6}>
              <Typography variant="caption" color="textSecondary">
                CPU Usage
              </Typography>
              <LinearProgress
                variant="determinate"
                value={deployment.cpu_usage}
                sx={{ mt: 0.5, mb: 1 }}
                color={deployment.cpu_usage > 80 ? 'error' : 'primary'}
              />
              <Typography variant="caption">
                {deployment.cpu_usage.toFixed(1)}%
              </Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="caption" color="textSecondary">
                Memory Usage
              </Typography>
              <LinearProgress
                variant="determinate"
                value={deployment.memory_usage}
                sx={{ mt: 0.5, mb: 1 }}
                color={deployment.memory_usage > 80 ? 'error' : 'primary'}
              />
              <Typography variant="caption">
                {deployment.memory_usage.toFixed(1)}%
              </Typography>
            </Grid>
          </Grid>
        </Box>

        {deployment.deployment_url && (
          <Box mt={2}>
            <Alert severity="info">
              <Typography variant="body2">
                <strong>Deployment URL:</strong>{' '}
                <a href={deployment.deployment_url} target="_blank" rel="noopener noreferrer">
                  {deployment.deployment_url}
                </a>
              </Typography>
            </Alert>
          </Box>
        )}

        <Box mt={2}>
          <Typography variant="caption" color="textSecondary">
            Version: {deployment.version}
            {deployment.last_deployed_at && (
              <> • Last deployed: {new Date(deployment.last_deployed_at).toLocaleDateString()}</>
            )}
          </Typography>
        </Box>
      </CardContent>

      <CardActions>
        <Button size="small" startIcon={<CodeIcon />} onClick={() => onViewLogs(deployment.id)}>
          Logs
        </Button>
        <Button size="small" startIcon={<MapIcon />}>
          Locations
        </Button>
        <Button size="small" startIcon={<SpeedIcon />} onClick={() => onScale(deployment.id)}>
          Scale
        </Button>
        <Button size="small" startIcon={<MetricsIcon />}>
          Metrics
        </Button>
      </CardActions>
    </Card>
  );
};

export const EdgeDeployment: React.FC<EdgeDeploymentProps> = ({ projectId }) => {
  const [deployments, setDeployments] = useState<EdgeDeployment[]>([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDeployments();
  }, [projectId]);

  const fetchDeployments = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/api/v1/infrastructure/edge/deployments?project_id=${projectId}`);
      setDeployments(response.data);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch edge deployments');
      console.error('Failed to fetch edge deployments:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateDeployment = async (config: any, codeFile: File) => {
    try {
      setCreateLoading(true);
      
      const formData = new FormData();
      formData.append('code_bundle', codeFile);
      
      // Append other config as JSON
      Object.keys(config).forEach(key => {
        if (key !== 'code_bundle') {
          formData.append(key, typeof config[key] === 'object' ? JSON.stringify(config[key]) : config[key]);
        }
      });

      await api.post('/api/v1/infrastructure/edge/deployments', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      setCreateDialogOpen(false);
      await fetchDeployments();
    } catch (err: any) {
      console.error('Failed to create edge deployment:', err);
      // Error will be shown in the dialog
    } finally {
      setCreateLoading(false);
    }
  };

  const handleUpdateDeployment = async (deploymentId: string) => {
    // TODO: Implement update dialog
    console.log('Update deployment:', deploymentId);
  };

  const handleDeleteDeployment = async (deploymentId: string) => {
    if (!confirm('Are you sure you want to delete this edge deployment? This action cannot be undone.')) {
      return;
    }

    try {
      await api.delete(`/api/v1/infrastructure/edge/deployments/${deploymentId}`);
      await fetchDeployments();
    } catch (err: any) {
      console.error('Failed to delete edge deployment:', err);
    }
  };

  const handleViewLogs = async (deploymentId: string) => {
    // TODO: Implement logs view
    console.log('View logs for:', deploymentId);
  };

  const handleScaleDeployment = async (deploymentId: string) => {
    // TODO: Implement scaling dialog
    console.log('Scale deployment:', deploymentId);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" py={4}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5">Edge Deployments</Typography>
        <Button
          variant="contained"
          startIcon={<DeployIcon />}
          onClick={() => setCreateDialogOpen(true)}
        >
          Deploy to Edge
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {deployments.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <EdgeIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              No edge deployments
            </Typography>
            <Typography variant="body2" color="textSecondary" paragraph>
              Deploy your applications to 300+ edge locations worldwide for ultra-low latency and better user experience.
            </Typography>
            <Button
              variant="contained"
              startIcon={<DeployIcon />}
              onClick={() => setCreateDialogOpen(true)}
            >
              Deploy Your First Application
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Grid container spacing={3}>
          {deployments.map((deployment) => (
            <Grid item xs={12} lg={6} key={deployment.id}>
              <EdgeDeploymentCard
                deployment={deployment}
                onUpdate={handleUpdateDeployment}
                onDelete={handleDeleteDeployment}
                onViewLogs={handleViewLogs}
                onScale={handleScaleDeployment}
              />
            </Grid>
          ))}
        </Grid>
      )}

      <CreateDeploymentDialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        onCreate={handleCreateDeployment}
        loading={createLoading}
      />
    </Box>
  );
};