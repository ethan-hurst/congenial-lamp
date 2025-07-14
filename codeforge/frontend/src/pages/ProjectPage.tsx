/**
 * Project Page Component - Shows project details and overview
 */
import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Box, Tabs, Tab, Paper, Container, Typography } from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Storage as DatabaseIcon,
  Settings as SettingsIcon,
  Psychology as AIIcon,
  CloudQueue as InfrastructureIcon,
} from '@mui/icons-material';

import { Navbar } from '../components/Layout/Navbar';
import { DatabasePanel } from '../components/Database';
import { AgentPanel } from '../components/AI/AgentPanel';
import { InfrastructurePanel } from '../components/Infrastructure';
import { api } from '../services/api';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`project-tabpanel-${index}`}
      aria-labelledby={`project-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

export const ProjectPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const [tabValue, setTabValue] = useState(0);

  const { data: project, isLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => api.getProject(projectId!),
    enabled: !!projectId,
  });

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <Navbar />
        <div className="flex items-center justify-center h-96">
          <div className="text-gray-600 dark:text-gray-400">Loading project...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navbar />
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          {project?.name || 'Project'}
        </Typography>
        
        <Paper sx={{ mt: 3 }}>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs value={tabValue} onChange={handleTabChange} aria-label="project tabs">
              <Tab
                icon={<DashboardIcon />}
                label="Overview"
                iconPosition="start"
                id="project-tab-0"
                aria-controls="project-tabpanel-0"
              />
              <Tab
                icon={<DatabaseIcon />}
                label="Databases"
                iconPosition="start"
                id="project-tab-1"
                aria-controls="project-tabpanel-1"
              />
              <Tab
                icon={<AIIcon />}
                label="AI Agents"
                iconPosition="start"
                id="project-tab-2"
                aria-controls="project-tabpanel-2"
              />
              <Tab
                icon={<InfrastructureIcon />}
                label="Infrastructure"
                iconPosition="start"
                id="project-tab-3"
                aria-controls="project-tabpanel-3"
              />
              <Tab
                icon={<SettingsIcon />}
                label="Settings"
                iconPosition="start"
                id="project-tab-4"
                aria-controls="project-tabpanel-4"
              />
            </Tabs>
          </Box>

          <TabPanel value={tabValue} index={0}>
            <Box p={3}>
              <Typography variant="h6" gutterBottom>Project Overview</Typography>
              <Typography variant="body1" color="textSecondary">
                Project details and statistics will be displayed here.
              </Typography>
            </Box>
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            {projectId && <DatabasePanel projectId={projectId} />}
          </TabPanel>

          <TabPanel value={tabValue} index={2}>
            {projectId && <AgentPanel projectId={projectId} />}
          </TabPanel>

          <TabPanel value={tabValue} index={3}>
            {projectId && <InfrastructurePanel projectId={projectId} />}
          </TabPanel>

          <TabPanel value={tabValue} index={4}>
            <Box p={3}>
              <Typography variant="h6" gutterBottom>Project Settings</Typography>
              <Typography variant="body1" color="textSecondary">
                Project configuration and settings will go here.
              </Typography>
            </Box>
          </TabPanel>
        </Paper>
      </Container>
    </div>
  );
};