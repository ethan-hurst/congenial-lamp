import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  IconButton,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControlLabel,
  Checkbox,
  Chip,
  Alert,
  CircularProgress,
  Tooltip,
  Divider,
} from '@mui/material';
import {
  AccountTree as BranchIcon,
  Add as AddIcon,
  MoreVert as MoreIcon,
  Delete as DeleteIcon,
  Merge as MergeIcon,
  Compare as CompareIcon,
  ContentCopy as CopyIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { api } from '../../services/api';

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

interface BranchVisualizerProps {
  databaseId: string;
  branches: DatabaseBranch[];
  onBranchCreate?: (branch: string) => void;
  onBranchSwitch?: (branch: string) => void;
  onBranchesUpdate?: () => void;
}

interface BranchNode {
  branch: DatabaseBranch;
  x: number;
  y: number;
  children: BranchNode[];
}

export const BranchVisualizer: React.FC<BranchVisualizerProps> = ({
  databaseId,
  branches: initialBranches,
  onBranchCreate,
  onBranchSwitch,
  onBranchesUpdate,
}) => {
  const [branches, setBranches] = useState<DatabaseBranch[]>(initialBranches);
  const [selectedBranch, setSelectedBranch] = useState<DatabaseBranch | null>(null);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [mergeDialogOpen, setMergeDialogOpen] = useState(false);
  const [diffDialogOpen, setDiffDialogOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [branchDiff, setBranchDiff] = useState<any>(null);
  
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Form state for create branch
  const [createForm, setCreateForm] = useState({
    sourceBranch: 'main',
    newBranch: '',
    useCow: true,
  });

  // Form state for merge
  const [mergeForm, setMergeForm] = useState({
    sourceBranch: '',
    targetBranch: 'main',
    strategy: 'full',
  });

  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    setBranches(initialBranches);
  }, [initialBranches]);

  useEffect(() => {
    drawBranchTree();
  }, [branches]);

  const buildBranchTree = (): BranchNode[] => {
    const branchMap = new Map<string, BranchNode>();
    const roots: BranchNode[] = [];

    // Create nodes
    branches.forEach(branch => {
      branchMap.set(branch.name, {
        branch,
        x: 0,
        y: 0,
        children: [],
      });
    });

    // Build tree structure
    branches.forEach(branch => {
      const node = branchMap.get(branch.name)!;
      if (branch.parent_branch) {
        const parent = branchMap.get(branch.parent_branch);
        if (parent) {
          parent.children.push(node);
        } else {
          roots.push(node);
        }
      } else {
        roots.push(node);
      }
    });

    // Calculate positions
    const nodeHeight = 60;
    const nodeWidth = 200;
    let currentY = 20;

    const calculatePositions = (node: BranchNode, x: number, y: number) => {
      node.x = x;
      node.y = y;
      let childY = y;
      node.children.forEach((child, index) => {
        calculatePositions(child, x + nodeWidth + 50, childY);
        childY += nodeHeight + 20;
      });
    };

    roots.forEach(root => {
      calculatePositions(root, 20, currentY);
      currentY += (root.children.length + 1) * (nodeHeight + 20);
    });

    return roots;
  };

  const drawBranchTree = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const tree = buildBranchTree();

    // Draw connections
    ctx.strokeStyle = '#666';
    ctx.lineWidth = 2;

    const drawConnections = (node: BranchNode) => {
      node.children.forEach(child => {
        ctx.beginPath();
        ctx.moveTo(node.x + 180, node.y + 25);
        ctx.lineTo(child.x, child.y + 25);
        ctx.stroke();
        drawConnections(child);
      });
    };

    tree.forEach(root => drawConnections(root));
  };

  const handleCreateBranch = async () => {
    const errors: Record<string, string> = {};
    if (!createForm.newBranch) errors.newBranch = 'Branch name is required';
    if (branches.some(b => b.name === createForm.newBranch)) {
      errors.newBranch = 'Branch name already exists';
    }

    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }

    setLoading(true);
    try {
      const response = await api.post(`/api/v1/databases/${databaseId}/branches`, {
        source_branch: createForm.sourceBranch,
        new_branch: createForm.newBranch,
        use_cow: createForm.useCow,
      });

      const newBranch = response.data;
      setBranches([...branches, newBranch]);
      setCreateDialogOpen(false);
      setCreateForm({ sourceBranch: 'main', newBranch: '', useCow: true });
      
      if (onBranchCreate) {
        onBranchCreate(newBranch.name);
      }
      if (onBranchesUpdate) {
        onBranchesUpdate();
      }
    } catch (error: any) {
      setFormErrors({ general: error.response?.data?.detail || 'Failed to create branch' });
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteBranch = async (branchName: string) => {
    if (!confirm(`Are you sure you want to delete branch "${branchName}"? This action cannot be undone.`)) {
      return;
    }

    try {
      await api.delete(`/api/v1/databases/${databaseId}/branches/${branchName}`);
      setBranches(branches.filter(b => b.name !== branchName));
      if (onBranchesUpdate) {
        onBranchesUpdate();
      }
    } catch (error) {
      console.error('Failed to delete branch:', error);
    }
  };

  const handleMergeBranch = async () => {
    setLoading(true);
    try {
      const response = await api.post(`/api/v1/databases/${databaseId}/branches/merge`, {
        source_branch: mergeForm.sourceBranch,
        target_branch: mergeForm.targetBranch,
        strategy: mergeForm.strategy,
      });

      setMergeDialogOpen(false);
      if (response.data.success) {
        alert('Branches merged successfully!');
      } else {
        alert(`Merge completed with conflicts: ${response.data.conflicts.length} conflicts found`);
      }
      
      if (onBranchesUpdate) {
        onBranchesUpdate();
      }
    } catch (error: any) {
      setFormErrors({ general: error.response?.data?.detail || 'Failed to merge branches' });
    } finally {
      setLoading(false);
    }
  };

  const handleCompareBranches = async (branch1: string, branch2: string) => {
    setLoading(true);
    try {
      const response = await api.get(
        `/api/v1/databases/${databaseId}/branches/diff?branch1=${branch1}&branch2=${branch2}`
      );
      setBranchDiff(response.data);
      setDiffDialogOpen(true);
    } catch (error) {
      console.error('Failed to compare branches:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleMenuClick = (event: React.MouseEvent<HTMLButtonElement>, branch: DatabaseBranch) => {
    setAnchorEl(event.currentTarget);
    setSelectedBranch(branch);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedBranch(null);
  };

  const renderBranchNode = (node: BranchNode) => {
    const { branch } = node;
    
    return (
      <Paper
        key={branch.id}
        elevation={3}
        sx={{
          position: 'absolute',
          left: node.x,
          top: node.y,
          width: 180,
          p: 1,
          cursor: 'pointer',
          border: branch.is_default ? '2px solid #1976d2' : '1px solid #ddd',
          '&:hover': {
            boxShadow: 4,
          },
        }}
        onClick={() => onBranchSwitch && onBranchSwitch(branch.name)}
      >
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box>
            <Typography variant="subtitle2" fontWeight="bold">
              {branch.name}
            </Typography>
            <Typography variant="caption" color="textSecondary">
              v{branch.schema_version} • {branch.storage_used_gb.toFixed(1)}GB
            </Typography>
          </Box>
          <IconButton
            size="small"
            onClick={(e) => {
              e.stopPropagation();
              handleMenuClick(e, branch);
            }}
          >
            <MoreIcon fontSize="small" />
          </IconButton>
        </Box>
        {branch.is_default && (
          <Chip label="Default" size="small" color="primary" sx={{ mt: 0.5 }} />
        )}
      </Paper>
    );
  };

  const tree = buildBranchTree();

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6">Database Branches</Typography>
        <Button
          variant="outlined"
          startIcon={<AddIcon />}
          onClick={() => setCreateDialogOpen(true)}
        >
          Create Branch
        </Button>
      </Box>

      <Paper
        variant="outlined"
        sx={{
          position: 'relative',
          height: 400,
          overflow: 'auto',
          bgcolor: '#f5f5f5',
        }}
      >
        <canvas
          ref={canvasRef}
          width={800}
          height={400}
          style={{ position: 'absolute', top: 0, left: 0 }}
        />
        {tree.map(root => {
          const renderTree = (node: BranchNode): React.ReactNode => (
            <React.Fragment key={node.branch.id}>
              {renderBranchNode(node)}
              {node.children.map(child => renderTree(child))}
            </React.Fragment>
          );
          return renderTree(root);
        })}
      </Paper>

      {/* Branch Actions Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem
          onClick={() => {
            if (selectedBranch) {
              setCreateForm({ ...createForm, sourceBranch: selectedBranch.name });
              setCreateDialogOpen(true);
              handleMenuClose();
            }
          }}
        >
          <BranchIcon fontSize="small" sx={{ mr: 1 }} />
          Create Branch from Here
        </MenuItem>
        <MenuItem
          onClick={() => {
            if (selectedBranch) {
              setMergeForm({ ...mergeForm, sourceBranch: selectedBranch.name });
              setMergeDialogOpen(true);
              handleMenuClose();
            }
          }}
        >
          <MergeIcon fontSize="small" sx={{ mr: 1 }} />
          Merge into Another Branch
        </MenuItem>
        <MenuItem
          onClick={() => {
            if (selectedBranch) {
              handleCompareBranches(selectedBranch.name, 'main');
              handleMenuClose();
            }
          }}
        >
          <CompareIcon fontSize="small" sx={{ mr: 1 }} />
          Compare with Main
        </MenuItem>
        <Divider />
        <MenuItem
          onClick={() => {
            if (selectedBranch && !selectedBranch.is_default) {
              handleDeleteBranch(selectedBranch.name);
              handleMenuClose();
            }
          }}
          disabled={selectedBranch?.is_default}
        >
          <DeleteIcon fontSize="small" sx={{ mr: 1 }} />
          Delete Branch
        </MenuItem>
      </Menu>

      {/* Create Branch Dialog */}
      <Dialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Create New Branch</DialogTitle>
        <DialogContent>
          {formErrors.general && (
            <Alert severity="error" sx={{ mb: 2 }}>{formErrors.general}</Alert>
          )}
          
          <TextField
            fullWidth
            label="New Branch Name"
            value={createForm.newBranch}
            onChange={(e) => setCreateForm({ ...createForm, newBranch: e.target.value })}
            error={!!formErrors.newBranch}
            helperText={formErrors.newBranch}
            margin="normal"
          />

          <TextField
            fullWidth
            label="Source Branch"
            value={createForm.sourceBranch}
            disabled
            margin="normal"
          />

          <FormControlLabel
            control={
              <Checkbox
                checked={createForm.useCow}
                onChange={(e) => setCreateForm({ ...createForm, useCow: e.target.checked })}
              />
            }
            label="Use Copy-on-Write (recommended for efficiency)"
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreateBranch} variant="contained" disabled={loading}>
            {loading ? <CircularProgress size={20} /> : 'Create Branch'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Merge Branch Dialog */}
      <Dialog
        open={mergeDialogOpen}
        onClose={() => setMergeDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Merge Branches</DialogTitle>
        <DialogContent>
          {formErrors.general && (
            <Alert severity="error" sx={{ mb: 2 }}>{formErrors.general}</Alert>
          )}
          
          <TextField
            fullWidth
            label="Source Branch"
            value={mergeForm.sourceBranch}
            disabled
            margin="normal"
          />

          <TextField
            fullWidth
            label="Target Branch"
            value={mergeForm.targetBranch}
            select
            onChange={(e) => setMergeForm({ ...mergeForm, targetBranch: e.target.value })}
            margin="normal"
          >
            {branches
              .filter(b => b.name !== mergeForm.sourceBranch)
              .map(branch => (
                <MenuItem key={branch.id} value={branch.name}>
                  {branch.name}
                </MenuItem>
              ))}
          </TextField>

          <Alert severity="warning" sx={{ mt: 2 }}>
            Merging will apply all changes from the source branch to the target branch.
            This operation cannot be undone.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setMergeDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleMergeBranch} variant="contained" color="warning" disabled={loading}>
            {loading ? <CircularProgress size={20} /> : 'Merge Branches'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Branch Diff Dialog */}
      <Dialog
        open={diffDialogOpen}
        onClose={() => setDiffDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Branch Differences</DialogTitle>
        <DialogContent>
          {branchDiff && (
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Schema Changes:
              </Typography>
              <Paper variant="outlined" sx={{ p: 2, mb: 2, bgcolor: '#f5f5f5' }}>
                <pre style={{ margin: 0, fontSize: '0.875rem' }}>
                  {JSON.stringify(branchDiff, null, 2)}
                </pre>
              </Paper>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDiffDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};