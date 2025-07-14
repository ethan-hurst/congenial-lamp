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
  Slider,
  Tooltip,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  TableContainer,
} from '@mui/material';
import {
  AccountTree as LoadBalancerIcon,
  Add as AddIcon,
  Settings as SettingsIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  Health as HealthIcon,
  Speed as SpeedIcon,
  ExpandMore as ExpandMoreIcon,
  Computer as ServerIcon,
  Timeline as MetricsIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Delete,
} from '@mui/icons-material';
import { api } from '../../services/api';

interface Backend {
  ip: string;
  port: number;
  weight: number;
  healthy: boolean;
  response_time_ms?: number;
}

interface LoadBalancer {
  id: string;
  domain_id: string;
  name: string;
  algorithm: string;
  status: string;
  backend_servers: Backend[];
  health_check_enabled: boolean;
  health_check_path: string;
  health_check_interval: number;
  external_ip?: string;
  dns_name?: string;
  active_connections: number;
  requests_per_second: number;
  response_time_p95: number;
  error_rate: number;
  created_at: string;
  updated_at: string;
}

interface LoadBalancerProps {
  projectId: string;
  domains: any[];
}

interface CreateLoadBalancerDialogProps {
  open: boolean;
  onClose: () => void;
  onCreate: (config: any) => void;
  loading: boolean;
  domains: any[];
}

const CreateLoadBalancerDialog: React.FC<CreateLoadBalancerDialogProps> = ({
  open,
  onClose,
  onCreate,
  loading,
  domains,
}) => {
  const [selectedDomain, setSelectedDomain] = useState('');
  const [name, setName] = useState('');
  const [algorithm, setAlgorithm] = useState('round_robin');
  const [backends, setBackends] = useState<Backend[]>([
    { ip: '', port: 80, weight: 100, healthy: true },
  ]);
  const [healthCheckEnabled, setHealthCheckEnabled] = useState(true);
  const [healthCheckPath, setHealthCheckPath] = useState('/health');
  const [healthCheckInterval, setHealthCheckInterval] = useState(30);
  const [error, setError] = useState('');

  const addBackend = () => {
    setBackends([...backends, { ip: '', port: 80, weight: 100, healthy: true }]);
  };

  const removeBackend = (index: number) => {
    if (backends.length > 1) {
      setBackends(backends.filter((_, i) => i !== index));
    }
  };

  const updateBackend = (index: number, field: keyof Backend, value: any) => {
    const newBackends = [...backends];
    newBackends[index] = { ...newBackends[index], [field]: value };
    setBackends(newBackends);
  };

  const handleSubmit = () => {
    if (!selectedDomain) {
      setError('Please select a domain');
      return;
    }
    if (!name.trim()) {
      setError('Please enter a load balancer name');
      return;
    }
    
    // Validate backends
    for (const backend of backends) {
      if (!backend.ip.trim()) {
        setError('Please enter IP addresses for all backends');
        return;
      }
      if (backend.port < 1 || backend.port > 65535) {
        setError('Port numbers must be between 1 and 65535');
        return;
      }
    }

    setError('');
    onCreate({
      domain_id: selectedDomain,
      name: name.trim(),
      backend_servers: backends.map(b => ({
        ip: b.ip.trim(),
        port: b.port,
        weight: b.weight,
      })),
      algorithm,
      health_check_config: healthCheckEnabled ? {
        enabled: true,
        path: healthCheckPath,
        interval: healthCheckInterval,
      } : null,
    });
  };

  const handleClose = () => {
    setSelectedDomain('');
    setName('');
    setAlgorithm('round_robin');
    setBackends([{ ip: '', port: 80, weight: 100, healthy: true }]);
    setHealthCheckEnabled(true);
    setHealthCheckPath('/health');
    setHealthCheckInterval(30);
    setError('');
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>Create Load Balancer</DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 1 }}>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth margin="normal">
                <InputLabel>Domain</InputLabel>
                <Select
                  value={selectedDomain}
                  onChange={(e) => setSelectedDomain(e.target.value)}
                  label="Domain"
                >
                  {domains.map((domain) => (
                    <MenuItem key={domain.domain.id} value={domain.domain.id}>
                      {domain.domain.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Load Balancer Name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                margin="normal"
                placeholder="my-load-balancer"
              />
            </Grid>
          </Grid>

          <FormControl fullWidth margin="normal">
            <InputLabel>Load Balancing Algorithm</InputLabel>
            <Select
              value={algorithm}
              onChange={(e) => setAlgorithm(e.target.value)}
              label="Load Balancing Algorithm"
            >
              <MenuItem value="round_robin">Round Robin</MenuItem>
              <MenuItem value="least_connections">Least Connections</MenuItem>
              <MenuItem value="ip_hash">IP Hash (Sticky Sessions)</MenuItem>
              <MenuItem value="weighted_round_robin">Weighted Round Robin</MenuItem>
            </Select>
          </FormControl>

          <Accordion sx={{ mt: 2 }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography>Backend Servers ({backends.length})</Typography>
            </AccordionSummary>
            <AccordionDetails>
              {backends.map((backend, index) => (
                <Paper key={index} variant="outlined" sx={{ p: 2, mb: 2 }}>
                  <Grid container spacing={2} alignItems="center">
                    <Grid item xs={12} sm={4}>
                      <TextField
                        fullWidth
                        label="IP Address"
                        value={backend.ip}
                        onChange={(e) => updateBackend(index, 'ip', e.target.value)}
                        placeholder="192.168.1.100"
                        size="small"
                      />
                    </Grid>
                    <Grid item xs={12} sm={3}>
                      <TextField
                        fullWidth
                        label="Port"
                        type="number"
                        value={backend.port}
                        onChange={(e) => updateBackend(index, 'port', parseInt(e.target.value))}
                        size="small"
                        inputProps={{ min: 1, max: 65535 }}
                      />
                    </Grid>
                    <Grid item xs={12} sm={3}>
                      <TextField
                        fullWidth
                        label="Weight"
                        type="number"
                        value={backend.weight}
                        onChange={(e) => updateBackend(index, 'weight', parseInt(e.target.value))}
                        size="small"
                        inputProps={{ min: 1, max: 1000 }}
                      />
                    </Grid>
                    <Grid item xs={12} sm={2}>
                      <IconButton
                        color="error"
                        onClick={() => removeBackend(index)}
                        disabled={backends.length === 1}
                      >
                        <Delete />
                      </IconButton>
                    </Grid>
                  </Grid>
                </Paper>
              ))}
              <Button
                startIcon={<AddIcon />}
                onClick={addBackend}
                variant="outlined"
                fullWidth
              >
                Add Backend Server
              </Button>
            </AccordionDetails>
          </Accordion>

          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography>Health Check Configuration</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={healthCheckEnabled}
                        onChange={(e) => setHealthCheckEnabled(e.target.checked)}
                      />
                    }
                    label="Enable Health Checks"
                  />
                </Grid>
                {healthCheckEnabled && (
                  <>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        fullWidth
                        label="Health Check Path"
                        value={healthCheckPath}
                        onChange={(e) => setHealthCheckPath(e.target.value)}
                        placeholder="/health"
                      />
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        fullWidth
                        label="Check Interval (seconds)"
                        type="number"
                        value={healthCheckInterval}
                        onChange={(e) => setHealthCheckInterval(parseInt(e.target.value))}
                        inputProps={{ min: 5, max: 300 }}
                      />
                    </Grid>
                  </>
                )}
              </Grid>
            </AccordionDetails>
          </Accordion>

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
          {loading ? <CircularProgress size={24} /> : 'Create Load Balancer'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

const LoadBalancerCard: React.FC<{
  loadBalancer: LoadBalancer;
  onUpdate: (lbId: string) => void;
  onDelete: (lbId: string) => void;
  onViewMetrics: (lbId: string) => void;
}> = ({ loadBalancer, onUpdate, onDelete, onViewMetrics }) => {
  const getStatusIcon = () => {
    switch (loadBalancer.status) {
      case 'active':
        return <CheckCircleIcon color="success" />;
      case 'pending':
        return <CircularProgress size={20} />;
      case 'failed':
        return <ErrorIcon color="error" />;
      default:
        return <WarningIcon color="warning" />;
    }
  };

  const getStatusColor = () => {
    switch (loadBalancer.status) {
      case 'active':
        return 'success';
      case 'pending':
        return 'warning';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const getHealthyBackends = () => {
    return loadBalancer.backend_servers.filter(b => b.healthy).length;
  };

  const formatAlgorithm = (algorithm: string) => {
    return algorithm.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  return (
    <Card>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
          <Box display="flex" alignItems="center" gap={1}>
            <LoadBalancerIcon />
            <Typography variant="h6">{loadBalancer.name}</Typography>
          </Box>
          <Box display="flex" alignItems="center" gap={1}>
            <Chip
              label={loadBalancer.status}
              color={getStatusColor() as any}
              size="small"
              icon={getStatusIcon()}
            />
            <IconButton size="small" onClick={() => onUpdate(loadBalancer.id)}>
              <SettingsIcon />
            </IconButton>
            <IconButton
              size="small"
              color="error"
              onClick={() => onDelete(loadBalancer.id)}
            >
              <DeleteIcon />
            </IconButton>
          </Box>
        </Box>

        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <ServerIcon fontSize="small" />
                <Typography variant="subtitle2">Backend Servers</Typography>
              </Box>
              <Typography variant="h6" color="primary">
                {getHealthyBackends()}/{loadBalancer.backend_servers.length}
              </Typography>
              <Typography variant="caption" color="textSecondary">
                Healthy Backends
              </Typography>
              <Box mt={1}>
                <Typography variant="caption" color="textSecondary">
                  Algorithm: {formatAlgorithm(loadBalancer.algorithm)}
                </Typography>
              </Box>
            </Paper>
          </Grid>

          <Grid item xs={12} sm={6}>
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <MetricsIcon fontSize="small" />
                <Typography variant="subtitle2">Performance</Typography>
              </Box>
              <Typography variant="body2">
                <strong>{loadBalancer.requests_per_second}</strong> RPS
              </Typography>
              <Typography variant="body2">
                <strong>{loadBalancer.response_time_p95}ms</strong> P95 Response Time
              </Typography>
              <Typography variant="body2">
                <strong>{(loadBalancer.error_rate * 100).toFixed(2)}%</strong> Error Rate
              </Typography>
            </Paper>
          </Grid>
        </Grid>

        {loadBalancer.external_ip && (
          <Box mt={2}>
            <Alert severity="info">
              <Typography variant="body2">
                <strong>External IP:</strong> {loadBalancer.external_ip}
                {loadBalancer.dns_name && (
                  <><br /><strong>DNS Name:</strong> {loadBalancer.dns_name}</>
                )}
              </Typography>
            </Alert>
          </Box>
        )}

        <Accordion sx={{ mt: 2 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle2">Backend Health Status</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Server</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Weight</TableCell>
                    <TableCell>Response Time</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {loadBalancer.backend_servers.map((backend, index) => (
                    <TableRow key={index}>
                      <TableCell>{backend.ip}:{backend.port}</TableCell>
                      <TableCell>
                        <Chip
                          label={backend.healthy ? 'Healthy' : 'Unhealthy'}
                          color={backend.healthy ? 'success' : 'error'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{backend.weight}</TableCell>
                      <TableCell>
                        {backend.response_time_ms ? `${backend.response_time_ms}ms` : 'N/A'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </AccordionDetails>
        </Accordion>

        <Box mt={2}>
          <Typography variant="caption" color="textSecondary">
            Created: {new Date(loadBalancer.created_at).toLocaleDateString()}
            • Active Connections: {loadBalancer.active_connections}
          </Typography>
        </Box>
      </CardContent>

      <CardActions>
        <Button size="small" startIcon={<HealthIcon />}>
          Health Checks
        </Button>
        <Button size="small" startIcon={<MetricsIcon />} onClick={() => onViewMetrics(loadBalancer.id)}>
          Metrics
        </Button>
        <Button size="small" startIcon={<SettingsIcon />} onClick={() => onUpdate(loadBalancer.id)}>
          Configure
        </Button>
      </CardActions>
    </Card>
  );
};

export const LoadBalancer: React.FC<LoadBalancerProps> = ({ projectId, domains }) => {
  const [loadBalancers, setLoadBalancers] = useState<LoadBalancer[]>([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchLoadBalancers();
  }, [projectId]);

  const fetchLoadBalancers = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/api/v1/infrastructure/load-balancers?project_id=${projectId}`);
      setLoadBalancers(response.data);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch load balancers');
      console.error('Failed to fetch load balancers:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateLoadBalancer = async (config: any) => {
    try {
      setCreateLoading(true);
      await api.post(`/api/v1/infrastructure/load-balancers?domain_id=${config.domain_id}`, config);
      
      setCreateDialogOpen(false);
      await fetchLoadBalancers();
    } catch (err: any) {
      console.error('Failed to create load balancer:', err);
      // Error will be shown in the dialog
    } finally {
      setCreateLoading(false);
    }
  };

  const handleUpdateLoadBalancer = async (lbId: string) => {
    // TODO: Implement update dialog
    console.log('Update load balancer:', lbId);
  };

  const handleDeleteLoadBalancer = async (lbId: string) => {
    if (!confirm('Are you sure you want to delete this load balancer? This action cannot be undone.')) {
      return;
    }

    try {
      await api.delete(`/api/v1/infrastructure/load-balancers/${lbId}`);
      await fetchLoadBalancers();
    } catch (err: any) {
      console.error('Failed to delete load balancer:', err);
    }
  };

  const handleViewMetrics = async (lbId: string) => {
    // TODO: Implement metrics view
    console.log('View metrics for:', lbId);
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
        <Typography variant="h5">Load Balancers</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateDialogOpen(true)}
          disabled={domains.length === 0}
        >
          Create Load Balancer
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {domains.length === 0 && (
        <Alert severity="info" sx={{ mb: 3 }}>
          Add a custom domain first before creating load balancers.
        </Alert>
      )}

      {loadBalancers.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <LoadBalancerIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              No load balancers configured
            </Typography>
            <Typography variant="body2" color="textSecondary" paragraph>
              Create load balancers to distribute traffic across multiple backend servers for high availability and performance.
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => setCreateDialogOpen(true)}
              disabled={domains.length === 0}
            >
              Create Your First Load Balancer
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Grid container spacing={3}>
          {loadBalancers.map((lb) => (
            <Grid item xs={12} key={lb.id}>
              <LoadBalancerCard
                loadBalancer={lb}
                onUpdate={handleUpdateLoadBalancer}
                onDelete={handleDeleteLoadBalancer}
                onViewMetrics={handleViewMetrics}
              />
            </Grid>
          ))}
        </Grid>
      )}

      <CreateLoadBalancerDialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        onCreate={handleCreateLoadBalancer}
        loading={createLoading}
        domains={domains}
      />
    </Box>
  );
};