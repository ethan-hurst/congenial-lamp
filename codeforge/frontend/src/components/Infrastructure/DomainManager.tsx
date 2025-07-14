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
  Tooltip,
  LinearProgress,
} from '@mui/material';
import {
  Domain as DomainIcon,
  Add as AddIcon,
  Verified as VerifiedIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  Delete as DeleteIcon,
  Dns as DnsIcon,
  Security as SecurityIcon,
  Speed as SpeedIcon,
} from '@mui/icons-material';
import { api } from '../../services/api';

interface Domain {
  domain: {
    id: string;
    name: string;
    status: string;
    verified: boolean;
    created_at: string;
    verified_at?: string;
  };
  dns: {
    propagation_percentage: number;
    all_propagated: boolean;
    last_checked: string;
  };
  ssl: {
    has_ssl: boolean;
    expires?: string;
    issuer?: any;
  };
  performance: {
    response_time_ms?: number;
    available: boolean;
    last_checked: string;
  };
  configuration: {
    redirect_https: boolean;
    www_redirect: boolean;
    custom_headers: any;
  };
}

interface DomainManagerProps {
  projectId: string;
}

interface AddDomainDialogProps {
  open: boolean;
  onClose: () => void;
  onAdd: (domainName: string, dnsProvider: string) => void;
  loading: boolean;
}

const AddDomainDialog: React.FC<AddDomainDialogProps> = ({
  open,
  onClose,
  onAdd,
  loading,
}) => {
  const [domainName, setDomainName] = useState('');
  const [dnsProvider, setDnsProvider] = useState('cloudflare');
  const [error, setError] = useState('');

  const handleSubmit = () => {
    if (!domainName.trim()) {
      setError('Please enter a domain name');
      return;
    }

    // Basic domain validation
    const domainRegex = /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;
    if (!domainRegex.test(domainName)) {
      setError('Please enter a valid domain name');
      return;
    }

    setError('');
    onAdd(domainName, dnsProvider);
  };

  const handleClose = () => {
    setDomainName('');
    setDnsProvider('cloudflare');
    setError('');
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Add Custom Domain</DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 1 }}>
          <TextField
            fullWidth
            label="Domain Name"
            value={domainName}
            onChange={(e) => setDomainName(e.target.value.toLowerCase())}
            placeholder="example.com"
            margin="normal"
            helperText="Enter your custom domain (without http:// or https://)"
          />

          <FormControl fullWidth margin="normal">
            <InputLabel>DNS Provider</InputLabel>
            <Select
              value={dnsProvider}
              onChange={(e) => setDnsProvider(e.target.value)}
              label="DNS Provider"
            >
              <MenuItem value="cloudflare">Cloudflare</MenuItem>
              <MenuItem value="route53">AWS Route 53</MenuItem>
              <MenuItem value="digitalocean">DigitalOcean</MenuItem>
              <MenuItem value="namecheap">Namecheap</MenuItem>
            </Select>
          </FormControl>

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
          {loading ? <CircularProgress size={24} /> : 'Add Domain'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

const DomainCard: React.FC<{
  domain: Domain;
  onRefresh: (domainId: string) => void;
  onDelete: (domainId: string) => void;
}> = ({ domain, onRefresh, onDelete }) => {
  const getStatusIcon = () => {
    switch (domain.domain.status) {
      case 'active':
        return <VerifiedIcon color="success" />;
      case 'pending':
        return <CircularProgress size={20} />;
      case 'failed':
        return <ErrorIcon color="error" />;
      default:
        return <WarningIcon color="warning" />;
    }
  };

  const getStatusColor = () => {
    switch (domain.domain.status) {
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

  return (
    <Card>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
          <Box display="flex" alignItems="center" gap={1}>
            <DomainIcon />
            <Typography variant="h6">{domain.domain.name}</Typography>
          </Box>
          <Box display="flex" alignItems="center" gap={1}>
            <Chip
              label={domain.domain.status}
              color={getStatusColor() as any}
              size="small"
              icon={getStatusIcon()}
            />
            <IconButton size="small" onClick={() => onRefresh(domain.domain.id)}>
              <RefreshIcon />
            </IconButton>
            <IconButton
              size="small"
              color="error"
              onClick={() => onDelete(domain.domain.id)}
            >
              <DeleteIcon />
            </IconButton>
          </Box>
        </Box>

        <Grid container spacing={2}>
          <Grid item xs={12} sm={4}>
            <Box display="flex" alignItems="center" gap={1} mb={1}>
              <DnsIcon fontSize="small" />
              <Typography variant="subtitle2">DNS Status</Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={domain.dns.propagation_percentage}
              sx={{ mb: 1 }}
            />
            <Typography variant="caption" color="textSecondary">
              {domain.dns.propagation_percentage.toFixed(1)}% propagated
            </Typography>
          </Grid>

          <Grid item xs={12} sm={4}>
            <Box display="flex" alignItems="center" gap={1} mb={1}>
              <SecurityIcon fontSize="small" />
              <Typography variant="subtitle2">SSL Status</Typography>
            </Box>
            <Chip
              label={domain.ssl.has_ssl ? 'Secured' : 'No SSL'}
              color={domain.ssl.has_ssl ? 'success' : 'error'}
              size="small"
              sx={{ mb: 1 }}
            />
            {domain.ssl.expires && (
              <Typography variant="caption" display="block" color="textSecondary">
                Expires: {new Date(domain.ssl.expires).toLocaleDateString()}
              </Typography>
            )}
          </Grid>

          <Grid item xs={12} sm={4}>
            <Box display="flex" alignItems="center" gap={1} mb={1}>
              <SpeedIcon fontSize="small" />
              <Typography variant="subtitle2">Performance</Typography>
            </Box>
            <Chip
              label={domain.performance.available ? 'Online' : 'Offline'}
              color={domain.performance.available ? 'success' : 'error'}
              size="small"
              sx={{ mb: 1 }}
            />
            {domain.performance.response_time_ms && (
              <Typography variant="caption" display="block" color="textSecondary">
                {domain.performance.response_time_ms.toFixed(0)}ms response
              </Typography>
            )}
          </Grid>
        </Grid>

        <Box mt={2}>
          <Typography variant="caption" color="textSecondary">
            Added: {new Date(domain.domain.created_at).toLocaleDateString()}
            {domain.domain.verified_at && (
              <> • Verified: {new Date(domain.domain.verified_at).toLocaleDateString()}</>
            )}
          </Typography>
        </Box>
      </CardContent>

      <CardActions>
        <Button size="small" startIcon={<DnsIcon />}>
          DNS Settings
        </Button>
        <Button size="small" startIcon={<SecurityIcon />}>
          SSL Certificate
        </Button>
      </CardActions>
    </Card>
  );
};

export const DomainManager: React.FC<DomainManagerProps> = ({ projectId }) => {
  const [domains, setDomains] = useState<Domain[]>([]);
  const [loading, setLoading] = useState(true);
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [addLoading, setAddLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDomains();
  }, [projectId]);

  const fetchDomains = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/api/v1/infrastructure/domains?project_id=${projectId}`);
      setDomains(response.data);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch domains');
      console.error('Failed to fetch domains:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddDomain = async (domainName: string, dnsProvider: string) => {
    try {
      setAddLoading(true);
      await api.post(`/api/v1/infrastructure/domains?project_id=${projectId}`, {
        domain_name: domainName,
        dns_provider: dnsProvider,
      });
      
      setAddDialogOpen(false);
      await fetchDomains();
    } catch (err: any) {
      console.error('Failed to add domain:', err);
      // Error will be shown in the dialog
    } finally {
      setAddLoading(false);
    }
  };

  const handleRefreshDomain = async (domainId: string) => {
    try {
      await api.post(`/api/v1/infrastructure/domains/${domainId}/verify`);
      await fetchDomains();
    } catch (err: any) {
      console.error('Failed to refresh domain:', err);
    }
  };

  const handleDeleteDomain = async (domainId: string) => {
    if (!confirm('Are you sure you want to delete this domain? This action cannot be undone.')) {
      return;
    }

    try {
      await api.delete(`/api/v1/infrastructure/domains/${domainId}`);
      await fetchDomains();
    } catch (err: any) {
      console.error('Failed to delete domain:', err);
    }
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
        <Typography variant="h5">Custom Domains</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setAddDialogOpen(true)}
        >
          Add Domain
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {domains.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <DomainIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              No custom domains configured
            </Typography>
            <Typography variant="body2" color="textSecondary" paragraph>
              Add a custom domain to make your application accessible from your own domain name.
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => setAddDialogOpen(true)}
            >
              Add Your First Domain
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Grid container spacing={3}>
          {domains.map((domain) => (
            <Grid item xs={12} lg={6} key={domain.domain.id}>
              <DomainCard
                domain={domain}
                onRefresh={handleRefreshDomain}
                onDelete={handleDeleteDomain}
              />
            </Grid>
          ))}
        </Grid>
      )}

      <AddDomainDialog
        open={addDialogOpen}
        onClose={() => setAddDialogOpen(false)}
        onAdd={handleAddDomain}
        loading={addLoading}
      />
    </Box>
  );
};