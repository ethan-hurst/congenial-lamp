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
  LinearProgress,
} from '@mui/material';
import {
  CloudQueue as CDNIcon,
  Add as AddIcon,
  Settings as SettingsIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  Speed as SpeedIcon,
  Security as SecurityIcon,
  ExpandMore as ExpandMoreIcon,
  Analytics as AnalyticsIcon,
  ClearAll as PurgeIcon,
  TrendingUp as TrendingUpIcon,
  Storage as CacheIcon,
} from '@mui/icons-material';
import { api } from '../../services/api';

interface CDNConfiguration {
  id: string;
  domain_id: string;
  provider: string;
  status: string;
  distribution_id?: string;
  cname?: string;
  default_ttl: number;
  max_ttl: number;
  compression_enabled: boolean;
  waf_enabled: boolean;
  ddos_protection: boolean;
  cache_hit_ratio: number;
  bandwidth_usage: any;
  created_at: string;
  updated_at: string;
}

interface CDNConfigurationProps {
  projectId: string;
  domains: any[];
}

interface CreateCDNDialogProps {
  open: boolean;
  onClose: () => void;
  onConfigure: (config: any) => void;
  loading: boolean;
  domains: any[];
}

const CreateCDNDialog: React.FC<CreateCDNDialogProps> = ({
  open,
  onClose,
  onConfigure,
  loading,
  domains,
}) => {
  const [selectedDomain, setSelectedDomain] = useState('');
  const [provider, setProvider] = useState('cloudflare');
  const [defaultTTL, setDefaultTTL] = useState(3600);
  const [maxTTL, setMaxTTL] = useState(86400);
  const [compressionEnabled, setCompressionEnabled] = useState(true);
  const [wafEnabled, setWafEnabled] = useState(true);
  const [ddosProtection, setDdosProtection] = useState(true);
  const [minification, setMinification] = useState({
    html: true,
    css: true,
    js: true,
  });
  const [error, setError] = useState('');

  const handleSubmit = () => {
    if (!selectedDomain) {
      setError('Please select a domain');
      return;
    }

    setError('');
    onConfigure({
      domain_id: selectedDomain,
      provider,
      default_ttl: defaultTTL,
      max_ttl: maxTTL,
      compression_enabled: compressionEnabled,
      waf_enabled: wafEnabled,
      ddos_protection: ddosProtection,
      minification,
    });
  };

  const handleClose = () => {
    setSelectedDomain('');
    setProvider('cloudflare');
    setDefaultTTL(3600);
    setMaxTTL(86400);
    setCompressionEnabled(true);
    setWafEnabled(true);
    setDdosProtection(true);
    setMinification({ html: true, css: true, js: true });
    setError('');
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>Configure CDN</DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 1 }}>
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

          <FormControl fullWidth margin="normal">
            <InputLabel>CDN Provider</InputLabel>
            <Select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              label="CDN Provider"
            >
              <MenuItem value="cloudflare">Cloudflare</MenuItem>
              <MenuItem value="fastly">Fastly</MenuItem>
              <MenuItem value="aws_cloudfront">AWS CloudFront</MenuItem>
              <MenuItem value="azure_cdn">Azure CDN</MenuItem>
            </Select>
          </FormControl>

          <Accordion sx={{ mt: 2 }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography>Cache Settings</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <Typography gutterBottom>Default TTL (seconds)</Typography>
                  <Slider
                    value={defaultTTL}
                    onChange={(_, value) => setDefaultTTL(value as number)}
                    min={60}
                    max={86400}
                    step={60}
                    marks={[
                      { value: 60, label: '1m' },
                      { value: 3600, label: '1h' },
                      { value: 86400, label: '24h' },
                    ]}
                    valueLabelDisplay="auto"
                    valueLabelFormat={(value) =>
                      value < 3600 ? `${Math.round(value / 60)}m` : `${Math.round(value / 3600)}h`
                    }
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography gutterBottom>Max TTL (seconds)</Typography>
                  <Slider
                    value={maxTTL}
                    onChange={(_, value) => setMaxTTL(value as number)}
                    min={300}
                    max={604800}
                    step={300}
                    marks={[
                      { value: 3600, label: '1h' },
                      { value: 86400, label: '1d' },
                      { value: 604800, label: '7d' },
                    ]}
                    valueLabelDisplay="auto"
                    valueLabelFormat={(value) =>
                      value < 86400 ? `${Math.round(value / 3600)}h` : `${Math.round(value / 86400)}d`
                    }
                  />
                </Grid>
              </Grid>
            </AccordionDetails>
          </Accordion>

          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography>Optimization Settings</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={compressionEnabled}
                        onChange={(e) => setCompressionEnabled(e.target.checked)}
                      />
                    }
                    label="Enable Compression (Gzip/Brotli)"
                  />
                </Grid>
                <Grid item xs={4}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={minification.html}
                        onChange={(e) =>
                          setMinification({ ...minification, html: e.target.checked })
                        }
                      />
                    }
                    label="Minify HTML"
                  />
                </Grid>
                <Grid item xs={4}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={minification.css}
                        onChange={(e) =>
                          setMinification({ ...minification, css: e.target.checked })
                        }
                      />
                    }
                    label="Minify CSS"
                  />
                </Grid>
                <Grid item xs={4}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={minification.js}
                        onChange={(e) =>
                          setMinification({ ...minification, js: e.target.checked })
                        }
                      />
                    }
                    label="Minify JS"
                  />
                </Grid>
              </Grid>
            </AccordionDetails>
          </Accordion>

          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography>Security Settings</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={wafEnabled}
                        onChange={(e) => setWafEnabled(e.target.checked)}
                      />
                    }
                    label="Web Application Firewall (WAF)"
                  />
                </Grid>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={ddosProtection}
                        onChange={(e) => setDdosProtection(e.target.checked)}
                      />
                    }
                    label="DDoS Protection"
                  />
                </Grid>
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
          {loading ? <CircularProgress size={24} /> : 'Configure CDN'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

const CDNCard: React.FC<{
  config: CDNConfiguration;
  onUpdate: (configId: string) => void;
  onDelete: (configId: string) => void;
  onPurge: (configId: string) => void;
  onAnalytics: (configId: string) => void;
}> = ({ config, onUpdate, onDelete, onPurge, onAnalytics }) => {
  const getStatusIcon = () => {
    switch (config.status) {
      case 'active':
        return <SpeedIcon color="success" />;
      case 'pending':
        return <CircularProgress size={20} />;
      case 'failed':
        return <SecurityIcon color="error" />;
      default:
        return <CDNIcon color="warning" />;
    }
  };

  const getStatusColor = () => {
    switch (config.status) {
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

  const formatTTL = (seconds: number) => {
    if (seconds < 3600) {
      return `${Math.round(seconds / 60)}m`;
    } else if (seconds < 86400) {
      return `${Math.round(seconds / 3600)}h`;
    } else {
      return `${Math.round(seconds / 86400)}d`;
    }
  };

  return (
    <Card>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
          <Box display="flex" alignItems="center" gap={1}>
            <CDNIcon />
            <Typography variant="h6">{config.provider}</Typography>
            {config.cname && (
              <Typography variant="caption" color="textSecondary">
                {config.cname}
              </Typography>
            )}
          </Box>
          <Box display="flex" alignItems="center" gap={1}>
            <Chip
              label={config.status}
              color={getStatusColor() as any}
              size="small"
              icon={getStatusIcon()}
            />
            <IconButton size="small" onClick={() => onUpdate(config.id)}>
              <SettingsIcon />
            </IconButton>
            <IconButton size="small" onClick={() => onPurge(config.id)}>
              <PurgeIcon />
            </IconButton>
            <IconButton
              size="small"
              color="error"
              onClick={() => onDelete(config.id)}
            >
              <DeleteIcon />
            </IconButton>
          </Box>
        </Box>

        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <CacheIcon fontSize="small" />
                <Typography variant="subtitle2">Cache Settings</Typography>
              </Box>
              <Typography variant="body2" color="textSecondary">
                Default TTL: {formatTTL(config.default_ttl)}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Max TTL: {formatTTL(config.max_ttl)}
              </Typography>
              <Box mt={1}>
                <Typography variant="caption" color="textSecondary">
                  Hit Ratio
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={config.cache_hit_ratio * 100}
                  sx={{ mt: 0.5, mb: 1 }}
                />
                <Typography variant="caption">
                  {(config.cache_hit_ratio * 100).toFixed(1)}%
                </Typography>
              </Box>
            </Paper>
          </Grid>

          <Grid item xs={12} sm={6}>
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <SecurityIcon fontSize="small" />
                <Typography variant="subtitle2">Security & Optimization</Typography>
              </Box>
              <Box display="flex" gap={1} flexWrap="wrap">
                {config.compression_enabled && (
                  <Chip label="Compression" size="small" color="primary" />
                )}
                {config.waf_enabled && (
                  <Chip label="WAF" size="small" color="primary" />
                )}
                {config.ddos_protection && (
                  <Chip label="DDoS Protection" size="small" color="primary" />
                )}
              </Box>
              <Box mt={1}>
                <Typography variant="caption" color="textSecondary">
                  Bandwidth Usage (Last 30 days)
                </Typography>
                <Typography variant="body2">
                  {config.bandwidth_usage?.total_gb || 0} GB
                </Typography>
              </Box>
            </Paper>
          </Grid>
        </Grid>

        <Box mt={2}>
          <Typography variant="caption" color="textSecondary">
            Created: {new Date(config.created_at).toLocaleDateString()}
            {config.distribution_id && (
              <> • Distribution: {config.distribution_id}</>
            )}
          </Typography>
        </Box>
      </CardContent>

      <CardActions>
        <Button size="small" startIcon={<AnalyticsIcon />} onClick={() => onAnalytics(config.id)}>
          Analytics
        </Button>
        <Button size="small" startIcon={<PurgeIcon />} onClick={() => onPurge(config.id)}>
          Purge Cache
        </Button>
        <Button size="small" startIcon={<TrendingUpIcon />}>
          Performance
        </Button>
      </CardActions>
    </Card>
  );
};

export const CDNConfiguration: React.FC<CDNConfigurationProps> = ({ projectId, domains }) => {
  const [configurations, setConfigurations] = useState<CDNConfiguration[]>([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchConfigurations();
  }, [projectId]);

  const fetchConfigurations = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/api/v1/infrastructure/cdn?project_id=${projectId}`);
      setConfigurations(response.data);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch CDN configurations');
      console.error('Failed to fetch CDN configurations:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCDN = async (config: any) => {
    try {
      setCreateLoading(true);
      await api.post(`/api/v1/infrastructure/cdn?domain_id=${config.domain_id}`, config);
      
      setCreateDialogOpen(false);
      await fetchConfigurations();
    } catch (err: any) {
      console.error('Failed to create CDN configuration:', err);
      // Error will be shown in the dialog
    } finally {
      setCreateLoading(false);
    }
  };

  const handleUpdateCDN = async (configId: string) => {
    // TODO: Implement update dialog
    console.log('Update CDN configuration:', configId);
  };

  const handleDeleteCDN = async (configId: string) => {
    if (!confirm('Are you sure you want to delete this CDN configuration? This action cannot be undone.')) {
      return;
    }

    try {
      await api.delete(`/api/v1/infrastructure/cdn/${configId}`);
      await fetchConfigurations();
    } catch (err: any) {
      console.error('Failed to delete CDN configuration:', err);
    }
  };

  const handlePurgeCache = async (configId: string) => {
    try {
      await api.post(`/api/v1/infrastructure/cdn/${configId}/purge`);
      // Show success message
      console.log('Cache purged successfully');
    } catch (err: any) {
      console.error('Failed to purge cache:', err);
    }
  };

  const handleViewAnalytics = async (configId: string) => {
    // TODO: Implement analytics view
    console.log('View analytics for:', configId);
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
        <Typography variant="h5">CDN Configuration</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateDialogOpen(true)}
          disabled={domains.length === 0}
        >
          Configure CDN
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {domains.length === 0 && (
        <Alert severity="info" sx={{ mb: 3 }}>
          Add a custom domain first before configuring CDN.
        </Alert>
      )}

      {configurations.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <CDNIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              No CDN configurations
            </Typography>
            <Typography variant="body2" color="textSecondary" paragraph>
              Configure a CDN to accelerate your content delivery globally and improve performance.
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => setCreateDialogOpen(true)}
              disabled={domains.length === 0}
            >
              Configure Your First CDN
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Grid container spacing={3}>
          {configurations.map((config) => (
            <Grid item xs={12} lg={6} key={config.id}>
              <CDNCard
                config={config}
                onUpdate={handleUpdateCDN}
                onDelete={handleDeleteCDN}
                onPurge={handlePurgeCache}
                onAnalytics={handleViewAnalytics}
              />
            </Grid>
          ))}
        </Grid>
      )}

      <CreateCDNDialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        onConfigure={handleCreateCDN}
        loading={createLoading}
        domains={domains}
      />
    </Box>
  );
};