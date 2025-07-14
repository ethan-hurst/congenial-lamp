import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  LinearProgress,
  Button,
  Card,
  CardContent,
  Grid,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Chip,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Tooltip,
  Tabs,
  Tab,
} from '@mui/material';
import {
  CheckCircle as CoveredIcon,
  Warning as UncoveredIcon,
  Error as CriticalIcon,
  Functions as FunctionIcon,
  Code as FileIcon,
  PlayArrow as RunIcon,
  Refresh as RefreshIcon,
  Assessment as ReportIcon,
  Build as GenerateIcon,
  TrendingUp as TrendIcon,
} from '@mui/icons-material';
import { api } from '../../services/api';

interface FileCoverage {
  path: string;
  coverage: number;
  lines_covered: number;
  lines_total: number;
  functions_covered: number;
  functions_total: number;
  branches_covered: number;
  branches_total: number;
  uncovered_lines: number[];
}

interface FunctionCoverage {
  name: string;
  file: string;
  line_start: number;
  line_end: number;
  coverage: number;
  complexity: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
}

interface CoverageReport {
  overall_coverage: number;
  line_coverage: number;
  function_coverage: number;
  branch_coverage: number;
  files: FileCoverage[];
  uncovered_functions: FunctionCoverage[];
  last_updated: string;
}

interface TestCoverageVisualizerProps {
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

export const TestCoverageVisualizer: React.FC<TestCoverageVisualizerProps> = ({
  projectId,
}) => {
  const [selectedTab, setSelectedTab] = useState(0);
  const [coverageReport, setCoverageReport] = useState<CoverageReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState<FileCoverage | null>(null);
  const [showGenerateDialog, setShowGenerateDialog] = useState(false);
  const [generateTarget, setGenerateTarget] = useState<any>(null);
  const [testFramework, setTestFramework] = useState('pytest');
  const [testTypes, setTestTypes] = useState(['unit', 'edge_cases']);

  useEffect(() => {
    fetchCoverageReport();
  }, [projectId]);

  const fetchCoverageReport = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/api/v1/ai/coverage?project_id=${projectId}`);
      setCoverageReport(response.data);
    } catch (error) {
      console.error('Failed to fetch coverage report:', error);
    } finally {
      setLoading(false);
    }
  };

  const getCoverageColor = (coverage: number) => {
    if (coverage >= 80) return 'success';
    if (coverage >= 60) return 'warning';
    return 'error';
  };

  const getCoverageIcon = (coverage: number) => {
    if (coverage >= 80) return <CoveredIcon color="success" />;
    if (coverage >= 60) return <UncoveredIcon color="warning" />;
    return <CriticalIcon color="error" />;
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'critical':
        return 'error';
      case 'high':
        return 'warning';
      case 'medium':
        return 'info';
      default:
        return 'default';
    }
  };

  const handleGenerateTests = (target: any) => {
    setGenerateTarget(target);
    setShowGenerateDialog(true);
  };

  const submitGenerateTests = async () => {
    try {
      const request = {
        file_path: generateTarget.file || generateTarget.path,
        coverage_target: 0.9,
        test_types: testTypes,
        test_framework: testFramework,
      };

      await api.post(`/api/v1/ai/agents/test?project_id=${projectId}`, request);
      setShowGenerateDialog(false);
      setGenerateTarget(null);
    } catch (error) {
      console.error('Failed to generate tests:', error);
    }
  };

  const renderCoverageHeatmap = (file: FileCoverage) => {
    const heatmapData = [];
    const linesPerRow = 50;
    
    for (let i = 0; i < file.lines_total; i += linesPerRow) {
      const row = [];
      for (let j = 0; j < linesPerRow && i + j < file.lines_total; j++) {
        const lineNum = i + j + 1;
        const isCovered = !file.uncovered_lines.includes(lineNum);
        row.push({ lineNum, isCovered });
      }
      heatmapData.push(row);
    }

    return (
      <Box sx={{ p: 2 }}>
        <Typography variant="subtitle2" gutterBottom>
          Coverage Heatmap: {file.path}
        </Typography>
        <Box sx={{ overflowX: 'auto' }}>
          {heatmapData.map((row, rowIndex) => (
            <Box key={rowIndex} display="flex" gap={0.25} mb={0.25}>
              {row.map((cell) => (
                <Tooltip key={cell.lineNum} title={`Line ${cell.lineNum}`}>
                  <Box
                    sx={{
                      width: 10,
                      height: 10,
                      bgcolor: cell.isCovered ? 'success.main' : 'error.main',
                      cursor: 'pointer',
                      '&:hover': { opacity: 0.8 },
                    }}
                  />
                </Tooltip>
              ))}
            </Box>
          ))}
        </Box>
        <Box display="flex" gap={2} mt={2}>
          <Chip
            icon={<CoveredIcon />}
            label="Covered"
            color="success"
            size="small"
          />
          <Chip
            icon={<UncoveredIcon />}
            label="Uncovered"
            color="error"
            size="small"
          />
        </Box>
      </Box>
    );
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" py={4}>
        <CircularProgress />
      </Box>
    );
  }

  if (!coverageReport) {
    return (
      <Alert severity="info">
        No coverage report available. Run tests to generate coverage data.
      </Alert>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5">Test Coverage Analysis</Typography>
        <Box display="flex" gap={1}>
          <Button
            startIcon={<RefreshIcon />}
            onClick={fetchCoverageReport}
            variant="outlined"
          >
            Refresh
          </Button>
          <Button
            startIcon={<ReportIcon />}
            variant="outlined"
          >
            Export Report
          </Button>
        </Box>
      </Box>

      {/* Overall Coverage Summary */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="textSecondary">
                Overall Coverage
              </Typography>
              <Box display="flex" alignItems="center" gap={1} mt={1}>
                <Typography variant="h4">
                  {Math.round(coverageReport.overall_coverage)}%
                </Typography>
                {getCoverageIcon(coverageReport.overall_coverage)}
              </Box>
              <LinearProgress
                variant="determinate"
                value={coverageReport.overall_coverage}
                color={getCoverageColor(coverageReport.overall_coverage) as any}
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="textSecondary">
                Line Coverage
              </Typography>
              <Box display="flex" alignItems="center" gap={1} mt={1}>
                <Typography variant="h4">
                  {Math.round(coverageReport.line_coverage)}%
                </Typography>
                <TrendIcon color="primary" />
              </Box>
              <LinearProgress
                variant="determinate"
                value={coverageReport.line_coverage}
                color={getCoverageColor(coverageReport.line_coverage) as any}
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="textSecondary">
                Function Coverage
              </Typography>
              <Box display="flex" alignItems="center" gap={1} mt={1}>
                <Typography variant="h4">
                  {Math.round(coverageReport.function_coverage)}%
                </Typography>
                <FunctionIcon color="primary" />
              </Box>
              <LinearProgress
                variant="determinate"
                value={coverageReport.function_coverage}
                color={getCoverageColor(coverageReport.function_coverage) as any}
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="textSecondary">
                Branch Coverage
              </Typography>
              <Box display="flex" alignItems="center" gap={1} mt={1}>
                <Typography variant="h4">
                  {Math.round(coverageReport.branch_coverage)}%
                </Typography>
                <CodeIcon color="primary" />
              </Box>
              <LinearProgress
                variant="determinate"
                value={coverageReport.branch_coverage}
                color={getCoverageColor(coverageReport.branch_coverage) as any}
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabs for different views */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={selectedTab} onChange={(e, v) => setSelectedTab(v)}>
          <Tab label="File Coverage" />
          <Tab label="Uncovered Functions" />
          <Tab label="Coverage Heatmap" />
        </Tabs>
      </Paper>

      <TabPanel value={selectedTab} index={0}>
        <List>
          {coverageReport.files.map((file) => (
            <ListItem
              key={file.path}
              button
              onClick={() => setSelectedFile(file)}
            >
              <ListItemIcon>
                {getCoverageIcon(file.coverage)}
              </ListItemIcon>
              <ListItemText
                primary={file.path}
                secondary={
                  <Box display="flex" gap={2}>
                    <Typography variant="caption">
                      Coverage: {Math.round(file.coverage)}%
                    </Typography>
                    <Typography variant="caption">
                      Lines: {file.lines_covered}/{file.lines_total}
                    </Typography>
                    <Typography variant="caption">
                      Functions: {file.functions_covered}/{file.functions_total}
                    </Typography>
                  </Box>
                }
              />
              <Box display="flex" alignItems="center" gap={1}>
                <LinearProgress
                  variant="determinate"
                  value={file.coverage}
                  sx={{ width: 100 }}
                  color={getCoverageColor(file.coverage) as any}
                />
                <IconButton
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleGenerateTests(file);
                  }}
                >
                  <GenerateIcon />
                </IconButton>
              </Box>
            </ListItem>
          ))}
        </List>
      </TabPanel>

      <TabPanel value={selectedTab} index={1}>
        <List>
          {coverageReport.uncovered_functions.map((func, index) => (
            <ListItem key={index}>
              <ListItemIcon>
                <FunctionIcon />
              </ListItemIcon>
              <ListItemText
                primary={func.name}
                secondary={
                  <Box>
                    <Typography variant="caption" display="block">
                      {func.file}:{func.line_start}-{func.line_end}
                    </Typography>
                    <Box display="flex" gap={1} mt={0.5}>
                      <Chip
                        label={`Coverage: ${Math.round(func.coverage)}%`}
                        size="small"
                        color={getCoverageColor(func.coverage) as any}
                      />
                      <Chip
                        label={`Complexity: ${func.complexity}`}
                        size="small"
                      />
                      <Chip
                        label={func.risk_level}
                        size="small"
                        color={getRiskColor(func.risk_level) as any}
                      />
                    </Box>
                  </Box>
                }
              />
              <Button
                size="small"
                startIcon={<GenerateIcon />}
                onClick={() => handleGenerateTests(func)}
              >
                Generate Tests
              </Button>
            </ListItem>
          ))}
        </List>
      </TabPanel>

      <TabPanel value={selectedTab} index={2}>
        {selectedFile ? (
          renderCoverageHeatmap(selectedFile)
        ) : (
          <Alert severity="info">
            Select a file from the File Coverage tab to view its heatmap
          </Alert>
        )}
      </TabPanel>

      {/* Generate Tests Dialog */}
      <Dialog
        open={showGenerateDialog}
        onClose={() => setShowGenerateDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Generate Tests</DialogTitle>
        <DialogContent>
          <Box py={2}>
            <Typography variant="body2" paragraph>
              Generate tests for: {generateTarget?.name || generateTarget?.path}
            </Typography>

            <FormControl fullWidth margin="normal">
              <InputLabel>Test Framework</InputLabel>
              <Select
                value={testFramework}
                onChange={(e) => setTestFramework(e.target.value)}
                label="Test Framework"
              >
                <MenuItem value="pytest">pytest</MenuItem>
                <MenuItem value="jest">Jest</MenuItem>
                <MenuItem value="mocha">Mocha</MenuItem>
                <MenuItem value="junit">JUnit</MenuItem>
              </Select>
            </FormControl>

            <Box mt={2}>
              <Typography variant="subtitle2" gutterBottom>
                Test Types
              </Typography>
              <Grid container spacing={1}>
                {['unit', 'integration', 'edge_cases', 'performance'].map((type) => (
                  <Grid item xs={6} key={type}>
                    <Chip
                      label={type}
                      onClick={() => {
                        if (testTypes.includes(type)) {
                          setTestTypes(testTypes.filter(t => t !== type));
                        } else {
                          setTestTypes([...testTypes, type]);
                        }
                      }}
                      color={testTypes.includes(type) ? 'primary' : 'default'}
                      variant={testTypes.includes(type) ? 'filled' : 'outlined'}
                    />
                  </Grid>
                ))}
              </Grid>
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowGenerateDialog(false)}>Cancel</Button>
          <Button
            onClick={submitGenerateTests}
            variant="contained"
            startIcon={<GenerateIcon />}
          >
            Generate Tests
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};