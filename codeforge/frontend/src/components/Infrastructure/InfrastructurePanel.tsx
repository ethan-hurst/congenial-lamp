import React, { useState } from 'react';
import {
  Box,
  Paper,
  Tabs,
  Tab,
  Typography,
} from '@mui/material';
import {
  Domain as DomainIcon,
  Security as SecurityIcon,
  Speed as CDNIcon,
  AccountTree as LoadBalancerIcon,
  Public as EdgeIcon,
} from '@mui/icons-material';

import { DomainManager } from './DomainManager';
import { SSLCertificates } from './SSLCertificates';

interface InfrastructurePanelProps {
  projectId: string;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div hidden={value !== index} {...other}>
      {value === index && <Box sx={{ py: 2 }}>{children}</Box>}
    </div>
  );
}

// Placeholder components for remaining infrastructure features
const CDNConfig: React.FC<{ projectId: string }> = ({ projectId }) => (
  <Box sx={{ textAlign: 'center', py: 6 }}>
    <CDNIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
    <Typography variant="h6" gutterBottom>
      CDN Configuration
    </Typography>
    <Typography variant="body2" color="textSecondary">
      Global content delivery network configuration will be available here.
    </Typography>
  </Box>
);

const LoadBalancer: React.FC<{ projectId: string }> = ({ projectId }) => (
  <Box sx={{ textAlign: 'center', py: 6 }}>
    <LoadBalancerIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
    <Typography variant="h6" gutterBottom>
      Load Balancers
    </Typography>
    <Typography variant="body2" color="textSecondary">
      Traffic distribution and load balancing configuration will be available here.
    </Typography>
  </Box>
);

const EdgeDeployments: React.FC<{ projectId: string }> = ({ projectId }) => (
  <Box sx={{ textAlign: 'center', py: 6 }}>
    <EdgeIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
    <Typography variant="h6" gutterBottom>
      Edge Deployments
    </Typography>
    <Typography variant="body2" color="textSecondary">
      Global edge deployment management will be available here.
    </Typography>
  </Box>
);

export const InfrastructurePanel: React.FC<InfrastructurePanelProps> = ({ projectId }) => {
  const [selectedTab, setSelectedTab] = useState(0);

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Infrastructure Management
      </Typography>
      <Typography variant="body1" color="textSecondary" paragraph>
        Manage your domains, SSL certificates, CDN, load balancers, and global edge deployments.
      </Typography>

      <Paper sx={{ mt: 3 }}>
        <Tabs value={selectedTab} onChange={(e, v) => setSelectedTab(v)}>
          <Tab
            icon={<DomainIcon />}
            label="Domains"
            iconPosition="start"
          />
          <Tab
            icon={<SecurityIcon />}
            label="SSL Certificates"
            iconPosition="start"
          />
          <Tab
            icon={<CDNIcon />}
            label="CDN"
            iconPosition="start"
          />
          <Tab
            icon={<LoadBalancerIcon />}
            label="Load Balancers"
            iconPosition="start"
          />
          <Tab
            icon={<EdgeIcon />}
            label="Edge Deployments"
            iconPosition="start"
          />
        </Tabs>
      </Paper>

      <TabPanel value={selectedTab} index={0}>
        <DomainManager projectId={projectId} />
      </TabPanel>

      <TabPanel value={selectedTab} index={1}>
        <SSLCertificates projectId={projectId} />
      </TabPanel>

      <TabPanel value={selectedTab} index={2}>
        <CDNConfig projectId={projectId} />
      </TabPanel>

      <TabPanel value={selectedTab} index={3}>
        <LoadBalancer projectId={projectId} />
      </TabPanel>

      <TabPanel value={selectedTab} index={4}>
        <EdgeDeployments projectId={projectId} />
      </TabPanel>
    </Box>
  );
};