import React, { useState, useEffect } from 'react';
import {
  Box,
  Tabs,
  Tab,
  Paper,
  Typography,
  Divider,
} from '@mui/material';
import {
  Storage as DatabaseIcon,
  AccountTree as BranchIcon,
  History as MigrationIcon,
} from '@mui/icons-material';
import { DatabaseManager } from './DatabaseManager';
import { BranchVisualizer } from './BranchVisualizer';
import { MigrationManager } from './MigrationManager';
import { api } from '../../services/api';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

interface DatabaseBranch {
  id: string;
  instance_id: string;
  name: string;
  parent_branch?: string;
  is_default: boolean;
  created_at: string;
  created_by: string;
  use_cow: boolean;
  storage_used_gb: number;
  schema_version: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`database-tabpanel-${index}`}
      aria-labelledby={`database-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

interface DatabasePanelProps {
  projectId: string;
}

export const DatabasePanel: React.FC<DatabasePanelProps> = ({ projectId }) => {
  const [tabValue, setTabValue] = useState(0);
  const [selectedDatabaseId, setSelectedDatabaseId] = useState<string | null>(null);
  const [selectedBranch, setSelectedBranch] = useState<string>('main');
  const [branches, setBranches] = useState<DatabaseBranch[]>([]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleDatabaseCreated = (database: any) => {
    setSelectedDatabaseId(database.id);
    setSelectedBranch('main');
    // Switch to branches tab to show the new database
    setTabValue(1);
  };

  const handleDatabaseSelected = (databaseId: string) => {
    setSelectedDatabaseId(databaseId);
    fetchBranches(databaseId);
  };

  const fetchBranches = async (databaseId: string) => {
    try {
      const response = await api.get(`/api/v1/databases/${databaseId}/branches`);
      setBranches(response.data);
    } catch (error) {
      console.error('Failed to fetch branches:', error);
    }
  };

  const handleBranchSwitch = (branchName: string) => {
    setSelectedBranch(branchName);
    // Switch to migrations tab to show branch-specific migrations
    setTabValue(2);
  };

  const handleBranchesUpdate = () => {
    if (selectedDatabaseId) {
      fetchBranches(selectedDatabaseId);
    }
  };

  return (
    <Paper elevation={0}>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="database management tabs">
          <Tab
            icon={<DatabaseIcon />}
            label="Databases"
            iconPosition="start"
            id="database-tab-0"
            aria-controls="database-tabpanel-0"
          />
          <Tab
            icon={<BranchIcon />}
            label="Branches"
            iconPosition="start"
            id="database-tab-1"
            aria-controls="database-tabpanel-1"
            disabled={!selectedDatabaseId}
          />
          <Tab
            icon={<MigrationIcon />}
            label="Migrations"
            iconPosition="start"
            id="database-tab-2"
            aria-controls="database-tabpanel-2"
            disabled={!selectedDatabaseId}
          />
        </Tabs>
      </Box>

      <TabPanel value={tabValue} index={0}>
        <DatabaseManager
          projectId={projectId}
          onDatabaseCreated={handleDatabaseCreated}
        />
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        {selectedDatabaseId ? (
          <Box>
            <Typography variant="body2" color="textSecondary" gutterBottom>
              Current Branch: <strong>{selectedBranch}</strong>
            </Typography>
            <Divider sx={{ mb: 2 }} />
            <BranchVisualizer
              databaseId={selectedDatabaseId}
              branches={branches}
              onBranchCreate={(branch) => {
                setSelectedBranch(branch);
                handleBranchesUpdate();
              }}
              onBranchSwitch={handleBranchSwitch}
              onBranchesUpdate={handleBranchesUpdate}
            />
          </Box>
        ) : (
          <Box textAlign="center" py={4}>
            <Typography variant="h6" color="textSecondary">
              Select a database from the Databases tab to manage branches
            </Typography>
          </Box>
        )}
      </TabPanel>

      <TabPanel value={tabValue} index={2}>
        {selectedDatabaseId && selectedBranch ? (
          <MigrationManager
            databaseId={selectedDatabaseId}
            currentBranch={selectedBranch}
          />
        ) : (
          <Box textAlign="center" py={4}>
            <Typography variant="h6" color="textSecondary">
              Select a database and branch to manage migrations
            </Typography>
          </Box>
        )}
      </TabPanel>
    </Paper>
  );
};