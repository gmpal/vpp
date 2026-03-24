import React, { useState } from 'react';
import {
  Box, Typography, Chip, Slider, Paper, Switch, FormControlLabel
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import HistoryIcon from '@mui/icons-material/History';

export interface TimelineState {
  isLive: boolean;
  startHoursAgo: number;
  endHoursAgo: number;
}

interface TimelineBarProps {
  onStateChange: (state: TimelineState) => void;
}

const TimelineBar: React.FC<TimelineBarProps> = ({ onStateChange }) => {
  const [isLive, setIsLive] = useState(true);
  const [range, setRange] = useState<[number, number]>([24, 0]);

  const handleLiveToggle = (checked: boolean) => {
    setIsLive(checked);
    onStateChange({ isLive: checked, startHoursAgo: range[0], endHoursAgo: range[1] });
  };

  const handleRangeChange = (_: any, val: number | number[]) => {
    const [a, b] = val as [number, number];
    setRange([a, b]);
    if (!isLive) onStateChange({ isLive: false, startHoursAgo: a, endHoursAgo: b });
  };

  const marks = [
    { value: 0, label: 'Now' },
    { value: 6, label: '6h ago' },
    { value: 12, label: '12h' },
    { value: 24, label: '24h' },
    { value: 48, label: '48h' },
  ];

  return (
    <Paper
      sx={{
        position: 'fixed', bottom: 0, left: 220, right: 0, zIndex: 1200,
        px: 4, py: 1.5,
        display: 'flex', alignItems: 'center', gap: 3,
        borderTop: '1px solid #e0e0e0',
        bgcolor: 'white',
      }}
      elevation={4}
    >
      <FormControlLabel
        control={<Switch checked={isLive} onChange={e => handleLiveToggle(e.target.checked)} color="success" />}
        label={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            {isLive ? <PlayArrowIcon color="success" fontSize="small" /> : <HistoryIcon fontSize="small" />}
            <Typography variant="body2" fontWeight="bold">{isLive ? 'Live' : 'Past'}</Typography>
          </Box>
        }
      />
      <Box sx={{ flex: 1, px: 2 }}>
        <Slider
          value={range}
          min={0}
          max={48}
          step={1}
          marks={marks}
          onChange={handleRangeChange}
          disabled={isLive}
          valueLabelDisplay="auto"
          valueLabelFormat={v => v === 0 ? 'Now' : `${v}h ago`}
          sx={{ '& .MuiSlider-mark': { bgcolor: '#bdbdbd' } }}
        />
      </Box>
      {!isLive && (
        <Chip
          label={`${range[0]}h – ${range[1] === 0 ? 'Now' : range[1] + 'h ago'}`}
          color="primary"
          size="small"
        />
      )}
    </Paper>
  );
};

export default TimelineBar;
