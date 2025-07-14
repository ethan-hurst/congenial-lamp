import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  LinearProgress,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Dialog,
  DialogTitle,
  DialogContent,
  CircularProgress,
  Alert,
  Tabs,
  Tab,
  Tooltip,
} from '@mui/material';
import {
  BuildCircle as BuildIcon,
  BugReport as BugIcon,
  Code as CodeIcon,
  Description as DocsIcon,
  RateReview as ReviewIcon,
  Science as TestIcon,
  PlayArrow as RunIcon,
  Stop as StopIcon,
  Refresh as RefreshIcon,
  Timeline as TimelineIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Schedule as PendingIcon,
} from '@mui/icons-material';
import { api } from '../../services/api';
import { FeatureBuilder } from './FeatureBuilder';
import { TestCoverageVisualizer } from './TestCoverageVisualizer';

interface Agent {
  type: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  capabilities: string[];
}

interface AgentTask {
  id: string;
  agent_type: string;
  title: string;
  status: string;
  progress: number;
  current_step?: string;
  created_at: string;
  completed_at?: string;
  error_message?: string;
  results?: any;
}

interface AgentPanelProps {
  projectId: string;
}

const agents: Agent[] = [
  {
    type: 'feature_builder',
    name: 'Feature Builder',
    description: 'Builds complete features from requirements',
    icon: <BuildIcon />,
    capabilities: ['API development', 'UI components', 'Database integration']
  },
  {
    type: 'test_writer',
    name: 'Test Writer',
    description: 'Generates comprehensive test suites',
    icon: <TestIcon />,
    capabilities: ['Unit tests', 'Integration tests', 'Edge cases']
  },
  {
    type: 'refactor',
    name: 'Refactor Agent',
    description: 'Improves code quality and structure',
    icon: <CodeIcon />,
    capabilities: ['Code optimization', 'Pattern improvements', 'Clean code']
  },
  {
    type: 'bug_fixer',
    name: 'Bug Fixer',
    description: 'Identifies and fixes bugs',
    icon: <BugIcon />,
    capabilities: ['Root cause analysis', 'Fix generation', 'Regression prevention']
  },
  {
    type: 'code_reviewer',
    name: 'Code Reviewer',
    description: 'Provides detailed code reviews',
    icon: <ReviewIcon />,
    capabilities: ['Security checks', 'Best practices', 'Performance analysis']
  },
  {
    type: 'documentation',
    name: 'Documentation Agent',
    description: 'Generates and maintains documentation',
    icon: <DocsIcon />,
    capabilities: ['API docs', 'README files', 'Code comments']
  }
];

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

export const AgentPanel: React.FC<AgentPanelProps> = ({ projectId }) => {
  const [selectedTab, setSelectedTab] = useState(0);
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [loadingTasks, setLoadingTasks] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [showFeatureBuilder, setShowFeatureBuilder] = useState(false);
  const [selectedTask, setSelectedTask] = useState<AgentTask | null>(null);
  const [taskDetailsOpen, setTaskDetailsOpen] = useState(false);

  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, [projectId]);

  const fetchTasks = async () => {
    try {
      const response = await api.get(`/api/v1/ai/agents/tasks?project_id=${projectId}`);
      setTasks(response.data.tasks);
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
    } finally {
      setLoadingTasks(false);
    }
  };

  const handleAgentClick = (agent: Agent) => {
    setSelectedAgent(agent);
    if (agent.type === 'feature_builder') {
      setShowFeatureBuilder(true);
    }
  };

  const handleTaskClick = (task: AgentTask) => {
    setSelectedTask(task);
    setTaskDetailsOpen(true);
  };

  const handleCancelTask = async (taskId: string) => {
    try {
      await api.delete(`/api/v1/ai/agents/tasks/${taskId}`);
      fetchTasks();
    } catch (error) {
      console.error('Failed to cancel task:', error);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <SuccessIcon color="success" />;
      case 'failed':
        return <ErrorIcon color="error" />;
      case 'running':
        return <CircularProgress size={20} />;
      default:
        return <PendingIcon color="action" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'running':
        return 'primary';
      default:
        return 'default';
    }
  };

  const runningTasks = tasks.filter(t => t.status === 'running' || t.status === 'pending');
  const completedTasks = tasks.filter(t => t.status === 'completed' || t.status === 'failed');

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        AI Development Agents
      </Typography>

      <Paper sx={{ mb: 3 }}>
        <Tabs value={selectedTab} onChange={(e, v) => setSelectedTab(v)}>
          <Tab label="Agents" />
          <Tab label="Active Tasks" />
          <Tab label="History" />
          <Tab label="Test Coverage" />
        </Tabs>
      </Paper>

      <TabPanel value={selectedTab} index={0}>
        <Grid container spacing={3}>
          {agents.map((agent) => (
            <Grid item xs={12} sm={6} md={4} key={agent.type}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" mb={2}>
                    {agent.icon}
                    <Typography variant="h6" sx={{ ml: 1 }}>
                      {agent.name}
                    </Typography>
                  </Box>
                  <Typography variant="body2" color="textSecondary" paragraph>
                    {agent.description}
                  </Typography>
                  <Box>
                    {agent.capabilities.map((cap, i) => (
                      <Chip
                        key={i}
                        label={cap}
                        size="small"
                        sx={{ mr: 0.5, mb: 0.5 }}
                      />
                    ))}
                  </Box>
                </CardContent>
                <CardActions>
                  <Button
                    size="small"
                    startIcon={<RunIcon />}
                    onClick={() => handleAgentClick(agent)}
                  >
                    Use Agent
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      </TabPanel>

      <TabPanel value={selectedTab} index={1}>
        {loadingTasks ? (
          <Box display="flex" justifyContent="center" py={4}>
            <CircularProgress />
          </Box>
        ) : runningTasks.length === 0 ? (
          <Alert severity="info">No active tasks</Alert>
        ) : (
          <List>
            {runningTasks.map((task) => (
              <ListItem key={task.id} button onClick={() => handleTaskClick(task)}>
                <ListItemIcon>
                  {getStatusIcon(task.status)}
                </ListItemIcon>
                <ListItemText
                  primary={task.title}
                  secondary={
                    <Box>
                      <Typography variant="caption" display="block">
                        {task.agent_type} • {task.current_step || 'Processing...'}
                      </Typography>
                      {task.progress > 0 && (
                        <LinearProgress
                          variant="determinate"
                          value={task.progress * 100}
                          sx={{ mt: 1 }}
                        />
                      )}
                    </Box>
                  }
                />
                <ListItemSecondaryAction>
                  {task.status === 'running' && (
                    <IconButton
                      edge="end"
                      onClick={() => handleCancelTask(task.id)}
                    >
                      <StopIcon />
                    </IconButton>
                  )}
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        )}
      </TabPanel>

      <TabPanel value={selectedTab} index={2}>
        {completedTasks.length === 0 ? (
          <Alert severity="info">No completed tasks</Alert>
        ) : (
          <List>
            {completedTasks.map((task) => (
              <ListItem key={task.id} button onClick={() => handleTaskClick(task)}>
                <ListItemIcon>
                  {getStatusIcon(task.status)}
                </ListItemIcon>
                <ListItemText
                  primary={task.title}
                  secondary={
                    <Typography variant="caption">
                      {task.agent_type} • Completed {new Date(task.completed_at!).toLocaleString()}
                    </Typography>
                  }
                />
                <ListItemSecondaryAction>
                  <Chip
                    label={task.status}
                    color={getStatusColor(task.status) as any}
                    size="small"
                  />
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        )}
      </TabPanel>

      {/* Feature Builder Dialog */}
      {showFeatureBuilder && (
        <FeatureBuilder
          projectId={projectId}
          open={showFeatureBuilder}
          onClose={() => {
            setShowFeatureBuilder(false);
            setSelectedAgent(null);
            fetchTasks();
          }}
        />
      )}

      <TabPanel value={selectedTab} index={3}>
        <TestCoverageVisualizer projectId={projectId} />
      </TabPanel>

      {/* Task Details Dialog */}
      <Dialog
        open={taskDetailsOpen}
        onClose={() => setTaskDetailsOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Task Details
          <IconButton
            sx={{ position: 'absolute', right: 8, top: 8 }}
            onClick={() => setTaskDetailsOpen(false)}
          >
            ×
          </IconButton>
        </DialogTitle>
        <DialogContent>
          {selectedTask && (
            <Box>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="caption" color="textSecondary">
                    Task ID
                  </Typography>
                  <Typography variant="body2">{selectedTask.id}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="caption" color="textSecondary">
                    Agent
                  </Typography>
                  <Typography variant="body2">{selectedTask.agent_type}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="caption" color="textSecondary">
                    Status
                  </Typography>
                  <Box display="flex" alignItems="center" gap={1}>
                    {getStatusIcon(selectedTask.status)}
                    <Typography variant="body2">{selectedTask.status}</Typography>
                  </Box>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="caption" color="textSecondary">
                    Progress
                  </Typography>
                  <Box display="flex" alignItems="center" gap={1}>
                    <LinearProgress
                      variant="determinate"
                      value={selectedTask.progress * 100}
                      sx={{ flex: 1 }}
                    />
                    <Typography variant="body2">
                      {Math.round(selectedTask.progress * 100)}%
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12}>
                  <Typography variant="caption" color="textSecondary">
                    Current Step
                  </Typography>
                  <Typography variant="body2">
                    {selectedTask.current_step || 'N/A'}
                  </Typography>
                </Grid>
                {selectedTask.error_message && (
                  <Grid item xs={12}>
                    <Alert severity="error">{selectedTask.error_message}</Alert>
                  </Grid>
                )}
                {selectedTask.results && (
                  <Grid item xs={12}>
                    <Typography variant="caption" color="textSecondary">
                      Results
                    </Typography>
                    <Paper variant="outlined" sx={{ p: 2, mt: 1 }}>
                      <pre style={{ margin: 0, fontSize: '0.875rem' }}>
                        {JSON.stringify(selectedTask.results, null, 2)}
                      </pre>
                    </Paper>
                  </Grid>
                )}
              </Grid>
            </Box>
          )}
        </DialogContent>
      </Dialog>
    </Box>
  );
};