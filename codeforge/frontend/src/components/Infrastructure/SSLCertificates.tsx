import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Chip,
  IconButton,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  LinearProgress,
} from '@mui/material';
import {
  Security as SecurityIcon,
  Add as AddIcon,
  Refresh as RefreshIcon,
  CheckCircle as ValidIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Download as DownloadIcon,
} from '@mui/icons-material';
import { api } from '../../services/api';

interface SSLCertificate {
  certificate: {
    id: string;
    domain: string;
    status: string;
    authority: string;
    issued_at?: string;
    expires_at?: string;
    days_until_expiry?: number;
    needs_renewal: boolean;
    auto_renew: boolean;
  };
  validation: {
    valid: boolean;
    issuer?: any;
    expires_at?: string;
    days_until_expiry?: number;
    error?: string;
  };
  metadata: {
    serial_number?: string;
    fingerprint?: string;
    key_size?: number;
    signature_algorithm?: string;
    subject_alternative_names?: string[];
  };
}

interface SSLCertificatesProps {
  projectId: string;
}

export const SSLCertificates: React.FC<SSLCertificatesProps> = ({ projectId }) => {
  const [certificates, setCertificates] = useState<SSLCertificate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCertificates();
  }, [projectId]);

  const fetchCertificates = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/api/v1/infrastructure/ssl/certificates?project_id=${projectId}`);
      setCertificates(response.data);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch SSL certificates');
      console.error('Failed to fetch SSL certificates:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRenewCertificate = async (certId: string) => {
    try {
      await api.post(`/api/v1/infrastructure/ssl/certificates/${certId}/renew`);
      await fetchCertificates();
    } catch (err: any) {
      console.error('Failed to renew certificate:', err);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <ValidIcon color="success" />;
      case 'expired':
        return <ErrorIcon color="error" />;
      case 'pending':
        return <CircularProgress size={20} />;
      default:
        return <WarningIcon color="warning" />;
    }
  };

  const getExpiryColor = (daysUntilExpiry?: number) => {
    if (!daysUntilExpiry) return 'default';
    if (daysUntilExpiry <= 7) return 'error';
    if (daysUntilExpiry <= 30) return 'warning';
    return 'success';
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
        <Typography variant="h5">SSL Certificates</Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={fetchCertificates}
        >
          Refresh
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {certificates.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <SecurityIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              No SSL certificates found
            </Typography>
            <Typography variant="body2" color="textSecondary">
              SSL certificates are automatically provisioned when you add a domain.
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <Grid container spacing={3}>
          {certificates.map((cert) => (
            <Grid item xs={12} key={cert.certificate.id}>
              <Card>
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
                    <Box display="flex" alignItems="center" gap={1}>
                      <SecurityIcon />
                      <Typography variant="h6">{cert.certificate.domain}</Typography>
                    </Box>
                    <Box display="flex" alignItems="center" gap={1}>
                      <Chip
                        label={cert.certificate.status}
                        color={cert.certificate.status === 'active' ? 'success' : 'warning'}
                        size="small"
                        icon={getStatusIcon(cert.certificate.status)}
                      />
                      {cert.certificate.needs_renewal && (
                        <Button
                          size="small"
                          variant="outlined"
                          color="warning"
                          onClick={() => handleRenewCertificate(cert.certificate.id)}
                        >
                          Renew
                        </Button>
                      )}
                    </Box>
                  </Box>

                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6} md={3}>
                      <Typography variant="subtitle2" gutterBottom>
                        Certificate Authority
                      </Typography>
                      <Typography variant="body2" color="textSecondary">
                        {cert.certificate.authority}
                      </Typography>
                    </Grid>

                    <Grid item xs={12} sm={6} md={3}>
                      <Typography variant="subtitle2" gutterBottom>
                        Issued
                      </Typography>
                      <Typography variant="body2" color="textSecondary">
                        {cert.certificate.issued_at 
                          ? new Date(cert.certificate.issued_at).toLocaleDateString()
                          : 'N/A'
                        }
                      </Typography>
                    </Grid>

                    <Grid item xs={12} sm={6} md={3}>
                      <Typography variant="subtitle2" gutterBottom>
                        Expires
                      </Typography>
                      <Box>
                        <Typography variant="body2" color="textSecondary">
                          {cert.certificate.expires_at 
                            ? new Date(cert.certificate.expires_at).toLocaleDateString()
                            : 'N/A'
                          }
                        </Typography>
                        {cert.certificate.days_until_expiry !== undefined && (
                          <Chip
                            label={`${cert.certificate.days_until_expiry} days left`}
                            size="small"
                            color={getExpiryColor(cert.certificate.days_until_expiry) as any}
                            sx={{ mt: 0.5 }}
                          />
                        )}
                      </Box>
                    </Grid>

                    <Grid item xs={12} sm={6} md={3}>
                      <Typography variant="subtitle2" gutterBottom>
                        Auto-Renewal
                      </Typography>
                      <Chip
                        label={cert.certificate.auto_renew ? 'Enabled' : 'Disabled'}
                        color={cert.certificate.auto_renew ? 'success' : 'default'}
                        size="small"
                      />
                    </Grid>
                  </Grid>

                  {cert.metadata.subject_alternative_names && cert.metadata.subject_alternative_names.length > 0 && (
                    <Box mt={2}>
                      <Typography variant="subtitle2" gutterBottom>
                        Subject Alternative Names
                      </Typography>
                      <Box display="flex" flexWrap="wrap" gap={0.5}>
                        {cert.metadata.subject_alternative_names.map((san, index) => (
                          <Chip key={index} label={san} size="small" variant="outlined" />
                        ))}
                      </Box>
                    </Box>
                  )}

                  {cert.validation && !cert.validation.valid && (
                    <Alert severity="warning" sx={{ mt: 2 }}>
                      Certificate validation failed: {cert.validation.error}
                    </Alert>
                  )}
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  );
};