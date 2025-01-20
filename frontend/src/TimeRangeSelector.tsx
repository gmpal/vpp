// TimeRangeSelector.tsx
import * as React from 'react';
import { DateRangePicker, DateRange } from '@mui/x-date-pickers-pro/DateRangePicker';
import { TextField, Box } from '@mui/material';
import { LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';

interface TimeRangeSelectorProps {
    value: DateRange<Date>;
    onChange: (newValue: DateRange<Date>) => void;
}

const TimeRangeSelector: React.FC<TimeRangeSelectorProps> = ({ value, onChange }) => {
    return (
        <LocalizationProvider dateAdapter={AdapterDateFns}>
            <DateRangePicker
                startText="Start"
                endText="End"
                value={value}
                onChange={(newValue) => onChange(newValue)}
                renderInput={(startProps, endProps) => (
                    <React.Fragment>
                        <TextField {...startProps} />
                        <Box sx={{ mx: 2 }}> to </Box>
                        <TextField {...endProps} />
                    </React.Fragment>
                )}
            />
        </LocalizationProvider>
    );
};

export default TimeRangeSelector;
