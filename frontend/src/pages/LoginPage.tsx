import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Button, TextField, Typography, Alert, CircularProgress, Link,
} from '@mui/material';
import BoltIcon from '@mui/icons-material/Bolt';
import { useAuth } from '../context/AuthContext';

const LoginPage: React.FC = () => {
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (mode === 'register') {
        await register(username, password);
        // After registration, log in automatically
        await login(username, password);
      } else {
        await login(username, password);
      }
      navigate('/');
    } catch (err: any) {
      setError(err.message ?? 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{
      minHeight: '100vh', bgcolor: '#1a1a2e',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <Box sx={{
        bgcolor: '#16213e', borderRadius: 3, p: 4, width: '100%', maxWidth: 380,
        boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
      }}>
        {/* Branding */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
          <BoltIcon sx={{ color: '#f0c040', fontSize: 32 }} />
          <Typography variant="h5" sx={{ color: '#f0c040', fontWeight: 'bold' }}>
            VPP Manager
          </Typography>
        </Box>

        <Typography variant="h6" sx={{ color: 'white', mb: 0.5 }}>
          {mode === 'login' ? 'Sign in' : 'Create account'}
        </Typography>
        <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)', mb: 3 }}>
          {mode === 'login'
            ? 'Access your energy community'
            : 'Start managing your virtual power plant'}
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            label="Username"
            value={username}
            onChange={e => setUsername(e.target.value)}
            required
            autoFocus
            autoComplete="username"
            InputLabelProps={{ sx: { color: 'rgba(255,255,255,0.6)' } }}
            InputProps={{ sx: { color: 'white' } }}
            sx={{ '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.2)' } }}
          />
          <TextField
            label="Password"
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            InputLabelProps={{ sx: { color: 'rgba(255,255,255,0.6)' } }}
            InputProps={{ sx: { color: 'white' } }}
            sx={{ '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.2)' } }}
          />
          <Button
            type="submit"
            variant="contained"
            disabled={loading || !username || !password}
            sx={{ bgcolor: '#f0c040', color: '#1a1a2e', fontWeight: 'bold', '&:hover': { bgcolor: '#d4a800' } }}
            startIcon={loading ? <CircularProgress size={16} color="inherit" /> : undefined}
          >
            {loading ? 'Please wait…' : mode === 'login' ? 'Sign In' : 'Create Account'}
          </Button>
        </Box>

        <Box sx={{ mt: 2, textAlign: 'center' }}>
          <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)' }}>
            {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
            <Link
              component="button"
              onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); }}
              sx={{ color: '#f0c040', cursor: 'pointer' }}
            >
              {mode === 'login' ? 'Register' : 'Sign in'}
            </Link>
          </Typography>
        </Box>
      </Box>
    </Box>
  );
};

export default LoginPage;
