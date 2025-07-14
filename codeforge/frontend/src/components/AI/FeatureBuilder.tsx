import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Paper,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Checkbox,
  IconButton,
  Grid,
} from '@mui/material';
import {
  Code as CodeIcon,
  Storage as DatabaseIcon,
  Api as ApiIcon,
  Web as UIIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { api } from '../../services/api';

interface Constraint {
  type: string;
  value: any;
  description: string;
}

interface FeatureBuilderProps {
  projectId: string;
  open: boolean;
  onClose: () => void;
}

const techStackOptions = {
  languages: ['python', 'javascript', 'typescript', 'go', 'java'],
  frameworks: {
    python: ['fastapi', 'django', 'flask'],
    javascript: ['express', 'nextjs'],
    typescript: ['nestjs', 'express'],
    go: ['gin', 'echo', 'fiber'],
    java: ['spring', 'springboot'],
  },
};

const featureTemplates = [
  {
    name: 'REST API',
    icon: <ApiIcon />,
    description: 'Create a RESTful API with CRUD operations',
    requirements: 'Create a REST API with endpoints for creating, reading, updating, and deleting resources.',
  },
  {
    name: 'User Authentication',
    icon: <CodeIcon />,
    description: 'Implement user registration and login',
    requirements: 'Implement user authentication with registration, login, JWT tokens, and password hashing.',
  },
  {
    name: 'Database Integration',
    icon: <DatabaseIcon />,
    description: 'Set up database models and queries',
    requirements: 'Create database models with proper relationships, migrations, and query methods.',
  },
  {
    name: 'UI Component',
    icon: <UIIcon />,
    description: 'Build a React component with state management',
    requirements: 'Create a React component with proper state management, props validation, and styling.',
  },
];

export const FeatureBuilder: React.FC<FeatureBuilderProps> = ({
  projectId,
  open,
  onClose,
}) => {
  const [activeStep, setActiveStep] = useState(0);
  const [requirements, setRequirements] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState<any>(null);
  const [language, setLanguage] = useState('python');
  const [framework, setFramework] = useState('fastapi');
  const [libraries, setLibraries] = useState<string[]>([]);
  const [newLibrary, setNewLibrary] = useState('');
  const [constraints, setConstraints] = useState<Constraint[]>([]);
  const [priority, setPriority] = useState('medium');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleTemplateSelect = (template: any) => {
    setSelectedTemplate(template);
    setRequirements(template.requirements);
    setActiveStep(1);
  };

  const handleNext = () => {
    setActiveStep((prev) => prev + 1);
  };

  const handleBack = () => {
    setActiveStep((prev) => prev - 1);
  };

  const handleAddLibrary = () => {
    if (newLibrary && !libraries.includes(newLibrary)) {
      setLibraries([...libraries, newLibrary]);
      setNewLibrary('');
    }
  };

  const handleRemoveLibrary = (lib: string) => {
    setLibraries(libraries.filter(l => l !== lib));
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError('');

    try {
      const techStack = {
        language,
        framework,
        libraries,
      };

      const requestData = {
        requirements,
        constraints: [
          {
            type: 'tech_stack',
            value: techStack,
            description: 'Technology stack for implementation',
          },
          ...constraints,
        ],
        tech_stack: techStack,
        priority,
      };

      const response = await api.post(
        `/api/v1/ai/agents/feature?project_id=${projectId}`,
        requestData
      );

      if (response.data.task_id) {
        onClose();
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create feature task');
    } finally {
      setLoading(false);
    }
  };

  const steps = [
    'Choose Template',
    'Define Requirements',
    'Configure Technology',
    'Review & Submit',
  ];

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Feature Builder</DialogTitle>
      <DialogContent>
        <Stepper activeStep={activeStep} orientation="vertical">
          <Step>
            <StepLabel>Choose Template (Optional)</StepLabel>
            <StepContent>
              <Typography variant="body2" color="textSecondary" paragraph>
                Select a template to get started quickly, or skip to define custom requirements.
              </Typography>
              <Grid container spacing={2}>
                {featureTemplates.map((template) => (
                  <Grid item xs={12} sm={6} key={template.name}>
                    <Paper
                      variant="outlined"
                      sx={{
                        p: 2,
                        cursor: 'pointer',
                        '&:hover': { bgcolor: 'action.hover' },
                        bgcolor: selectedTemplate?.name === template.name ? 'action.selected' : 'transparent',
                      }}
                      onClick={() => handleTemplateSelect(template)}
                    >
                      <Box display="flex" alignItems="center" mb={1}>
                        {template.icon}
                        <Typography variant="subtitle2" sx={{ ml: 1 }}>
                          {template.name}
                        </Typography>
                      </Box>
                      <Typography variant="caption" color="textSecondary">
                        {template.description}
                      </Typography>
                    </Paper>
                  </Grid>
                ))}
              </Grid>
              <Box mt={2}>
                <Button onClick={() => setActiveStep(1)} variant="outlined">
                  Skip Template
                </Button>
              </Box>
            </StepContent>
          </Step>

          <Step>
            <StepLabel>Define Requirements</StepLabel>
            <StepContent>
              <TextField
                fullWidth
                multiline
                rows={6}
                label="Feature Requirements"
                value={requirements}
                onChange={(e) => setRequirements(e.target.value)}
                placeholder="Describe the feature you want to build in detail..."
                helperText="Be specific about functionality, inputs/outputs, and business logic"
                margin="normal"
              />
              <Box mt={2}>
                <Button onClick={handleBack}>Back</Button>
                <Button
                  onClick={handleNext}
                  variant="contained"
                  disabled={requirements.length < 10}
                  sx={{ ml: 1 }}
                >
                  Next
                </Button>
              </Box>
            </StepContent>
          </Step>

          <Step>
            <StepLabel>Configure Technology</StepLabel>
            <StepContent>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth margin="normal">
                    <InputLabel>Language</InputLabel>
                    <Select
                      value={language}
                      onChange={(e) => {
                        setLanguage(e.target.value);
                        setFramework('');
                      }}
                      label="Language"
                    >
                      {techStackOptions.languages.map((lang) => (
                        <MenuItem key={lang} value={lang}>
                          {lang}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth margin="normal">
                    <InputLabel>Framework</InputLabel>
                    <Select
                      value={framework}
                      onChange={(e) => setFramework(e.target.value)}
                      label="Framework"
                      disabled={!language}
                    >
                      {(techStackOptions.frameworks[language as keyof typeof techStackOptions.frameworks] || []).map(
                        (fw) => (
                          <MenuItem key={fw} value={fw}>
                            {fw}
                          </MenuItem>
                        )
                      )}
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>

              <Box mt={2}>
                <Typography variant="subtitle2" gutterBottom>
                  Additional Libraries
                </Typography>
                <Box display="flex" gap={1} mb={1}>
                  <TextField
                    size="small"
                    placeholder="Library name"
                    value={newLibrary}
                    onChange={(e) => setNewLibrary(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleAddLibrary()}
                  />
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={handleAddLibrary}
                    startIcon={<AddIcon />}
                  >
                    Add
                  </Button>
                </Box>
                <Box display="flex" flexWrap="wrap" gap={1}>
                  {libraries.map((lib) => (
                    <Chip
                      key={lib}
                      label={lib}
                      onDelete={() => handleRemoveLibrary(lib)}
                      size="small"
                    />
                  ))}
                </Box>
              </Box>

              <FormControl fullWidth margin="normal">
                <InputLabel>Priority</InputLabel>
                <Select
                  value={priority}
                  onChange={(e) => setPriority(e.target.value)}
                  label="Priority"
                >
                  <MenuItem value="low">Low</MenuItem>
                  <MenuItem value="medium">Medium</MenuItem>
                  <MenuItem value="high">High</MenuItem>
                  <MenuItem value="critical">Critical</MenuItem>
                </Select>
              </FormControl>

              <Box mt={2}>
                <Button onClick={handleBack}>Back</Button>
                <Button onClick={handleNext} variant="contained" sx={{ ml: 1 }}>
                  Next
                </Button>
              </Box>
            </StepContent>
          </Step>

          <Step>
            <StepLabel>Review & Submit</StepLabel>
            <StepContent>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Requirements
                </Typography>
                <Typography variant="body2" paragraph>
                  {requirements}
                </Typography>

                <Typography variant="subtitle2" gutterBottom>
                  Technology Stack
                </Typography>
                <Box display="flex" gap={1} mb={2}>
                  <Chip label={language} color="primary" size="small" />
                  <Chip label={framework} color="primary" size="small" />
                  {libraries.map((lib) => (
                    <Chip key={lib} label={lib} size="small" />
                  ))}
                </Box>

                <Typography variant="subtitle2" gutterBottom>
                  Priority
                </Typography>
                <Chip
                  label={priority}
                  color={priority === 'critical' ? 'error' : priority === 'high' ? 'warning' : 'default'}
                  size="small"
                />
              </Paper>

              {error && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {error}
                </Alert>
              )}

              <Box mt={2}>
                <Button onClick={handleBack}>Back</Button>
                <Button
                  onClick={handleSubmit}
                  variant="contained"
                  sx={{ ml: 1 }}
                  disabled={loading}
                >
                  {loading ? 'Creating...' : 'Build Feature'}
                </Button>
              </Box>
            </StepContent>
          </Step>
        </Stepper>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
      </DialogActions>
    </Dialog>
  );
};